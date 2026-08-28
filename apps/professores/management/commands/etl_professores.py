"""Comando Django para executar o ETL do dominio PROFESSORES_DB.

Suporta execução incremental por hash de linha e retomada por checkpoint
de fase, tabela e lote, integrando ao fluxo Celery de controle_auditoria.

Fluxo de controle:
    1. Lê checkpoint para determinar fase/tabela/lote de retomada.
    2. Inicia registro de execução no banco de auditoria.
    3. Executa ETL a partir da fase/tabela/lote determinada.
    4. Após cada lote concluído: salva checkpoint com "tabela:lote".
    5. Após cada tabela concluída: salva checkpoint com "tabela".
    6. Registra métricas por tabela no log de auditoria.
    7. Atualiza checkpoint final com token_parada acumulado.

Formato de indice_sincronizacao:
    "turma_escola:435"  — tabela interrompida no lote 435 (retoma do 436)
    "turma_escola"      — tabela concluída (próxima tabela começa do lote 1)
    None                — execução concluída ou nunca iniciada
"""

import json
import os
from argparse import SUPPRESS
from typing import Any
from uuid import UUID

from django.core.management.base import BaseCommand

from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)
from apps.professores.services import (
    _ORDEM_TABELAS,
    _TABELAS_FULL_REFRESH,
    EtlProfessoresService,
)

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
        "funcionario_unidade_educacional",
        "funcionario_sistema_perfil",
        "agrupamento_atribuicao_territorio_saber",
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
        parser.add_argument(
            "--anos-letivos",
            type=int,
            nargs="+",
            default=None,
            metavar="ANO",
            help="Processa apenas os anos letivos informados.",
        )
        parser.add_argument(
            "--skip-audit-hash",
            "--skip-salvar-dados-auditoria",
            action="store_true",
            dest="skip_audit_hash",
            help="Não grava hashes em etl_auditoria_linha.",
        )
        parser.add_argument(
            "--parametros-disparo",
            type=str,
            default=None,
            help=SUPPRESS,
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Executa o ETL e registra auditoria e checkpoint."""
        continuar: bool = options["continuar"]
        anos_letivos: list[int] | None = options.get("anos_letivos")
        if options.get("skip_audit_hash"):
            os.environ["ETL_SKIP_AUDIT_HASH"] = "1"

        repositorio = RepositorioAuditoriaPostgres()

        fase_inicial, pular_ate, token_anterior, lote_inicial = (
            self._obter_contexto_retomada(continuar, repositorio)
        )

        # ------------------------------------------------------------------
        # Executar ETL
        # ------------------------------------------------------------------
        id_execucao: UUID = repositorio.iniciar_execucao(
            "professores",
            parametros=self._parametros_execucao(fase_inicial, **options),
        )
        servico = EtlProfessoresService(anos_letivos=anos_letivos)
        ultimo_indice_salvo: str | None = None

        def _salvar_checkpoint_lote(tabela: str, lote: int) -> None:
            """Salva checkpoint após cada lote — formato 'tabela:lote'."""
            nonlocal ultimo_indice_salvo
            ultimo_indice_salvo = f"{tabela}:{lote}"
            repositorio.atualizar_checkpoint_dominio(
                dominio="professores",
                ultimo_id_execucao=id_execucao,
                ultima_pagina=servico.ultima_fase_concluida,
                token_parada=str(token_anterior),
                indice_sincronizacao=ultimo_indice_salvo,
                ultima_situacao="parcial",
                sucesso=False,
            )

        def _salvar_checkpoint_tabela(tabela: str, _linhas: int) -> None:
            """Salva checkpoint após tabela concluída — formato 'tabela'."""
            nonlocal ultimo_indice_salvo
            ultimo_indice_salvo = tabela
            repositorio.atualizar_checkpoint_dominio(
                dominio="professores",
                ultimo_id_execucao=id_execucao,
                ultima_pagina=servico.ultima_fase_concluida,
                token_parada=str(token_anterior),
                indice_sincronizacao=ultimo_indice_salvo,
                ultima_situacao="parcial",
                sucesso=False,
            )

        try:
            resultado = servico.executar(
                fase_inicial=fase_inicial,
                pular_ate=pular_ate,
                lote_inicial=lote_inicial,
                on_lote=_salvar_checkpoint_lote,
                on_tabela_concluida=_salvar_checkpoint_tabela,
            )

            # Registrar métricas por tabela no log de auditoria
            for tabela, linhas in resultado.items():
                modo = (
                    "upsert" if tabela in _TABELAS_UPSERT else "full_refresh"
                )
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
            # O callback já salvou o indice_sincronizacao da última tabela
            # concluída. Aqui apenas marca a situação como "erro" preservando
            # esse valor para que --continuar retome após essa tabela.
            repositorio.atualizar_checkpoint_dominio(
                dominio="professores",
                ultimo_id_execucao=id_execucao,
                ultima_pagina=servico.ultima_fase_concluida,
                token_parada=str(token_anterior),
                indice_sincronizacao=ultimo_indice_salvo,
                ultima_situacao="erro",
                sucesso=False,
            )
            repositorio.finalizar_execucao(
                id_execucao,
                situacao="erro",
                mensagem_erro=str(erro),
            )
            raise

    # ------------------------------------------------------------------
    # Helpers de retomada
    # ------------------------------------------------------------------

    def _parametros_execucao(
        self, fase_inicial: int, **options: Any
    ) -> dict[str, object]:
        """Monta parâmetros rastreáveis da execução."""
        disparo_raw = options.get("parametros_disparo")
        disparo: dict[str, object] = {}
        if disparo_raw:
            try:
                disparo = json.loads(disparo_raw)
            except (TypeError, json.JSONDecodeError):
                disparo = {"raw": str(disparo_raw)}

        execucao = {
            "volume": options.get("volume"),
            "offset": options.get("offset"),
            "continuar": options.get("continuar", False),
            "fase_inicial": fase_inicial,
            "anos_letivos": options.get("anos_letivos"),
            "skip_audit_hash": options.get("skip_audit_hash", False),
        }
        return {"execucao": execucao, "disparo": disparo}

    def _interpretar_checkpoint(
        self, checkpoint: dict
    ) -> tuple[int, str, int]:
        """Extrai ultima_fase, raw_indice e token_anterior do checkpoint."""
        ultima_fase = int(str(checkpoint.get("ultima_pagina") or 0))
        raw_indice = str(checkpoint.get("indice_sincronizacao") or "")
        token_anterior = int(str(checkpoint.get("token_parada") or 0))
        return ultima_fase, raw_indice, token_anterior

    def _log_retomada(
        self,
        fase_inicial: int,
        tabela_interrompida: str | None,
        lote_salvo: int | None,
        pular_ate: str | None,
    ) -> None:
        """Emitir mensagem de retomada adequada ao contexto."""
        if tabela_interrompida is not None and lote_salvo is not None:
            self.stdout.write(
                self.style.WARNING(
                    f"[ETL PROF] Retomando '{tabela_interrompida}'"
                    f" do lote {lote_salvo + 1}"
                    f" (fase {fase_inicial})."
                )
            )
        elif pular_ate is not None:
            self.stdout.write(
                self.style.WARNING(
                    f"[ETL PROF] Retomando da fase {fase_inicial}"
                    f", após '{pular_ate}'."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"[ETL PROF] Retomando da fase {fase_inicial}."
                )
            )

    def _calcular_pulo_e_lote(
        self, raw_indice: str, fase_inicial: int
    ) -> tuple[str | None, int]:
        """Determina pular_ate e lote_inicial a partir do índice salvo."""
        if not raw_indice:
            self._log_retomada(fase_inicial, None, None, None)
            return None, 0

        if ":" in raw_indice:
            # "tabela:lote" — tabela interrompida no meio
            tabela_interrompida, lote_str = raw_indice.split(":", 1)
            lote_salvo = int(lote_str)
            # Tabelas full-refresh não suportam retomada por lote.
            lote_inicial = (
                0
                if tabela_interrompida in _TABELAS_FULL_REFRESH
                else lote_salvo
            )
            idx = (
                _ORDEM_TABELAS.index(tabela_interrompida)
                if tabela_interrompida in _ORDEM_TABELAS
                else -1
            )
            pular_ate = _ORDEM_TABELAS[idx - 1] if idx > 0 else None
            self._log_retomada(
                fase_inicial, tabela_interrompida, lote_salvo, pular_ate
            )
            return pular_ate, lote_inicial

        # "tabela" — tabela concluída; próxima começa do lote 0
        pular_ate = raw_indice
        self._log_retomada(fase_inicial, None, None, pular_ate)
        return pular_ate, 0

    def _obter_contexto_retomada(
        self,
        continuar: bool,
        repositorio: RepositorioAuditoriaPostgres,
    ) -> tuple[int, str | None, int, int]:
        """Retorna (fase_inicial, pular_ate, token_anterior, lote_inicial)."""
        if not continuar:
            return 1, None, 0, 0

        checkpoint = repositorio.obter_checkpoint_dominio("professores")
        if not checkpoint:
            return 1, None, 0, 0

        ultima_fase, raw_indice, token_anterior = self._interpretar_checkpoint(
            checkpoint
        )
        # Se tudo foi concluído (fase 4), reinicia do zero.
        fase_inicial = ultima_fase + 1 if ultima_fase < 4 else 1
        pular_ate, lote_inicial = self._calcular_pulo_e_lote(
            raw_indice, fase_inicial
        )
        return fase_inicial, pular_ate, token_anterior, lote_inicial
