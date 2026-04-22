"""Serviço de ETL do domínio PROGRAMAS_DB.

Herda de ``BaseEtlService`` para reutilizar o pipeline genérico:
threadpool producer/consumer, upsert incremental via hash SHA-256
em ``etl_auditoria_linha`` e registro automático em
``etl_execucao_tabela_lida`` / ``etl_execucao_tabela_escrita``.
"""

import logging
from collections.abc import Iterator
from typing import Any
from uuid import UUID

from apps.core.libs.base_etl_service import BaseEtlService, PhaseConfig
from apps.eol_connection.libs.servico_eol import EOLService
from apps.programas.dtos.model_in import (
    ComponenteCurricularProgramaIn,
    MatriculaTurmaProgramaIn,
    TipoProgramaIn,
    TurmaProgramaComponenteCurricularIn,
    TurmaProgramaIn,
)
from apps.programas.enums import ComponenteCurricularEOL, TipoProgramaEOL
from apps.programas.models import (
    ComponenteCurricularPrograma,
    MatriculaTurmaPrograma,
    TipoPrograma,
    TurmaPrograma,
    TurmaProgramaComponenteCurricular,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQLs — Extração
# ---------------------------------------------------------------------------

_TIPOS_PROGRAMA_IN = ", ".join(str(c) for c in TipoProgramaEOL.codigos())
_COMPONENTES_IN = ", ".join(str(c) for c in ComponenteCurricularEOL.codigos())

SQL_TIPO_PROGRAMA = f"""
SELECT
    cd_tipo_programa
  , LTRIM(RTRIM(sg_tipo_programa)) AS sigla
  , LTRIM(RTRIM(dc_tipo_programa)) AS descricao
FROM tipo_programa
WHERE cd_tipo_programa IN ({_TIPOS_PROGRAMA_IN})
"""

SQL_COMPONENTE_CURRICULAR_PROGRAMA = f"""
SELECT
    cc.cd_componente_curricular
  , LTRIM(RTRIM(cc.dc_componente_curricular)) AS nome_componente_curricular
FROM componente_curricular cc
WHERE cc.cd_componente_curricular IN ({_COMPONENTES_IN})
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
FROM turma_escola te
INNER JOIN v_cadastro_unidade_educacao vcue
    ON vcue.cd_unidade_educacao = te.cd_escola
LEFT JOIN tipo_turno tt
    ON tt.cd_tipo_turno = te.cd_tipo_turno
WHERE te.cd_tipo_turma = 3
  AND te.cd_tipo_programa IN ({_TIPOS_PROGRAMA_IN})
ORDER BY te.cd_turma_escola
"""

SQL_TURMA_PROGRAMA_COMPONENTE_CURRICULAR = f"""
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
  AND te.cd_tipo_programa IN ({_TIPOS_PROGRAMA_IN})
  AND gcc.cd_componente_curricular IN ({_COMPONENTES_IN})
ORDER BY tegp.cd_turma_escola
"""

SQL_MATRICULA_TURMA_PROGRAMA = f"""
SELECT
      vm.cd_aluno
    , m.cd_turma_escola
    , gcc.cd_componente_curricular
    , LTRIM(RTRIM(cc.dc_componente_curricular)) AS nome_componente_curricular
    , m.cd_situacao_aluno
    , m.dt_situacao_aluno
    , m.dt_situacao_aluno AS dt_situacao
    , te.an_letivo
    , CAST(te.cd_escola AS VARCHAR(20)) AS codigo_ue
    , CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20)) AS codigo_dre
    , te.cd_tipo_programa
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
    AND te.cd_tipo_programa IN ({_TIPOS_PROGRAMA_IN})
    AND gcc.cd_componente_curricular IN ({_COMPONENTES_IN})
  ORDER BY vm.cd_aluno, te.cd_turma_escola
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
        """Inicializa o serviço de programas conectando ao EOL."""
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
        ]
