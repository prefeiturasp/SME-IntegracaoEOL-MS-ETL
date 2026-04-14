"""Verificadores de compatibilidade: TurmaGradeTerritorioExperiencia.

Cobre:
    ComponenteCurricularRepository.ObterComponentesCurricularesTerritorioAtribuidos
    ComponenteCurricularRepository.ObterComponentesCurricularesTerritorioNaoDisponibilizados

Verifica:
  1. Os registros de TurmaGradeTerritorioExperiencia foram replicados com
     os campos corretos.
  2. O JOIN interno TurmaGradeTerritorioExperiencia ↔ SerieTurmaGrade
     ↔ AtribuicaoAula produz os mesmos pares
     (rf, codigo_turma, codigo_componente, codigo_territorio,
      codigo_experiencia) que a consulta original.

Nota: TurmaGradeTerritorioExperiencia usa full-refresh (PK autogerada),
portanto a chave de comparação usa os campos naturais:
(codigo_serie_grade, codigo_componente_curricular,
 codigo_territorio_saber, codigo_experiencia_pedagogica).
"""

from typing import Any

from apps.professores.compat.base import VerificadorBase
from apps.professores.models import TurmaGradeTerritorioExperiencia
from apps.professores.services import _PLACEHOLDERS_CARGO, CARGOS_PROFESSOR

# ---------------------------------------------------------------------------
# Consultas SQL Server (origem)
# ---------------------------------------------------------------------------

_SQL_TERRITORIO = """
    SELECT TOP {limite}
        tgt.cd_serie_grade              AS codigo_serie_grade,
        tgt.cd_componente_curricular    AS codigo_componente,
        tgt.cd_territorio_saber         AS codigo_territorio,
        tgt.cd_experiencia_pedagogica   AS codigo_experiencia,
        tgt.dt_inicio
    FROM turma_grade_territorio_experiencia tgt
    ORDER BY tgt.cd_serie_grade, tgt.cd_componente_curricular
"""

_SQL_TERRITORIO_ATRIBUICAO = f"""
    SELECT DISTINCT TOP {{limite}}
        sc.cd_registro_funcional        AS codigo_rf,
        te.cd_turma_escola              AS codigo_turma,
        tgt.cd_componente_curricular    AS codigo_componente,
        tgt.cd_territorio_saber         AS codigo_territorio,
        tgt.cd_experiencia_pedagogica   AS codigo_experiencia,
        aa.an_atribuicao                AS ano_atribuicao
    FROM turma_escola te
    INNER JOIN serie_turma_escola ste
        ON ste.cd_turma_escola = te.cd_turma_escola
    INNER JOIN serie_turma_grade stg
        ON stg.cd_turma_escola = ste.cd_turma_escola
       AND stg.dt_fim IS NULL
    INNER JOIN turma_grade_territorio_experiencia tgt
        ON tgt.cd_serie_grade = stg.cd_serie_grade
    INNER JOIN atribuicao_aula aa
        ON aa.cd_serie_grade = stg.cd_serie_grade
       AND aa.cd_componente_curricular = tgt.cd_componente_curricular
       AND aa.dt_cancelamento IS NULL
       AND aa.an_atribuicao = te.an_letivo
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
    INNER JOIN v_servidor_cotic sc
        ON sc.cd_servidor = cbs.cd_servidor
    WHERE te.st_turma_escola IN ('O','A','C','E')
      AND cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
    ORDER BY te.cd_turma_escola
"""


# ---------------------------------------------------------------------------
# Verificador 1: dados brutos replicados
# ---------------------------------------------------------------------------


class VerificadorTerritorioReplicado(VerificadorBase):
    """Valida replicação de TurmaGradeTerritorioExperiencia.

    ObterComponentesCurricularesTerritorioAtribuidos — dados brutos.
    Chave natural: (codigo_serie_grade, codigo_componente,
                    codigo_territorio, codigo_experiencia).
    """

    nome = "ComponenteCurricularRepository"
    nome_consulta = "ObterComponentesCurricularesTerritorioAtribuidos"

    def buscar_origem(self, eol: Any, limite: int) -> list[dict[str, Any]]:
        """Busca registros de território/experiência na origem."""
        sql = _SQL_TERRITORIO.format(limite=limite)
        linhas = eol.executar_query(sql, [])
        return [
            {
                "codigo_serie_grade": r[0],
                "codigo_componente": r[1],
                "codigo_territorio": r[2],
                "codigo_experiencia": r[3],
            }
            for r in linhas
        ]

    def buscar_destino(
        self, linhas_origem: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Busca os mesmos registros no professores_db por serie_grade."""
        serie_grades = list({r["codigo_serie_grade"] for r in linhas_origem})
        consulta = (
            TurmaGradeTerritorioExperiencia.objects.using("professores_db")
            .filter(codigo_serie_grade__in=serie_grades)
            .values(
                "codigo_serie_grade",
                "codigo_componente_curricular",
                "codigo_territorio_saber",
                "codigo_experiencia_pedagogica",
            )
        )
        return [
            {
                "codigo_serie_grade": linha["codigo_serie_grade"],
                "codigo_componente": linha["codigo_componente_curricular"],
                "codigo_territorio": linha["codigo_territorio_saber"],
                "codigo_experiencia": linha["codigo_experiencia_pedagogica"],
            }
            for linha in consulta
        ]

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Chave: serie_grade + componente + territorio + experiencia."""
        return (
            linha["codigo_serie_grade"],
            linha["codigo_componente"],
            linha["codigo_territorio"],
            linha["codigo_experiencia"],
        )


# ---------------------------------------------------------------------------
# Verificador 2: cadeia JOIN com AtribuicaoAula
# ---------------------------------------------------------------------------


class VerificadorTerritorioAtribuicao(VerificadorBase):
    """Valida cadeia TurmaGradeTerritorioExperiencia ↔ AtribuicaoAula.

    ObterComponentesCurricularesTerritorioAtribuidos — verifica que o
    JOIN interno no professores_db reproduz os pares
    (rf, turma, componente, territorio, experiencia, ano).

    Chave: (codigo_rf, codigo_turma, codigo_componente, codigo_territorio,
             codigo_experiencia, ano_atribuicao).
    """

    nome = "ComponenteCurricularRepository"
    nome_consulta = "ObterComponentesCurricularesTerritorioAtribuidos_cadeia"

    def buscar_origem(self, eol: Any, limite: int) -> list[dict[str, Any]]:
        """Busca pares rf/turma/territorio na origem via JOINs EOL."""
        sql = _SQL_TERRITORIO_ATRIBUICAO.format(limite=limite)
        linhas = eol.executar_query(sql, list(CARGOS_PROFESSOR))
        return [
            {
                "codigo_rf": str(r[0]).strip(),
                "codigo_turma": r[1],
                "codigo_componente": r[2],
                "codigo_territorio": r[3],
                "codigo_experiencia": r[4],
                "ano_atribuicao": r[5],
            }
            for r in linhas
        ]

    def buscar_destino(
        self, linhas_origem: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Reconstrói pares via JOINs internos do professores_db."""
        from apps.professores.models import AtribuicaoAula, SerieTurmaGrade

        turma_ids = list({r["codigo_turma"] for r in linhas_origem})
        mapa_stg_por_turma: dict[int, list[int]] = {}
        for linha in (
            SerieTurmaGrade.objects.using("professores_db")
            .filter(codigo_turma__in=turma_ids, dt_fim__isnull=True)
            .values("codigo_turma", "codigo_serie_grade")
        ):
            mapa_stg_por_turma.setdefault(linha["codigo_turma"], []).append(
                linha["codigo_serie_grade"]
            )

        todos_serie_grades = [
            sg for sgs in mapa_stg_por_turma.values() for sg in sgs
        ]

        # índice: serie_grade → lista (componente, territorio, experiencia)
        indice_tgt: dict[int, list[tuple]] = {}
        for t in (
            TurmaGradeTerritorioExperiencia.objects.using("professores_db")
            .filter(codigo_serie_grade__in=todos_serie_grades)
            .values(
                "codigo_serie_grade",
                "codigo_componente_curricular",
                "codigo_territorio_saber",
                "codigo_experiencia_pedagogica",
            )
        ):
            indice_tgt.setdefault(t["codigo_serie_grade"], []).append(
                (
                    t["codigo_componente_curricular"],
                    t["codigo_territorio_saber"],
                    t["codigo_experiencia_pedagogica"],
                )
            )

        atribuicoes = (
            AtribuicaoAula.objects.using("professores_db")
            .filter(
                dt_cancelamento__isnull=True,
                codigo_serie_grade__in=todos_serie_grades,
            )
            .values(
                "cargo_base__professor_id",
                "codigo_serie_grade",
                "codigo_componente_curricular",
                "ano_atribuicao",
            )
        )

        # resolve serie_grade → turma (inverso do mapa)
        sg_para_turma = {
            sg: turma
            for turma, sgs in mapa_stg_por_turma.items()
            for sg in sgs
        }

        resultado = []
        for aa in atribuicoes:
            sg = aa["codigo_serie_grade"]
            for comp, terr, exp in indice_tgt.get(sg, []):
                if aa["codigo_componente_curricular"] == comp:
                    resultado.append(
                        {
                            "codigo_rf": aa["cargo_base__professor_id"],
                            "codigo_turma": sg_para_turma.get(sg),
                            "codigo_componente": comp,
                            "codigo_territorio": terr,
                            "codigo_experiencia": exp,
                            "ano_atribuicao": aa["ano_atribuicao"],
                        }
                    )
        return resultado

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Chave: rf + turma + componente + territorio + exp + ano."""
        return (
            linha["codigo_rf"],
            linha["codigo_turma"],
            linha["codigo_componente"],
            linha["codigo_territorio"],
            linha["codigo_experiencia"],
            linha["ano_atribuicao"],
        )
