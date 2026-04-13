"""Comando Django para executar o ETL do domínio PEDAGOGICO_DB."""

from apps.core.libs.base_etl_command import BaseEtlCommand
from apps.pedagogico.services import EtlPedagogicoService

_TABELAS_UPSERT = frozenset({
    "componente_curricular",
    "componente_curricular_agrupamento",
    "componente_curricular_por_turma",
    "componente_curricular_regencia",
    "dados_aula_turma",
    "componente_curricular_por_ano_letivo",
    "agrupamento_atribuicao_territorio_saber",
})


class Command(BaseEtlCommand):
    """Executa ETL completo ou parcial do domínio PEDAGOGICO_DB."""

    help = "Popula pedagogico_db a partir do EOL (SQL Server)"
    dominio = "pedagogico"
    fase_final = 6
    service_class = EtlPedagogicoService

    def get_modo_escrita(self, tabela: str) -> str:
        return "upsert" if tabela in _TABELAS_UPSERT else "full_refresh"
