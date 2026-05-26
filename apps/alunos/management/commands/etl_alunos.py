"""Comando Django para executar o ETL do domínio ALUNOS_DB."""

from apps.alunos.orquestrador import EtlAlunosOrquestrador
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
        "matricula_ano_letivo",
        "matricula_componente_curricular_ano_letivo",
        "dados_aluno_acompanhamento_escolar",
    }
)


class Command(BaseEtlCommand):
    """Execução do pipeline ETL de Alunos via Celery."""

    help = "Executa pipeline ETL do domínio ALUNOS_DB (Sync ou Celery)"
    dominio = "alunos"
    fase_final = 9
    service_class = EtlAlunosService
    orquestrador_class = EtlAlunosOrquestrador

    def get_modo_escrita(self, tabela: str) -> str:
        """Determina o modo de escrita da tabela."""
        return "upsert" if tabela in _TABELAS_UPSERT else "full_refresh"
