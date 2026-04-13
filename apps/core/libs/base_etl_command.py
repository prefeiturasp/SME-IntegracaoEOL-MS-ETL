"""Base para implementação de comandos de ETL com controle de auditoria."""

import logging
from typing import Any

from django.core.management.base import BaseCommand

from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)

logger = logging.getLogger(__name__)


class BaseEtlCommand(BaseCommand):
    """Base para comandos que executam serviços de ETL.

    Centraliza o controle de:
        - Registro de execução (início/fim).
        - Leitura e atualização de checkpoint de retomada.
        - Registro de métricas de tabelas lidas/escritas.
        - Tratamento de exceções com persistência de erro no auditoria.
    """

    # Atributos obrigatórios nas subclasses
    dominio: str = ""
    fase_final: int = 4
    service_class: Any = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Inicializa o comando de ETL validando os atributos mandatórios."""
        super().__init__(*args, **kwargs)
        if not self.dominio or not self.service_class:
            raise NotImplementedError(
                "Subclasse deve definir 'dominio' e 'service_class'"
            )

    def add_arguments(self, parser: Any) -> None:
        """Declara argumentos padrão para todos os comandos de ETL."""
        parser.add_argument(
            "--volume",
            type=int,
            default=500,
            help="Tamanho de lote para controle de progresso pelo Celery.",
        )
        parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="Deslocamento inicial (reservado para uso futuro).",
        )
        parser.add_argument(
            "--continuar",
            action="store_true",
            help=(
                "Retoma da fase seguinte à última concluída com sucesso. "
                "Quando a última execução terminou com sucesso, reinicia "
                "do zero para processar alterações incrementais."
            ),
        )
        parser.add_argument(
            "--particao",
            type=int,
            default=0,
            help="ID da partição atual (0 a total-1).",
        )
        parser.add_argument(
            "--total-particoes",
            type=int,
            default=1,
            help="Total de partições concorrentes.",
        )
        parser.add_argument(
            "--fase",
            type=int,
            default=0,
            help="Forçar início a partir desta fase (ignora checkpoint se > 0).",
        )
        parser.add_argument(
            "--id-min",
            type=int,
            default=None,
            help="ID mínimo do range para esta partição.",
        )
        parser.add_argument(
            "--id-max",
            type=int,
            default=None,
            help="ID máximo do range para esta partição.",
        )
        parser.add_argument(
            "--full-sync",
            action="store_true",
            help=(
                "Primeiro processamento: suprime a consulta de hashes "
                "existentes e escreve todos os registros diretamente. "
                "Usar na carga inicial."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execução padronizada do fluxo de ETL."""
        repositorio = RepositorioAuditoriaPostgres()
        fase_inicial, token_ant = self._obter_ponto_partida(repositorio, **options)
        id_execucao = repositorio.iniciar_execucao(self.dominio)

        servico = self.service_class(
            db_alias=f"{self.dominio}_db",
            id_execucao=id_execucao,
            repositorio_auditoria=repositorio,
            id_min=options.get("id_min"),
            id_max=options.get("id_max"),
            particao=options.get("particao", 0),
            total_particoes=options.get("total_particoes", 1),
            primeiro_run=options.get("full_sync", False),
        )

        try:
            resultado = servico.executar(fase_inicial=fase_inicial)
            self._finalizar_com_sucesso(
                repositorio, id_execucao, servico, resultado, token_ant
            )
        except Exception as erro:
            self._finalizar_com_erro(
                repositorio, id_execucao, servico, erro, token_ant
            )

    def _obter_ponto_partida(
        self, repositorio: Any, **options: Any
    ) -> tuple[int, int]:
        """Define fase e token inicial baseados em checkpoint ou flags."""
        fase_forcada = options.get("fase", 0)
        if fase_forcada > 0:
            return fase_forcada, 0

        if not options.get("continuar", False):
            return 1, 0

        checkpoint = repositorio.obter_checkpoint_dominio(self.dominio)
        if not checkpoint:
            return 1, 0

        situacao = str(checkpoint.get("ultima_situacao") or "")
        fase = int(str(checkpoint.get("ultima_pagina") or 0))
        token = int(str(checkpoint.get("token_parada") or 0))

        if situacao == "erro" and 0 < fase < self.fase_final:
            label = self.dominio[:4].upper()
            logger.warning("[ETL %s] Retomando da fase %d.", label, fase + 1)
            return fase + 1, token

        return 1, 0

    def _finalizar_com_sucesso(
        self,
        repositorio: Any,
        id_exec: Any,
        servico: Any,
        resultado: dict[str, int],
        token_ant: int,
    ) -> None:
        """Registra métricas, finaliza execução e atualiza checkpoint."""
        for tabela, linhas in resultado.items():
            repositorio.registrar_tabela_escrita(
                id_execucao=id_exec,
                tabela_destino=tabela,
                linhas_escritas=linhas,
                modo_escrita=self.get_modo_escrita(tabela),
            )

        total = sum(resultado.values())
        novo_token = token_ant + total
        ultima = list(resultado.keys())[-1] if resultado else self.dominio
        indice = f"{ultima}:offset:{novo_token}"

        repositorio.atualizar_checkpoint_dominio(
            dominio=self.dominio,
            ultimo_id_execucao=id_exec,
            ultima_pagina=servico.ultima_fase_concluida,
            token_parada=str(novo_token),
            indice_sincronizacao=indice,
            ultima_situacao="concluido",
            sucesso=True,
        )
        repositorio.finalizar_execucao(id_exec, situacao="concluido")
        logger.info(
            "[ETL %s] Concluído. %d alterados.",
            self.dominio[:4].upper(),
            total,
        )

    def _finalizar_com_erro(
        self,
        repositorio: Any,
        id_exec: Any,
        servico: Any,
        erro: Exception,
        token_ant: int,
    ) -> None:
        """Registra falha na auditoria e no checkpoint para retomada."""
        token_erro = servico.ultimo_token or str(token_ant)
        fase = servico.ultima_fase_concluida

        repositorio.atualizar_checkpoint_dominio(
            dominio=self.dominio,
            ultimo_id_execucao=id_exec,
            ultima_pagina=fase,
            token_parada=token_erro,
            indice_sincronizacao=f"ERRO:{fase}:{token_erro}",
            ultima_situacao="erro",
            sucesso=False,
        )
        repositorio.finalizar_execucao(id_exec, situacao="erro", mensagem_erro=str(erro))
        from django.core.management.base import CommandError

        raise CommandError(f"Falha ao executar {self.dominio}: {erro}")

    def get_modo_escrita(self, _tabela: str) -> str:
        """Determina o modo de escrita da tabela (pode ser sobrescrito)."""
        return "full_refresh"
