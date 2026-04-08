"""Comando Django para executar o ETL do domínio PROGRAMAS_DB."""

from apps.core.libs.base_etl_command import BaseEtlCommand
from apps.programas.services import EtlProgramasService


class Command(BaseEtlCommand):
    """Executa ETL completo ou parcial do domínio PROGRAMAS_DB."""

    help = "Popula programas_db a partir do EOL (SQL Server)"
    dominio = "programas"
    fase_final = 5
    service_class = EtlProgramasService

    def get_modo_escrit(self, tabela: str) -> str:
        """Determina o modo de escrita da tabela (pode ser sobrescrito)."""
        return "upsert" if tabela in {"programa", "acao_programa"} else "full_refresh"
