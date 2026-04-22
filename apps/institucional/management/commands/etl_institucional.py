"""Comando Django para executar o ETL do domínio INSTITUCIONAL_DB."""

from apps.core.libs.base_etl_command import BaseEtlCommand
from apps.institucional.orquestrador import EtlInstitucionalOrquestrador
from apps.institucional.services import EtlInstitucionalService

_TABELAS_UPSERT = frozenset(
    {
        "dre",
        "tipo_escola",
        "sub_prefeitura",
        "unidade_educacional",
    }
)


class Command(BaseEtlCommand):
    """Executa ETL completo ou parcial do domínio INSTITUCIONAL_DB."""

    help = "Popula institucional_db a partir do EOL (SQL Server)"
    dominio = "institucional"
    fase_final = 4
    service_class = EtlInstitucionalService
    orquestrador_class = EtlInstitucionalOrquestrador

    def get_modo_escrita(self, tabela: str) -> str:
        """Determina o modo de escrita da tabela (pode ser sobrescrito)."""
        return "upsert" if tabela in _TABELAS_UPSERT else "full_refresh"
