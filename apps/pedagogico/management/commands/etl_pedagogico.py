"""Comando Django para executar o ETL do domínio PEDAGOGICO_DB."""

from typing import Any

from apps.core.libs.base_etl_command import BaseEtlCommand
from apps.pedagogico.orquestrador import EtlPedagogicoOrquestrador
from apps.pedagogico.services import EtlPedagogicoService

_TABELAS_UPSERT = frozenset(
    {
        "componente_curricular",
        "componente_curricular_agrupamento",
        "componente_curricular_por_turma",
        "componente_curricular_regencia",
        "dados_aula_turma",
        "componente_curricular_por_ano_letivo",
        "agrupamento_atribuicao_territorio_saber",
    }
)


class Command(BaseEtlCommand):
    """Executa ETL completo ou parcial do domínio PEDAGOGICO_DB."""

    help = "Popula pedagogico_db a partir do EOL (SQL Server)"
    dominio = "pedagogico"
    fase_final = 6
    service_class = EtlPedagogicoService
    orquestrador_class = EtlPedagogicoOrquestrador

    def add_arguments(self, parser: Any) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--ano-letivo",
            type=int,
            default=None,
            help=(
                "Processa apenas anos letivos "
                "a partir deste valor (inclusive)."
            ),
        )

    def _extra_service_kwargs(self, **options: Any) -> dict[str, Any]:
        ano_letivo = options.get("ano_letivo")
        return {"ano_letivo": ano_letivo} if ano_letivo is not None else {}

    def get_modo_escrita(self, tabela: str) -> str:
        return "upsert" if tabela in _TABELAS_UPSERT else "full_refresh"
