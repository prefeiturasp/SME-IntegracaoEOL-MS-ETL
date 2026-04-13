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
        continuar: bool = options.get("continuar", False)
        fase_forcada: int = options.get("fase", 0)
        repositorio = RepositorioAuditoriaPostgres()

        # Determinando fase inicial e token anterior
        fase_inicial = fase_forcada if fase_forcada > 0 else 1
        token_anterior = 0

        if continuar and not fase_forcada:
            checkpoint = repositorio.obter_checkpoint_dominio(self.dominio)
            if checkpoint:
                ultima_situacao = str(checkpoint.get("ultima_situacao") or "")
                ultima_fase = int(str(checkpoint.get("ultima_pagina") or 0))
                token_anterior = int(
                    str(checkpoint.get("token_parada") or 0)
                )

                if ultima_situacao == "erro" and 0 < ultima_fase < self.fase_final:
                    fase_inicial = ultima_fase + 1
                    label = self.dominio[:4].upper()
                    logger.warning(
                        "[ETL %s] Retomando da fase %d (última concluída: %d).",
                        label,
                        fase_inicial,
                        ultima_fase,
                    )
                else:
                    fase_inicial = 1

        id_execucao = repositorio.iniciar_execucao(self.dominio)

        # Injeção de dependências no serviço
        servico = self.service_class(
            db_alias=self.dominio + "_db",
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

            for tabela, linhas in resultado.items():
                repositorio.registrar_tabela_escrita(
                    id_execucao=id_execucao,
                    tabela_destino=tabela,
                    linhas_escritas=linhas,
                    modo_escrita=self.get_modo_escrita(tabela),
                )

            total_alterado = sum(resultado.values())
            novo_token = token_anterior + total_alterado

            ultima_tabela = (
                list(resultado.keys())[-1] if resultado else self.dominio
            )
            indice = f"{ultima_tabela}:offset:{novo_token}"

            repositorio.atualizar_checkpoint_dominio(
                dominio=self.dominio,
                ultimo_id_execucao=id_execucao,
                ultima_pagina=servico.ultima_fase_concluida,
                token_parada=str(novo_token),
                indice_sincronizacao=indice,
                ultima_situacao="concluido",
                sucesso=True,
            )
            repositorio.finalizar_execucao(id_execucao, situacao="concluido")

            label = self.dominio[:4].upper()
            logger.info(
                "[ETL %s] Concluído. Linhas alteradas: %d. token_parada: %s.",
                label,
                total_alterado,
                str(novo_token),
            )

        except Exception as erro:
            # Em caso de erro, salvamos o progresso parcial se disponível
            token_erro = servico.ultimo_token or str(token_anterior)
            fase_atual = servico.ultima_fase_concluida

            repositorio.atualizar_checkpoint_dominio(
                dominio=self.dominio,
                ultimo_id_execucao=id_execucao,
                ultima_pagina=fase_atual,
                token_parada=token_erro,
                indice_sincronizacao=f"ERRO:{fase_atual}:{token_erro}",
                ultima_situacao="erro",
                sucesso=False,
            )
            repositorio.finalizar_execucao(
                id_execucao,
                situacao="erro",
                mensagem_erro=str(erro),
            )
            from django.core.management.base import CommandError

            raise CommandError(
                f"Falha ao executar {self.dominio}: {erro}"
            ) from erro

    def get_modo_escrita(self, _tabela: str) -> str:
        """Determina o modo de escrita da tabela (pode ser sobrescrito)."""
        return "full_refresh"
