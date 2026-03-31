"""Comando Django para executar o ETL do dominio PROFESSORES_DB.

Suporta execução incremental por hash de linha e retomada por checkpoint
de fase, integrando-se ao fluxo Celery definido em controle_auditoria.

Fluxo de controle:
    1. Lê checkpoint para determinar de qual fase retomar (se --continuar).
    2. Inicia registro de execução no banco de auditoria.
    3. Executa as fases do ETL a partir da fase determinada.
    4. Registra leituras e escritas por tabela no log de auditoria.
    5. Atualiza checkpoint com a fase concluída e token_parada acumulado.
    6. Em caso de erro: persiste o checkpoint da última fase bem-sucedida
       antes de propagar a exceção, permitindo retomada precisa.

Controle por hash (EtlAuditoriaLinha):
    Cada registro escrito é comparado via SHA-256 dos campos relevantes.
    Apenas registros alterados ou novos geram escrita no destino.
    O ``token_parada`` acumula o total de linhas *efetivamente alteradas*
    em todas as execuções, servindo como sinal de progresso para o Celery.
"""

from typing import Any
from uuid import UUID

from django.core.management.base import BaseCommand

from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)
from apps.professores.services import EtlProfessoresService

# Tabelas que usam estratégia upsert incremental (hash por linha).
# As demais usam full-refresh (delete + bulk_create).
_TABELAS_UPSERT = frozenset(
    {
        "unidade_educacional",
        "turma_escola",
        "professor",
        "pessoa",
        "serie_turma_grade",
        "turma_escola_grade_programa",
        "cargo_base_servidor",
        "contrato_externo",
        "atribuicao_aula",
        "atribuicao_externo",
    }
)


class Command(BaseCommand):
    """Executa ETL completo ou parcial do dominio PROFESSORES_DB."""

    help = "Popula professores_db a partir do EOL (SQL Server)"

    def add_arguments(self, parser: Any) -> None:
        """Declara argumentos do comando."""
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
        """Executa o ETL e registra auditoria e checkpoint."""
        continuar: bool = options["continuar"]

        repositorio = RepositorioAuditoriaPostgres()

        # ------------------------------------------------------------------
        # Determinar fase inicial e token acumulado anterior
        # ------------------------------------------------------------------
        fase_inicial = 1
        token_anterior = 0

        if continuar:
            checkpoint = repositorio.obter_checkpoint_dominio("professores")
            if checkpoint:
                ultima_situacao = str(checkpoint.get("ultima_situacao") or "")
                ultima_fase = int(str(checkpoint.get("ultima_pagina") or 0))
                token_anterior = int(str(checkpoint.get("token_parada") or 0))

                if ultima_situacao == "erro" and 0 < ultima_fase < 4:
                    # Retoma da próxima fase após a última bem-sucedida
                    fase_inicial = ultima_fase + 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"[ETL PROF] Retomando da fase {fase_inicial}"
                            f" (última concluída: {ultima_fase})."
                        )
                    )
                else:
                    # Sucesso ou fase 4 já concluída: reinicia do zero
                    fase_inicial = 1

        # ------------------------------------------------------------------
        # Executar ETL
        # ------------------------------------------------------------------
        id_execucao: UUID = repositorio.iniciar_execucao("professores")
        servico = EtlProfessoresService()

        try:
            resultado = servico.executar(fase_inicial=fase_inicial)

            # Registrar métricas por tabela no log de auditoria
            for tabela, linhas in resultado.items():
                modo = "upsert" if tabela in _TABELAS_UPSERT else "full_refresh"
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

            repositorio.atualizar_checkpoint_dominio(
                dominio="professores",
                ultimo_id_execucao=id_execucao,
                ultima_pagina=servico.ultima_fase_concluida,
                token_parada=str(novo_token),
                indice_sincronizacao=None,
                ultima_situacao="concluido",
                sucesso=True,
            )
            repositorio.finalizar_execucao(id_execucao, situacao="concluido")

            self.stdout.write(
                self.style.SUCCESS(
                    f"[ETL PROF] Concluído. "
                    f"Linhas alteradas: {total_alterado}. "
                    f"token_parada: {novo_token}."
                )
            )

        except Exception as erro:
            # Persiste checkpoint com a fase até onde chegou antes de falhar.
            # Permite que o Celery retome via --continuar na próxima tentativa.
            repositorio.atualizar_checkpoint_dominio(
                dominio="professores",
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
            raise
