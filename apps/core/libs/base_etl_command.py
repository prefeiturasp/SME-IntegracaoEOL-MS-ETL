"""Base para implementação de comandos de ETL com controle de auditoria."""

import logging
from typing import Any
from uuid import UUID

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

    def handle(self, *args: Any, **options: Any) -> None:
        """Execução padronizada do fluxo de ETL."""
        continuar: bool = options["continuar"]
        repositorio = RepositorioAuditoriaPostgres()

        # Determinando fase inicial e token anterior
        fase_inicial = 1
        token_anterior = 0

        if continuar:
            checkpoint = repositorio.obter_checkpoint_dominio(self.dominio)
            if checkpoint:
                ultima_situacao = str(checkpoint.get("ultima_situacao") or "")
                ultima_fase = int(str(checkpoint.get("ultima_pagina") or 0))
                token_anterior = int(str(checkpoint.get("token_parada") or 0))

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

        # Registro de início
        id_execucao: UUID = repositorio.iniciar_execucao(self.dominio)
        servico = self.service_class()

        try:
            resultado = servico.executar(fase_inicial=fase_inicial)

            # Registrar métricas por tabela
            for tabela, linhas in resultado.items():
                modo = self.get_modo_escrita(tabela)
                repositorio.registrar_tabela_escrita(
                    id_execucao=id_execucao,
                    tabela_destino=tabela,
                    linhas_escritas=linhas,
                    modo_escrita=modo,
                )
                repositorio.registrar_tabela_lida(
                    id_execucao=id_execucao,
                    tabela_origem=tabela,
                    numero_pagina=1,
                    linhas_lidas=linhas,
                )

            total_alterado = sum(resultado.values())
            novo_token = token_anterior + total_alterado

            # Finalização com sucesso
            repositorio.atualizar_checkpoint_dominio(
                dominio=self.dominio,
                ultimo_id_execucao=id_execucao,
                ultima_pagina=servico.ultima_fase_concluida,
                token_parada=str(novo_token),
                indice_sincronizacao=None,
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
            # Persistência de erro no checkpoint e log
            repositorio.atualizar_checkpoint_dominio(
                dominio=self.dominio,
                ultimo_id_execucao=id_execucao,
                ultima_pagina=servico.ultima_fase_concluida,
                token_parada=str(token_anterior),
                indice_sincronizacao=None,
                ultima_situacao="erro",
                sucesso=False,
            )
            repositorio.finalizar_execucao(
                id_execucao,
                situacao="erro",
                mensagem_erro=str(erro),
            )
            from django.core.management.base import CommandError

            raise CommandError(f"Falha ao executar {self.dominio}: {erro}") from erro

    def get_modo_escrita(self, tabela: str) -> str:
        """Determina o modo de escrita da tabela (pode ser sobrescrito)."""
        return "full_refresh"
