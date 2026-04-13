"""Comando Django para executar o ETL do domínio ALUNOS_DB."""

from apps.alunos.services import EtlAlunosService
from apps.core.libs.base_etl_command import BaseEtlCommand

_TABELAS_UPSERT = frozenset(
    {
        "tipo_necessidade_especial",
        "aluno",
        "responsavel_aluno",
        "necessidade_especial_aluno",
        "matricula",
        "matricula_turma",
    }
)


class Command(BaseEtlCommand):
    """Executa ETL completo ou parcial do domínio ALUNOS_DB."""

    help = "Popula alunos_db a partir do EOL (SQL Server)"
    dominio = "alunos"
    fase_final = 6
    service_class = EtlAlunosService

    def get_modo_escrita(self, tabela: str) -> str:
        """Determina o modo de escrita da tabela (pode ser sobrescrito)."""
        return "upsert" if tabela in _TABELAS_UPSERT else "full_refresh"
