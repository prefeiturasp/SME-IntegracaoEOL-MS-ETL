"""Comando Django para executar o ETL do domínio PROGRAMAS_DB."""

from typing import Any

from apps.core.libs.base_etl_command import BaseEtlCommand
from apps.programas.orquestrador import EtlProgramasOrquestrador
from apps.programas.services import EtlProgramasService

_TABELAS_UPSERT = frozenset(
    {
        "tipo_programa",
        "componente_curricular_programa",
        "turma_programa",
        "turma_programa_componente_curricular",
        "matricula_turma_programa",
        "matricula_turma_programa_historico",
    }
)


class Command(BaseEtlCommand):
    """Executa o pipeline ETL do domínio Programas."""

    help = "Executa pipeline ETL do domínio PROGRAMAS_DB (Sync ou Celery)"
    dominio = "programas"
    fase_final = 6
    service_class = EtlProgramasService
    orquestrador_class = EtlProgramasOrquestrador

    def add_arguments(self, parser: Any) -> None:
        """Declara argumentos do comando, incluindo o filtro de anos."""
        super().add_arguments(parser)
        parser.add_argument(
            "--anos-letivos",
            type=int,
            nargs="+",
            default=None,
            metavar="ANO",
            help="Processa apenas os anos letivos informados.",
        )

    def _extra_service_kwargs(self, **options: Any) -> dict[str, Any]:
        """Repassa o filtro de anos letivos para o service."""
        anos = options.get("anos_letivos")
        return {"anos_letivos": anos} if anos else {}

    def get_modo_escrita(self, tabela: str) -> str:
        """Retorna modo de escrita usado no log da tabela."""
        return "upsert" if tabela in _TABELAS_UPSERT else "full_refresh"
