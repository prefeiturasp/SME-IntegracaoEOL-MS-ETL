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
            "--fase",
            type=int,
            default=0,
            help="Forçar início a partir desta fase (ignora checkpoint se > 0).",
        )
        parser.add_argument(
            "--carga-inicial",
            action="store_true",
            help=(
                "Primeiro processamento: suprime a consulta de hashes "
                "existentes e escreve todos os registros diretamente. "
                "Usar na carga inicial."
            ),
        )
        parser.add_argument(
            "--celery",
            action="store_true",
            help="Lança a execução via Celery (Assíncrono).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execução padronizada do fluxo de ETL (Sync ou Async)."""
        repositorio = RepositorioAuditoriaPostgres()
        fase_inicial, token_ant = self._obter_ponto_partida(repositorio, **options)
        id_execucao = repositorio.iniciar_execucao(self.dominio)

        if options.get("celery"):
            self._handle_celery(fase_inicial, id_execucao, **options)
            return

        self._handle_sync(
            fase_inicial, id_execucao, repositorio, token_ant, **options
        )

    def _handle_celery(
        self,
        fase_inicial: int,
        id_execucao: Any,
        **options: Any,
    ) -> None:
        """Lança execução assíncrona via Orquestrador."""
        from apps.core.libs.base_etl_orquestrador import GenericEtlOrquestrador

        orquestrador_class = getattr(self, "orquestrador_class", GenericEtlOrquestrador)
        orquestrador = orquestrador_class(
            dominio=self.dominio,
            service_class=self.service_class,
            db_alias=f"{self.dominio}_db",
            id_execucao=id_execucao,
            primeiro_run=options.get("carga_inicial", False),
        )
        orquestrador.lancar(fase_inicial=fase_inicial)
        logger.info(
            "[%s] Pipeline lançado via Celery na fase %d.",
            self.dominio.upper(),
            fase_inicial,
        )

    def _handle_sync(
        self,
        fase_inicial: int,
        id_execucao: Any,
        repositorio: Any,
        token_ant: int,
        **options: Any,
    ) -> None:
        """Execução síncrona local."""
        servico = self.service_class(
            db_alias=f"{self.dominio}_db",
            id_execucao=id_execucao,
            repositorio_auditoria=repositorio,
            primeiro_run=options.get("carga_inicial", False),
        )

        try:
            resultado = servico.executar(fase_inicial=fase_inicial)
            self._finalizar_com_sucesso(
                repositorio, id_execucao, servico, resultado, token_ant
            )
        except KeyboardInterrupt:
            self._finalizar_com_interrupcao(repositorio, id_execucao, servico)
            raise
        except Exception as erro:
            self._finalizar_com_erro(
                repositorio, id_execucao, servico, erro, token_ant
            )

    def _finalizar_com_interrupcao(
        self, repositorio: Any, id_exec: Any, servico: Any
    ) -> None:
        """Registra interrupção manual pelo usuário."""
        token = servico.ultimo_token or "0"
        fase = servico.ultima_fase_concluida + 1
        repositorio.atualizar_checkpoint_dominio(
            dominio=self.dominio.lower(),
            ultimo_id_execucao=id_exec,
            ultima_pagina=fase,
            token_parada=token,
            indice_sincronizacao=f"CTRL+C:offset:{token}",
            ultima_situacao="interrompido",
            sucesso=False,
        )
        repositorio.finalizar_execucao(id_exec, situacao="interrompido")
        logger.warning("[%s] Execução interrompida pelo usuário.", self.dominio.upper())

    def _obter_ponto_partida(
        self, repositorio: Any, **options: Any
    ) -> tuple[int, int]:
        """Define fase e token inicial baseados em checkpoint ou flags."""
        fase_force = options.get("fase", 0)
        if fase_force > 0:
            return fase_force, 0

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
        """Finaliza execução registrando sucesso total."""
        token = servico.ultimo_token or str(token_ant)
        fase = servico.ultima_fase_concluida

        nome_tabela = "ultima_fase"
        if 0 < fase <= len(servico._fases):
            nome_tabela = servico._fases[fase - 1].table_name

        repositorio.atualizar_checkpoint_dominio(
            dominio=self.dominio.lower(),
            ultimo_id_execucao=id_exec,
            ultima_pagina=fase,
            token_parada=token,
            indice_sincronizacao=f"{nome_tabela}:offset:{token}",
            ultima_situacao="concluido",
            sucesso=True,
        )
        repositorio.finalizar_execucao(id_exec, situacao="concluido")
        total = sum(resultado.values())
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
            indice_sincronizacao=f"ERRO:offset:{token_erro}",
            ultima_situacao="erro",
            sucesso=False,
        )
        repositorio.finalizar_execucao(
            id_exec, situacao="erro", mensagem_erro=str(erro)
        )
        from django.core.management.base import CommandError

        raise CommandError(f"Falha ao executar {self.dominio}: {erro}")

    def get_modo_escrita(self, _tabela: str) -> str:
        """Determina o modo de escrita da tabela (pode ser sobrescrito)."""
        return "full_refresh"
