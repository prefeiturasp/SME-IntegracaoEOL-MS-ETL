"""Comando Django para executar o ETL do domínio ALUNOS_DB."""

from typing import Any

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
    fase_final = 11
    service_class = EtlAlunosService
    orquestrador_class = EtlAlunosOrquestrador

    def add_arguments(self, parser: Any) -> None:
        """Declara argumentos do comando, incluindo o filtro de anos."""
        super().add_arguments(parser)
        parser.add_argument(
            "--anos-letivos",
            type=int,
            nargs="+",
            default=None,
            metavar="ANO",
            help=(
                "Processa apenas matrículas e turmas dos anos letivos "
                "informados. Ex: --anos-letivos 2021 2022 2023 2024 2025"
            ),
        )

    def _extra_service_kwargs(self, **options: Any) -> dict[str, Any]:
        """Repassa o filtro de anos letivos para o service de alunos."""
        anos = options.get("anos_letivos")
        return {"anos_letivos": anos} if anos else {}

    def get_modo_escrita(self, tabela: str) -> str:
        """Determina o modo de escrita da tabela."""
        return "upsert" if tabela in _TABELAS_UPSERT else "full_refresh"
