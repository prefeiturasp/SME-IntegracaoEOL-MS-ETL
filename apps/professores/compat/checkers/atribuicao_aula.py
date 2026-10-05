"""Verificadores de compatibilidade: AtribuicaoAula (servidor efetivo)."""

from typing import Any

from apps.professores.compat.base import (
    VerificadorBase,
    _formatar_data,
)
from apps.professores.models import AtribuicaoAula
from apps.professores.queries import _PLACEHOLDERS_CARGO, CARGOS_PROFESSOR

_SQL_ATRIBUICAO_AULA = f"""
    SELECT DISTINCT TOP {{limite}}
        aa.cd_atribuicao_aula               AS id,
        sc.cd_registro_funcional            AS codigo_rf,
        aa.cd_unidade_educacao              AS codigo_ue,
        aa.cd_serie_grade                   AS codigo_serie_grade,
        aa.cd_componente_curricular         AS codigo_componente,
        aa.an_atribuicao                    AS ano_atribuicao,
        aa.dt_atribuicao_aula               AS dt_atribuicao,
        aa.dt_disponibilizacao_aulas        AS dt_disponibilizacao,
        aa.cd_motivo_disponibilizacao       AS motivo,
        aa.dt_cancelamento
    FROM atribuicao_aula aa
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
    INNER JOIN v_servidor_cotic sc
        ON sc.cd_servidor = cbs.cd_servidor
    WHERE aa.dt_cancelamento IS NULL
      AND cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
    ORDER BY aa.cd_atribuicao_aula
"""

_SQL_TITULAR_SERVIDOR = f"""
    SELECT DISTINCT TOP {{limite}}
        aa.cd_atribuicao_aula               AS id,
        sc.cd_registro_funcional            AS codigo_rf,
        aa.cd_serie_grade                   AS codigo_serie_grade,
        aa.cd_componente_curricular         AS codigo_componente,
        aa.an_atribuicao                    AS ano_atribuicao,
        aa.cd_turma_escola_grade_programa   AS id_tegp
    FROM atribuicao_aula aa
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
    INNER JOIN v_servidor_cotic sc
        ON sc.cd_servidor = cbs.cd_servidor
    WHERE aa.dt_cancelamento IS NULL
      AND aa.dt_disponibilizacao_aulas IS NULL
      AND cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
    ORDER BY aa.cd_atribuicao_aula
"""

_SQL_PERFIL_SERVIDOR = """
    SELECT DISTINCT TOP {limite}
        sc.cd_registro_funcional            AS codigo_rf,
        turma_escola.cd_escola              AS codigo_escola,
        turma_escola.cd_turma_escola        AS codigo_turma,
        turma_escola.an_letivo              AS ano_letivo,
        stg.cd_serie_grade                  AS codigo_serie_grade,
        aa.cd_componente_curricular         AS codigo_componente,
        aa.dt_cancelamento
    FROM turma_escola
    INNER JOIN serie_turma_escola ste
        ON ste.cd_turma_escola = turma_escola.cd_turma_escola
    INNER JOIN serie_turma_grade stg
        ON stg.cd_turma_escola = ste.cd_turma_escola
    INNER JOIN atribuicao_aula aa
        ON aa.cd_serie_grade = stg.cd_serie_grade
       AND aa.cd_unidade_educacao = turma_escola.cd_escola
       AND aa.an_atribuicao = turma_escola.an_letivo
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
    INNER JOIN v_servidor_cotic sc
        ON sc.cd_servidor = cbs.cd_servidor
    WHERE aa.dt_cancelamento IS NULL
      AND turma_escola.st_turma_escola IN ('O','A','C','E')
    ORDER BY turma_escola.cd_turma_escola
"""


class VerificadorAtribuicaoAula(VerificadorBase):
    """Valida AtribuicaoAula de servidor efetivo."""

    nome = "ProfessorRepository"
    nome_consulta = "BuscaProfessoresAsync"

    def buscar_origem(self, eol: Any, limite: int) -> list[dict[str, Any]]:
        """Busca atribuições de aula ativas na origem."""
        sql = _SQL_ATRIBUICAO_AULA.format(limite=limite)
        linhas = eol.executar_query(sql, list(CARGOS_PROFESSOR))
        return [
            {
                "id": r[0],
                "codigo_rf": str(r[1]).strip(),
                "codigo_ue": str(r[2]).strip(),
                "codigo_serie_grade": r[3],
                "codigo_componente": r[4],
                "ano_atribuicao": r[5],
                "dt_atribuicao": _formatar_data(r[6]),
                "dt_cancelamento": _formatar_data(r[9]),
            }
            for r in linhas
        ]

    def buscar_destino(
        self, linhas_origem: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Busca as mesmas atribuições no professores_db por PK."""
        pks = [r["id"] for r in linhas_origem]
        consulta = (
            AtribuicaoAula.objects.using("professores_db")
            .filter(pk__in=pks)
            .values(
                "id",
                "cargo_base__professor_id",
                "codigo_unidade_educacao",
                "codigo_serie_grade",
                "codigo_componente_curricular",
                "ano_atribuicao",
                "dt_atribuicao_aula",
                "dt_cancelamento",
            )
        )
        return [
            {
                "id": linha["id"],
                "codigo_rf": linha["cargo_base__professor_id"],
                "codigo_ue": linha["codigo_unidade_educacao"],
                "codigo_serie_grade": linha["codigo_serie_grade"],
                "codigo_componente": linha["codigo_componente_curricular"],
                "ano_atribuicao": linha["ano_atribuicao"],
                "dt_atribuicao": _formatar_data(linha["dt_atribuicao_aula"]),
                "dt_cancelamento": _formatar_data(linha["dt_cancelamento"]),
            }
            for linha in consulta
        ]

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Retorna a chave de comparação da atribuição."""
        return (
            linha["id"],
            linha["codigo_rf"],
            linha["codigo_serie_grade"],
            linha["codigo_componente"],
            linha["ano_atribuicao"],
        )


class VerificadorTitularServidor(VerificadorBase):
    """Valida atribuições titulares de servidor efetivo."""

    nome = "ProfessorRepository"
    nome_consulta = "BuscarProfessorTitularPorDisciplinaAsync"

    def buscar_origem(self, eol: Any, limite: int) -> list[dict[str, Any]]:
        """Busca atribuições titulares na origem."""
        sql = _SQL_TITULAR_SERVIDOR.format(limite=limite)
        linhas = eol.executar_query(sql, list(CARGOS_PROFESSOR))
        return [
            {
                "id": r[0],
                "codigo_rf": str(r[1]).strip(),
                "codigo_serie_grade": r[2],
                "codigo_componente": r[3],
                "ano_atribuicao": r[4],
                "id_tegp": r[5],
            }
            for r in linhas
        ]

    def buscar_destino(
        self, linhas_origem: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Busca titulares no professores_db filtrando dt_disponibilizacao."""
        pks = [r["id"] for r in linhas_origem]
        consulta = (
            AtribuicaoAula.objects.using("professores_db")
            .filter(pk__in=pks, dt_disponibilizacao_aulas__isnull=True)
            .values(
                "id",
                "cargo_base__professor_id",
                "codigo_serie_grade",
                "codigo_componente_curricular",
                "ano_atribuicao",
                "codigo_turma_escola_grade_programa",
            )
        )
        return [
            {
                "id": linha["id"],
                "codigo_rf": linha["cargo_base__professor_id"],
                "codigo_serie_grade": linha["codigo_serie_grade"],
                "codigo_componente": linha["codigo_componente_curricular"],
                "ano_atribuicao": linha["ano_atribuicao"],
                "id_tegp": linha["codigo_turma_escola_grade_programa"],
            }
            for linha in consulta
        ]

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Retorna a chave de comparação da atribuição titular."""
        return (
            linha["id"],
            linha["codigo_rf"],
            linha["codigo_serie_grade"],
            linha["codigo_componente"],
        )


class VerificadorPerfilProfServidor(VerificadorBase):
    """Valida o perfil de professor de servidor efetivo."""

    nome = "PerfilSGPRepository"
    nome_consulta = "BuscarInformacoesPerfilProfAsync_servidor"

    def buscar_origem(self, eol: Any, limite: int) -> list[dict[str, Any]]:
        """Busca pares rf/escola/turma na origem via JOIN EOL."""
        sql = _SQL_PERFIL_SERVIDOR.format(limite=limite)
        linhas = eol.executar_query(sql, [])
        return [
            {
                "codigo_rf": str(r[0]).strip(),
                "codigo_escola": str(r[1]).strip(),
                "codigo_turma": r[2],
                "ano_letivo": r[3],
                "codigo_serie_grade": r[4],
                "codigo_componente": r[5],
            }
            for r in linhas
        ]

    def buscar_destino(
        self, linhas_origem: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Reconstrói pares rf/escola/turma via AtribuicaoAula no destino."""
        serie_grades = list({r["codigo_serie_grade"] for r in linhas_origem})
        consulta = (
            AtribuicaoAula.objects.using("professores_db")
            .filter(
                dt_cancelamento__isnull=True,
                codigo_serie_grade__in=serie_grades,
            )
            .values(
                "cargo_base__professor_id",
                "codigo_unidade_educacao",
                "codigo_turma_escola",
                "codigo_serie_grade",
                "ano_atribuicao",
            )
        )
        return [
            {
                "codigo_rf": linha["cargo_base__professor_id"],
                "codigo_escola": linha["codigo_unidade_educacao"],
                "codigo_turma": linha["codigo_turma_escola"],
                "ano_letivo": linha["ano_atribuicao"],
                "codigo_serie_grade": linha["codigo_serie_grade"],
            }
            for linha in consulta
        ]

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Retorna a chave de comparação do perfil."""
        return (
            linha["codigo_rf"],
            linha["codigo_escola"],
            linha["codigo_turma"],
            linha["ano_letivo"],
        )
