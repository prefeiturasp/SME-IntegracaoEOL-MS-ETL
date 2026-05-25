"""Comando Django para executar o ETL do domínio PROGRAMAS_DB."""

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

    def get_modo_escrita(self, tabela: str) -> str:
        """Retorna 'upsert' para tabelas incrementais e 'full_refresh' caso contrário."""
        return "upsert" if tabela in _TABELAS_UPSERT else "full_refresh"
