"""Serviço de ETL do domínio PROGRAMAS_DB."""

import logging
from collections.abc import Iterator
from typing import Any
from uuid import UUID

from apps.core.libs.base_etl_service import BaseEtlService, PhaseConfig
from apps.eol_connection.libs.servico_eol import EOLService
from apps.programas.dtos.model_in import (
    AlunoPapAnoLetivoIn,
    ComponenteCurricularProgramaIn,
    MatriculaTurmaProgramaIn,
    TipoProgramaIn,
    TurmaProgramaComponenteCurricularIn,
    TurmaProgramaIn,
)
from apps.programas.enums import (
    _COMPONENTES_PAP_CONHECIDOS,
    ComponenteCurricularEOL,
)
from apps.programas.models import (
    AlunoPapAnoLetivo,
    AlunoPapAnoLetivoHistorico,
    ComponenteCurricularPrograma,
    MatriculaTurmaPrograma,
    MatriculaTurmaProgramaHistorico,
    TipoPrograma,
    TurmaPrograma,
    TurmaProgramaComponenteCurricular,
)

logger = logging.getLogger(__name__)

_COMPONENTES_IN = ", ".join(str(c) for c in ComponenteCurricularEOL.codigos())
_COMPONENTE_PAEE_SRM = int(
    ComponenteCurricularEOL.PAEE_SALA_RECURSOS_MULTIFUNCIONAIS
)
_COMPONENTES_PAP_VIGENTES_IN = ", ".join(
    str(c) for c in ComponenteCurricularEOL.codigos_pap_vigentes()
)
_COMPONENTES_PAP_IN = ", ".join(str(c) for c in _COMPONENTES_PAP_CONHECIDOS)

SQL_TIPO_PROGRAMA = """
SELECT DISTINCT
    tp.cd_tipo_programa
  , LTRIM(RTRIM(tp.sg_tipo_programa)) AS sigla
  , LTRIM(RTRIM(tp.dc_tipo_programa)) AS descricao
FROM tipo_programa tp
WHERE EXISTS (
    SELECT 1
    FROM turma_escola te_t
    INNER JOIN turma_escola_grade_programa tegp_t
        ON tegp_t.cd_turma_escola = te_t.cd_turma_escola
    INNER JOIN escola_grade eg_t
        ON eg_t.cd_escola_grade = tegp_t.cd_escola_grade
    INNER JOIN grade_componente_curricular gcc_t
        ON gcc_t.cd_grade = eg_t.cd_grade
    WHERE te_t.cd_tipo_programa = tp.cd_tipo_programa
      AND te_t.cd_tipo_turma = 3
      AND tegp_t.dt_fim IS NULL
)
"""

SQL_COMPONENTE_CURRICULAR_PROGRAMA = """
SELECT DISTINCT
    cc.cd_componente_curricular
  , LTRIM(RTRIM(cc.dc_componente_curricular)) AS nome_componente_curricular
FROM componente_curricular cc
INNER JOIN grade_componente_curricular gcc
    ON gcc.cd_componente_curricular = cc.cd_componente_curricular
INNER JOIN escola_grade eg
    ON eg.cd_grade = gcc.cd_grade
INNER JOIN turma_escola_grade_programa tegp
    ON tegp.cd_escola_grade = eg.cd_escola_grade
INNER JOIN turma_escola te
    ON te.cd_turma_escola = tegp.cd_turma_escola
WHERE te.cd_tipo_turma = 3
  AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
  AND tegp.dt_fim IS NULL
  AND cc.dt_cancelamento IS NULL
"""

SQL_TURMA_PROGRAMA = f"""
SELECT
    te.cd_turma_escola
  , LTRIM(RTRIM(te.dc_turma_escola)) AS nome_turma
  , CAST(te.cd_escola AS VARCHAR(20)) AS codigo_ue
  , CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20)) AS codigo_dre
  , te.an_letivo
  , te.cd_tipo_turno
  , tt.dc_exibicao_portal AS descricao_turno
  , te.st_turma_escola AS situacao
  , te.cd_tipo_programa
  , CASE
        WHEN EXISTS (
            SELECT 1
            FROM turma_escola_grade_programa tegp_paee
            INNER JOIN escola_grade eg_paee
                ON eg_paee.cd_escola_grade = tegp_paee.cd_escola_grade
            INNER JOIN grade_componente_curricular gcc_paee
                ON gcc_paee.cd_grade = eg_paee.cd_grade
            WHERE tegp_paee.cd_turma_escola = te.cd_turma_escola
              AND tegp_paee.dt_fim IS NULL
              AND gcc_paee.cd_componente_curricular = {_COMPONENTE_PAEE_SRM}
        ) THEN 'PAEE'
        WHEN EXISTS (
            SELECT 1
            FROM turma_escola_grade_programa tegp_pap
            INNER JOIN escola_grade eg_pap
                ON eg_pap.cd_escola_grade = tegp_pap.cd_escola_grade
            INNER JOIN grade_componente_curricular gcc_pap
                ON gcc_pap.cd_grade = eg_pap.cd_grade
            WHERE tegp_pap.cd_turma_escola = te.cd_turma_escola
              AND tegp_pap.dt_fim IS NULL
              AND gcc_pap.cd_componente_curricular IN ({_COMPONENTES_PAP_IN})
        ) THEN 'PAP'
        ELSE 'OUTROS'
    END AS categoria
  , g_one.descricao_grade
FROM turma_escola te
INNER JOIN v_cadastro_unidade_educacao vcue
    ON vcue.cd_unidade_educacao = te.cd_escola
LEFT JOIN tipo_turno tt
    ON tt.cd_tipo_turno = te.cd_tipo_turno
OUTER APPLY (
    SELECT TOP 1 LTRIM(RTRIM(g.dc_grade)) AS descricao_grade
    FROM turma_escola_grade_programa tegp_g
    INNER JOIN escola_grade eg_g
        ON eg_g.cd_escola_grade = tegp_g.cd_escola_grade
    INNER JOIN grade g
        ON g.cd_grade = eg_g.cd_grade
    WHERE tegp_g.cd_turma_escola = te.cd_turma_escola
      AND tegp_g.dt_fim IS NULL
) AS g_one
WHERE te.cd_tipo_turma = 3
  AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
  AND EXISTS (
      SELECT 1
      FROM turma_escola_grade_programa tegp_f
      WHERE tegp_f.cd_turma_escola = te.cd_turma_escola
        AND tegp_f.dt_fim IS NULL
  )
ORDER BY te.cd_turma_escola
"""

SQL_TURMA_PROGRAMA_COMPONENTE_CURRICULAR = """
SELECT DISTINCT
    tegp.cd_turma_escola
  , gcc.cd_componente_curricular
  , LTRIM(RTRIM(cc.dc_componente_curricular)) AS nome_componente_curricular
FROM turma_escola_grade_programa tegp
INNER JOIN escola_grade egp
    ON egp.cd_escola_grade = tegp.cd_escola_grade
INNER JOIN grade_componente_curricular gcc
    ON gcc.cd_grade = egp.cd_grade
INNER JOIN componente_curricular cc
    ON cc.cd_componente_curricular = gcc.cd_componente_curricular
INNER JOIN turma_escola te
    ON te.cd_turma_escola = tegp.cd_turma_escola
WHERE te.cd_tipo_turma = 3
  AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
  AND tegp.dt_fim IS NULL
  AND cc.dt_cancelamento IS NULL
ORDER BY tegp.cd_turma_escola
"""

SQL_MATRICULA_TURMA_PROGRAMA = """
SELECT
      vm.cd_aluno
    , m.cd_turma_escola
    , gcc.cd_componente_curricular
    , LTRIM(RTRIM(cc.dc_componente_curricular)) AS nome_componente_curricular
    , m.cd_situacao_aluno
    , vm.dt_status_matricula AS dt_matricula
    , m.dt_situacao_aluno AS dt_situacao
    , te.an_letivo
    , CAST(te.cd_escola AS VARCHAR(20)) AS codigo_ue
    , CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20)) AS codigo_dre
  FROM matricula_turma_escola m
  INNER JOIN v_matricula_cotic vm
      ON vm.cd_matricula = m.cd_matricula
  INNER JOIN turma_escola te
      ON te.cd_turma_escola = m.cd_turma_escola
  INNER JOIN v_cadastro_unidade_educacao vcue
      ON vcue.cd_unidade_educacao = te.cd_escola
  INNER JOIN turma_escola_grade_programa tegp
      ON tegp.cd_turma_escola = te.cd_turma_escola
  INNER JOIN escola_grade eg
      ON eg.cd_escola_grade = tegp.cd_escola_grade
  INNER JOIN grade_componente_curricular gcc
      ON gcc.cd_grade = eg.cd_grade
  INNER JOIN componente_curricular cc
      ON cc.cd_componente_curricular = gcc.cd_componente_curricular
  WHERE te.cd_tipo_turma = 3
    AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
    AND tegp.dt_fim IS NULL
    AND cc.dt_cancelamento IS NULL
    AND m.cd_situacao_aluno IN (1, 5, 6, 10, 13)
  ORDER BY vm.cd_aluno, te.cd_turma_escola
"""


SQL_MATRICULA_TURMA_PROGRAMA_HISTORICO = """
SELECT DISTINCT
      vm.cd_aluno
    , m.cd_turma_escola
    , gcc.cd_componente_curricular
    , LTRIM(RTRIM(cc.dc_componente_curricular)) AS nome_componente_curricular
    , CAST(vm.st_matricula AS SMALLINT) AS cd_situacao_aluno
    , vm.dt_status_matricula AS dt_matricula
    , NULL AS dt_situacao
    , te.an_letivo
    , CAST(te.cd_escola AS VARCHAR(20)) AS codigo_ue
    , CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20)) AS codigo_dre
  FROM v_historico_matricula_cotic vm WITH (NOLOCK)
  INNER JOIN historico_matricula_turma_escola m WITH (NOLOCK)
      ON vm.cd_matricula = m.cd_matricula
  INNER JOIN turma_escola te WITH (NOLOCK)
      ON te.cd_turma_escola = m.cd_turma_escola
  INNER JOIN v_cadastro_unidade_educacao vcue WITH (NOLOCK)
      ON vcue.cd_unidade_educacao = te.cd_escola
  INNER JOIN turma_escola_grade_programa tegp WITH (NOLOCK)
      ON tegp.cd_turma_escola = te.cd_turma_escola
  INNER JOIN escola_grade eg WITH (NOLOCK)
      ON eg.cd_escola_grade = tegp.cd_escola_grade
  INNER JOIN grade_componente_curricular gcc WITH (NOLOCK)
      ON gcc.cd_grade = eg.cd_grade
  INNER JOIN componente_curricular cc WITH (NOLOCK)
      ON cc.cd_componente_curricular = gcc.cd_componente_curricular
  WHERE te.cd_tipo_turma = 3
    AND te.st_turma_escola IN ('O', 'A', 'C')
    AND vm.st_matricula IN ('1', '5')
    AND tegp.dt_fim IS NULL
    AND cc.dt_cancelamento IS NULL
  ORDER BY vm.cd_aluno, m.cd_turma_escola
"""

SQL_ALUNO_PAP_ANO_LETIVO = f"""
SELECT DISTINCT
      vm.cd_aluno
    , m.cd_turma_escola
    , gcc.cd_componente_curricular
    , te.an_letivo
    , CAST(te.cd_escola AS VARCHAR(20)) AS codigo_ue
    , CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20)) AS codigo_dre
  FROM matricula_turma_escola m
  INNER JOIN v_matricula_cotic vm
      ON vm.cd_matricula = m.cd_matricula
  INNER JOIN turma_escola te
      ON te.cd_turma_escola = m.cd_turma_escola
  INNER JOIN v_cadastro_unidade_educacao vcue
      ON vcue.cd_unidade_educacao = te.cd_escola
  INNER JOIN turma_escola_grade_programa tegp
      ON tegp.cd_turma_escola = te.cd_turma_escola
  INNER JOIN escola_grade eg
      ON eg.cd_escola_grade = tegp.cd_escola_grade
  INNER JOIN grade_componente_curricular gcc
      ON gcc.cd_grade = eg.cd_grade
  INNER JOIN componente_curricular cc
      ON cc.cd_componente_curricular = gcc.cd_componente_curricular
  WHERE te.cd_tipo_turma = 3
    AND gcc.cd_componente_curricular IN ({_COMPONENTES_PAP_VIGENTES_IN})
    AND te.st_turma_escola IN ('O', 'A', 'C')
    AND tegp.dt_fim IS NULL
    AND cc.dt_cancelamento IS NULL
    AND m.cd_situacao_aluno = 1
"""


SQL_ALUNO_PAP_ANO_LETIVO_HISTORICO = f"""
SELECT DISTINCT
      vm.cd_aluno
    , m.cd_turma_escola
    , gcc.cd_componente_curricular
    , te.an_letivo
    , CAST(te.cd_escola AS VARCHAR(20)) AS codigo_ue
    , CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20)) AS codigo_dre
  FROM v_historico_matricula_cotic vm WITH (NOLOCK)
  INNER JOIN historico_matricula_turma_escola m WITH (NOLOCK)
      ON vm.cd_matricula = m.cd_matricula
  INNER JOIN turma_escola te WITH (NOLOCK)
      ON te.cd_turma_escola = m.cd_turma_escola
  INNER JOIN v_cadastro_unidade_educacao vcue WITH (NOLOCK)
      ON vcue.cd_unidade_educacao = te.cd_escola
  INNER JOIN turma_escola_grade_programa tegp WITH (NOLOCK)
      ON tegp.cd_turma_escola = te.cd_turma_escola
  INNER JOIN escola_grade eg WITH (NOLOCK)
      ON eg.cd_escola_grade = tegp.cd_escola_grade
  INNER JOIN grade_componente_curricular gcc WITH (NOLOCK)
      ON gcc.cd_grade = eg.cd_grade
  INNER JOIN componente_curricular cc WITH (NOLOCK)
      ON cc.cd_componente_curricular = gcc.cd_componente_curricular
  WHERE te.cd_tipo_turma = 3
    AND gcc.cd_componente_curricular IN ({_COMPONENTES_PAP_VIGENTES_IN})
    AND te.st_turma_escola IN ('O', 'A', 'C')
    AND tegp.dt_fim IS NULL
    AND cc.dt_cancelamento IS NULL
    AND vm.st_matricula IN ('1', '5')
"""


class EtlProgramasService(BaseEtlService):
    """Pipeline ETL de Programas (PAP/PAEE)."""

    _dominio = "PROGRAMAS"

    def __init__(
        self,
        db_alias: str,
        id_execucao: UUID | None = None,
        repositorio_auditoria: Any | None = None,
        primeiro_run: bool = False,
        eol: EOLService | None = None,
    ) -> None:
        super().__init__(
            db_alias=db_alias,
            id_execucao=id_execucao,
            repositorio_auditoria=repositorio_auditoria,
            primeiro_run=primeiro_run,
        )
        self.eol = eol or EOLService()
        self._fases = self._init_fases()

    def _iter_chunks(self, sql: str) -> Iterator[list[tuple]]:
        """Lê os dados brutos da origem (MSSQL) em chunks."""
        return self.eol.iter_query(sql)

    def _init_fases(self) -> list[PhaseConfig]:
        """Define as fases do domínio Programas em ordem de dependência."""
        return [
            PhaseConfig(
                nome="tipo_programa",
                sql=SQL_TIPO_PROGRAMA,
                table_name="tipo_programa",
                source_table="tipo_programa",
                model_class=TipoPrograma,
                dto_in=TipoProgramaIn,
                pk_field="codigo_tipo_programa",
                update_fields=("nome", "categoria", "ativo"),
                unique_fields=("codigo_tipo_programa",),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="componente_curricular_programa",
                sql=SQL_COMPONENTE_CURRICULAR_PROGRAMA,
                table_name="componente_curricular_programa",
                source_table="componente_curricular",
                model_class=ComponenteCurricularPrograma,
                dto_in=ComponenteCurricularProgramaIn,
                pk_field="codigo_componente_curricular",
                update_fields=(
                    "nome_componente_curricular",
                    "categoria",
                    "vigente",
                ),
                unique_fields=("codigo_componente_curricular",),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="turma_programa",
                sql=SQL_TURMA_PROGRAMA,
                table_name="turma_programa",
                source_table="turma_escola",
                model_class=TurmaPrograma,
                dto_in=TurmaProgramaIn,
                pk_field="codigo_turma",
                update_fields=(
                    "nome_turma",
                    "codigo_ue",
                    "codigo_dre",
                    "ano_letivo",
                    "tipo_turno",
                    "descricao_turno",
                    "descricao_grade",
                    "situacao",
                    "codigo_tipo_programa",
                    "categoria",
                ),
                unique_fields=("codigo_turma",),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="turma_programa_componente_curricular",
                sql=SQL_TURMA_PROGRAMA_COMPONENTE_CURRICULAR,
                table_name="turma_programa_componente_curricular",
                source_table="turma_escola_grade_programa",
                model_class=TurmaProgramaComponenteCurricular,
                dto_in=TurmaProgramaComponenteCurricularIn,
                pk_field=["codigo_turma", "codigo_componente_curricular"],
                update_fields=("nome_componente_curricular",),
                unique_fields=(
                    "codigo_turma",
                    "codigo_componente_curricular",
                ),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="matricula_turma_programa",
                sql=SQL_MATRICULA_TURMA_PROGRAMA,
                table_name="matricula_turma_programa",
                source_table="matricula_turma_escola",
                model_class=MatriculaTurmaPrograma,
                dto_in=MatriculaTurmaProgramaIn,
                pk_field=[
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ],
                update_fields=(
                    "nome_componente_curricular",
                    "codigo_situacao_matricula",
                    "descricao_situacao_matricula",
                    "data_matricula",
                    "data_situacao",
                    "ano_letivo",
                    "codigo_ue",
                    "codigo_dre",
                    "categoria",
                ),
                unique_fields=(
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="matricula_turma_programa_historico",
                sql=SQL_MATRICULA_TURMA_PROGRAMA_HISTORICO,
                table_name="matricula_turma_programa_historico",
                source_table="v_historico_matricula_cotic",
                model_class=MatriculaTurmaProgramaHistorico,
                dto_in=MatriculaTurmaProgramaIn,
                pk_field=[
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ],
                update_fields=(
                    "nome_componente_curricular",
                    "codigo_situacao_matricula",
                    "descricao_situacao_matricula",
                    "data_matricula",
                    "data_situacao",
                    "ano_letivo",
                    "codigo_ue",
                    "codigo_dre",
                    "categoria",
                ),
                unique_fields=(
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="aluno_pap_ano_letivo",
                sql=SQL_ALUNO_PAP_ANO_LETIVO,
                table_name="aluno_pap_ano_letivo",
                source_table="v_matricula_cotic",
                model_class=AlunoPapAnoLetivo,
                dto_in=AlunoPapAnoLetivoIn,
                pk_field=[
                    "ano_letivo",
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ],
                update_fields=("codigo_ue", "codigo_dre"),
                unique_fields=(
                    "ano_letivo",
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ),
                modo_escrita="upsert",
            ),
            PhaseConfig(
                nome="aluno_pap_ano_letivo_historico",
                sql=SQL_ALUNO_PAP_ANO_LETIVO_HISTORICO,
                table_name="aluno_pap_ano_letivo_historico",
                source_table="v_historico_matricula_cotic",
                model_class=AlunoPapAnoLetivoHistorico,
                dto_in=AlunoPapAnoLetivoIn,
                pk_field=[
                    "ano_letivo",
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ],
                update_fields=("codigo_ue", "codigo_dre"),
                unique_fields=(
                    "ano_letivo",
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ),
                modo_escrita="upsert",
            ),
        ]
