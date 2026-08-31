"""Comando Django para executar o ETL do domínio PEDAGOGICO_DB."""

from typing import Any

from apps.core.libs.base_etl_command import BaseEtlCommand
from apps.pedagogico.orquestrador import EtlPedagogicoOrquestrador
from apps.pedagogico.services import EtlPedagogicoService

_TABELAS_UPSERT = frozenset(
    {
        "componente_curricular",
        "componente_curricular_agrupamento",
        "componente_curricular_regencia",
        "dados_aula_turma",
        "grade_componente_curricular",
        "atribuicao_territorio_saber",
        "turma",
    }
)


class Command(BaseEtlCommand):
    """Executa ETL completo ou parcial do domínio PEDAGOGICO_DB."""

    help = "Popula pedagogico_db a partir do EOL e da API EOL"
    dominio = "pedagogico"
    fase_final = 15
    service_class = EtlPedagogicoService
    orquestrador_class = EtlPedagogicoOrquestrador

    def add_arguments(self, parser: Any) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--anos-letivos",
            type=int,
            nargs="+",
            default=None,
            metavar="ANO",
            help=(
                "Processa apenas os anos letivos informados. "
                "Ex: --anos-letivos 2025 2026"
            ),
        )

    def _extra_service_kwargs(self, **options: Any) -> dict[str, Any]:
        anos = options.get("anos_letivos")
        return {"anos_letivos": anos} if anos else {}

    def get_modo_escrita(self, tabela: str) -> str:
        return "upsert" if tabela in _TABELAS_UPSERT else "full_refresh"
