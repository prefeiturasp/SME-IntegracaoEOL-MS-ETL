"""Verificadores de compatibilidade: TurmaEscola e TurmaEscolaGradePrograma.

Cobre:
    ProfessorRepository.VerificaSeEhTurmaDeProgramaAsync
        cd_tipo_turma deve estar replicado para filtrar cd_tipo_turma != 1.

    ProfessorRepository.BuscaTurmasAtribuidasProfessorAsync
        dt_inicio_turma deve estar replicado (DataInicioAtribuicao).

    ProfessorRepository.VerificaSeTemAtribuicaoNaTurmaDeProgramaNaDisciplina
        Requer TurmaEscolaGradePrograma.codigo_turma para JOIN interno.

    PerfilSGPRepository.BuscarInformacoesPerfilProfAutoCompleteAsync
        TurmaEscola.status + dt_fim para filtros de turma ativa.
"""

from typing import Any

from apps.professores.compat.base import (
    VerificadorBase,
    _formatar_data,
)
from apps.professores.models import TurmaEscola, TurmaEscolaGradePrograma

# ---------------------------------------------------------------------------
# Consultas SQL Server (origem)
# ---------------------------------------------------------------------------

_SQL_TURMA = """
    SELECT TOP {limite}
        cd_turma_escola     AS codigo_turma,
        cd_escola           AS codigo_escola,
        an_letivo           AS ano_letivo,
        st_turma_escola     AS status,
        cd_tipo_turma       AS tipo_turma,
        dt_inicio_turma,
        dt_fim_turma,
        dt_fim
    FROM turma_escola
    ORDER BY cd_turma_escola
"""

_SQL_TEGP = """
    SELECT TOP {limite}
        cd_turma_escola_grade_programa  AS id,
        cd_turma_escola                 AS codigo_turma,
        cd_escola_grade                 AS codigo_escola_grade,
        dt_fim
    FROM turma_escola_grade_programa
    ORDER BY cd_turma_escola_grade_programa
"""


# ---------------------------------------------------------------------------
# Verificador 1: VerificaSeEhTurmaDeProgramaAsync
# ---------------------------------------------------------------------------


class VerificadorTurmaEscola(VerificadorBase):
    """Valida TurmaEscola — tipo_turma, dt_inicio_turma, status.

    VerificaSeEhTurmaDeProgramaAsync (tipo_turma != 1) e
    BuscaTurmasAtribuidasProfessorAsync (dt_inicio_turma).

    Chave: (codigo_turma, codigo_escola, ano_letivo, status, tipo_turma,
            dt_inicio_turma).
    """

    nome = "ProfessorRepository"
    nome_consulta = "VerificaSeEhTurmaDeProgramaAsync"

    def buscar_origem(self, eol: Any, limite: int) -> list[dict[str, Any]]:
        """Busca turmas com tipo_turma e dt_inicio na origem."""
        sql = _SQL_TURMA.format(limite=limite)
        linhas = eol.executar_query(sql, [])
        return [
            {
                "codigo_turma": r[0],
                "codigo_escola": str(r[1]).strip(),
                "ano_letivo": r[2],
                "status": r[3] or "",
                "tipo_turma": r[4],
                "dt_inicio_turma": _formatar_data(r[5]),
                "dt_fim_turma": _formatar_data(r[6]),
                "dt_fim": _formatar_data(r[7]),
            }
            for r in linhas
        ]

    def buscar_destino(
        self, linhas_origem: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Busca as mesmas turmas no professores_db por PK."""
        pks = [r["codigo_turma"] for r in linhas_origem]
        consulta = (
            TurmaEscola.objects.using("professores_db")
            .filter(pk__in=pks)
            .values(
                "codigo_turma",
                "codigo_escola",
                "ano_letivo",
                "status",
                "tipo_turma",
                "dt_inicio_turma",
                "dt_fim_turma",
                "dt_fim",
            )
        )
        return [
            {
                "codigo_turma": linha["codigo_turma"],
                "codigo_escola": linha["codigo_escola"],
                "ano_letivo": linha["ano_letivo"],
                "status": linha["status"],
                "tipo_turma": linha["tipo_turma"],
                "dt_inicio_turma": _formatar_data(linha["dt_inicio_turma"]),
                "dt_fim_turma": _formatar_data(linha["dt_fim_turma"]),
                "dt_fim": _formatar_data(linha["dt_fim"]),
            }
            for linha in consulta
        ]

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Chave: turma + escola + ano + status + tipo + dt_inicio."""
        return (
            linha["codigo_turma"],
            linha["codigo_escola"],
            linha["ano_letivo"],
            linha["status"],
            linha["tipo_turma"],
            linha["dt_inicio_turma"],
        )


# ---------------------------------------------------------------------------
# Verificador 2: VerificaSeTemAtribuicaoNaTurmaDeProgramaNaDisciplina
# ---------------------------------------------------------------------------


class VerificadorTurmaEscolaGradePrograma(VerificadorBase):
    """Valida TurmaEscolaGradePrograma — join de turmas de programa.

    VerificaSeTemAtribuicaoNaTurmaDeProgramaNaDisciplinaAsync.
    Chave: (id, codigo_turma, codigo_escola_grade).
    """

    nome = "ProfessorRepository"
    nome_consulta = "VerificaSeTemAtribuicaoNaTurmaDeProgramaNaDisciplina"

    def buscar_origem(self, eol: Any, limite: int) -> list[dict[str, Any]]:
        """Busca registros de grade/programa de turma na origem."""
        sql = _SQL_TEGP.format(limite=limite)
        linhas = eol.executar_query(sql, [])
        return [
            {
                "id": r[0],
                "codigo_turma": r[1],
                "codigo_escola_grade": r[2],
                "dt_fim": _formatar_data(r[3]),
            }
            for r in linhas
        ]

    def buscar_destino(
        self, linhas_origem: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Busca as mesmas grades de programa no professores_db."""
        pks = [r["id"] for r in linhas_origem]
        consulta = (
            TurmaEscolaGradePrograma.objects.using("professores_db")
            .filter(pk__in=pks)
            .values(
                "codigo",
                "codigo_turma",
                "codigo_escola_grade",
                "dt_fim",
            )
        )
        return [
            {
                "id": linha["codigo"],
                "codigo_turma": linha["codigo_turma"],
                "codigo_escola_grade": linha["codigo_escola_grade"],
                "dt_fim": _formatar_data(linha["dt_fim"]),
            }
            for linha in consulta
        ]

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Chave: id + codigo_turma + codigo_escola_grade."""
        return (
            linha["id"],
            linha["codigo_turma"],
            linha["codigo_escola_grade"],
        )
