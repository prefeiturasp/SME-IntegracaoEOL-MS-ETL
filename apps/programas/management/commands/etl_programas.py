"""Comando Django para executar o ETL do domínio PROGRAMAS_DB."""

from apps.core.libs.base_etl_command import BaseEtlCommand
from apps.programas.services import EtlProgramasService

_TABELAS_UPSERT = frozenset(
    {
        "tipo_programa",
        "componente_curricular_programa",
        "turma_programa",
        "turma_programa_componente_curricular",
        "matricula_turma_programa",
    }
)


class Command(BaseEtlCommand):
    """Executa ETL completo ou parcial do domínio PROGRAMAS_DB."""

    help = "Popula programas_db a partir do EOL (SQL Server)"
    dominio = "programas"
    fase_final = 5
    service_class = EtlProgramasService

    def get_modo_escrita(self, tabela: str) -> str:
        """Determina o modo de escrita da tabela (pode ser sobrescrito)."""
        return "upsert" if tabela in _TABELAS_UPSERT else "full_refresh"
