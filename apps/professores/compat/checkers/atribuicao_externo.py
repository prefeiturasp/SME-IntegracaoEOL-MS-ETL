"""Verificadores de compatibilidade: AtribuicaoExterno (professor externo)."""

from typing import Any

from apps.professores.compat.base import (
    VerificadorBase,
    _formatar_data,
)
from apps.professores.models import AtribuicaoExterno

_SQL_ATRIBUICAO_EXTERNO = """
    SELECT DISTINCT TOP {limite}
        ae.cd_atribuicao_externo            AS id,
        pe.cd_cpf_pessoa                    AS cpf_pessoa,
        ae.cd_unidade_educacao              AS codigo_ue,
        ae.cd_serie_grade                   AS codigo_serie_grade,
        ae.cd_componente_curricular         AS codigo_componente,
        ae.an_atribuicao                    AS ano_atribuicao,
        ae.dt_atribuicao                    AS dt_atribuicao,
        ae.dt_disponibilizacao              AS dt_disponibilizacao,
        ae.cd_motivo_disponibilizacao_externo AS motivo,
        ae.dt_cancelamento
    FROM atribuicao_externo ae
    INNER JOIN contrato_externo ce
        ON ce.cd_contrato_externo = ae.cd_contrato_externo
    INNER JOIN pessoa pe
        ON pe.cd_pessoa = ce.cd_pessoa
    WHERE ae.dt_cancelamento IS NULL
      AND ce.dt_cancelamento IS NULL
    ORDER BY ae.cd_atribuicao_externo
"""

_SQL_TITULAR_EXTERNO = """
    SELECT DISTINCT TOP {limite}
        ae.cd_atribuicao_externo            AS id,
        pe.cd_cpf_pessoa                    AS cpf_pessoa,
        ae.cd_serie_grade                   AS codigo_serie_grade,
        ae.cd_componente_curricular         AS codigo_componente,
        ae.an_atribuicao                    AS ano_atribuicao,
        ae.cd_turma_escola_grade_programa   AS id_tegp
    FROM atribuicao_externo ae
    INNER JOIN contrato_externo ce
        ON ce.cd_contrato_externo = ae.cd_contrato_externo
    INNER JOIN pessoa pe
        ON pe.cd_pessoa = ce.cd_pessoa
    WHERE ae.dt_cancelamento IS NULL
      AND ae.dt_disponibilizacao IS NULL
      AND ce.dt_cancelamento IS NULL
    ORDER BY ae.cd_atribuicao_externo
"""

_SQL_PERFIL_EXTERNO = """
    SELECT DISTINCT TOP {limite}
        pe.cd_cpf_pessoa                    AS cpf_pessoa,
        turma_escola.cd_escola              AS codigo_escola,
        turma_escola.cd_turma_escola        AS codigo_turma,
        turma_escola.an_letivo              AS ano_letivo,
        stg.cd_serie_grade                  AS codigo_serie_grade,
        ae.cd_componente_curricular         AS codigo_componente
    FROM atribuicao_externo ae
    INNER JOIN contrato_externo ce
        ON ce.cd_contrato_externo = ae.cd_contrato_externo
    INNER JOIN pessoa pe
        ON pe.cd_pessoa = ce.cd_pessoa
    INNER JOIN serie_turma_grade stg
        ON stg.cd_serie_grade = ae.cd_serie_grade
    INNER JOIN turma_escola
        ON turma_escola.cd_turma_escola = stg.cd_turma_escola
       AND turma_escola.an_letivo = ae.an_atribuicao
    WHERE ae.dt_cancelamento IS NULL
      AND ce.dt_cancelamento IS NULL
      AND turma_escola.st_turma_escola IN ('O','A','C','E')
    ORDER BY turma_escola.cd_turma_escola
"""


class VerificadorAtribuicaoExterno(VerificadorBase):
    """Valida AtribuicaoExterno de professor externo."""

    nome = "ProfessorRepository"
    nome_consulta = "BuscaProfessoresAsync_externo"

    def buscar_origem(self, eol: Any, limite: int) -> list[dict[str, Any]]:
        """Busca atribuições de externos ativas na origem."""
        sql = _SQL_ATRIBUICAO_EXTERNO.format(limite=limite)
        linhas = eol.executar_query(sql, [])
        return [
            {
                "id": r[0],
                "cpf_pessoa": str(r[1]).strip() if r[1] else None,
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
        """Busca as mesmas atribuições externas no professores_db por PK."""
        pks = [r["id"] for r in linhas_origem]
        consulta = (
            AtribuicaoExterno.objects.using("professores_db")
            .filter(pk__in=pks)
            .values(
                "id",
                "contrato_externo__pessoa__cpf",
                "codigo_unidade_educacao",
                "codigo_serie_grade",
                "codigo_componente_curricular",
                "ano_atribuicao",
                "dt_atribuicao",
                "dt_cancelamento",
            )
        )
        return [
            {
                "id": linha["id"],
                "cpf_pessoa": linha["contrato_externo__pessoa__cpf"],
                "codigo_ue": linha["codigo_unidade_educacao"],
                "codigo_serie_grade": linha["codigo_serie_grade"],
                "codigo_componente": linha["codigo_componente_curricular"],
                "ano_atribuicao": linha["ano_atribuicao"],
                "dt_atribuicao": _formatar_data(linha["dt_atribuicao"]),
                "dt_cancelamento": _formatar_data(linha["dt_cancelamento"]),
            }
            for linha in consulta
        ]

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Retorna a chave de comparação da atribuição externa."""
        return (
            linha["id"],
            linha["cpf_pessoa"],
            linha["codigo_serie_grade"],
            linha["codigo_componente"],
            linha["ano_atribuicao"],
        )


class VerificadorTitularExterno(VerificadorBase):
    """Valida titulares de professor externo."""

    nome = "ProfessorRepository"
    nome_consulta = "BuscarProfessorTitularPorDisciplinaAsync_externo"

    def buscar_origem(self, eol: Any, limite: int) -> list[dict[str, Any]]:
        """Busca atribuições titulares de externos na origem."""
        sql = _SQL_TITULAR_EXTERNO.format(limite=limite)
        linhas = eol.executar_query(sql, [])
        return [
            {
                "id": r[0],
                "cpf_pessoa": str(r[1]).strip() if r[1] else None,
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
        """Busca titulares externos no professores_db."""
        pks = [r["id"] for r in linhas_origem]
        consulta = (
            AtribuicaoExterno.objects.using("professores_db")
            .filter(pk__in=pks, dt_disponibilizacao__isnull=True)
            .values(
                "id",
                "contrato_externo__pessoa__cpf",
                "codigo_serie_grade",
                "codigo_componente_curricular",
                "ano_atribuicao",
                "codigo_turma_escola_grade_programa",
            )
        )
        return [
            {
                "id": linha["id"],
                "cpf_pessoa": linha["contrato_externo__pessoa__cpf"],
                "codigo_serie_grade": linha["codigo_serie_grade"],
                "codigo_componente": linha["codigo_componente_curricular"],
                "ano_atribuicao": linha["ano_atribuicao"],
                "id_tegp": linha["codigo_turma_escola_grade_programa"],
            }
            for linha in consulta
        ]

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Retorna a chave de comparação do titular externo."""
        return (
            linha["id"],
            linha["cpf_pessoa"],
            linha["codigo_serie_grade"],
            linha["codigo_componente"],
        )


class VerificadorPerfilProfExterno(VerificadorBase):
    """Valida o perfil de professor externo por CPF."""

    nome = "PerfilSGPRepository"
    nome_consulta = "BuscarInformacoesPerfilProf_externo"

    def buscar_origem(self, eol: Any, limite: int) -> list[dict[str, Any]]:
        """Busca pares cpf/escola/turma na origem via JOIN EOL."""
        sql = _SQL_PERFIL_EXTERNO.format(limite=limite)
        linhas = eol.executar_query(sql, [])
        return [
            {
                "cpf_pessoa": str(r[0]).strip() if r[0] else None,
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
        """Reconstrói pares cpf/escola/turma via AtribuicaoExterno."""
        serie_grades = list({r["codigo_serie_grade"] for r in linhas_origem})
        consulta = (
            AtribuicaoExterno.objects.using("professores_db")
            .filter(
                dt_cancelamento__isnull=True,
                codigo_serie_grade__in=serie_grades,
            )
            .values(
                "contrato_externo__pessoa__cpf",
                "codigo_unidade_educacao",
                "codigo_turma_escola",
                "codigo_serie_grade",
                "ano_atribuicao",
            )
        )
        return [
            {
                "cpf_pessoa": linha["contrato_externo__pessoa__cpf"],
                "codigo_escola": linha["codigo_unidade_educacao"],
                "codigo_turma": linha["codigo_turma_escola"],
                "ano_letivo": linha["ano_atribuicao"],
                "codigo_serie_grade": linha["codigo_serie_grade"],
            }
            for linha in consulta
        ]

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Retorna a chave de comparação do perfil externo."""
        return (
            linha["cpf_pessoa"],
            linha["codigo_escola"],
            linha["codigo_turma"],
            linha["ano_letivo"],
        )
