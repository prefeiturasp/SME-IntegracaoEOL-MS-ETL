"""Serviço de ETL do domínio Alunos (ALUNOS_DB)."""

import logging
from collections.abc import Iterator
from typing import Any
from uuid import UUID

from apps.alunos.dtos.model_in import (
    AlunoIn,
    MatriculaIn,
    MatriculaTurmaIn,
    NecessidadeEspecialAlunoIn,
    ResponsavelAlunoIn,
    TipoNecessidadeEspecialIn,
)
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
    TipoNecessidadeEspecial,
)
from apps.core.libs.base_etl_service import BaseEtlService, PhaseConfig
from apps.eol_connection.libs.servico_eol import EOLService

logger = logging.getLogger(__name__)

SQL_TIPO_NEE = """
SELECT
    tp_necessidade_especial AS codigo_necessidade_especial
  , dc_necessidade_especial AS descricao
  , tp_necessidade_especial_estado AS codigo_estado
  , dt_cancelamento
FROM tipo_necessidade_especial
"""

SQL_ALUNO = """
SELECT
     a.cd_aluno AS codigo_aluno
   , v.nm_aluno AS nome
   , v.nm_social_aluno AS nome_social
   , v.dt_nascimento_aluno AS data_nascimento
   , v.cd_sexo_aluno AS sexo
   , a.cd_nacionalidade_aluno AS nacionalidade
   , a.cd_identificacao_social AS nis
   , a.cd_cpf_aluno AS cpf
   , trc.dc_raca_cor AS raca_cor
FROM aluno a
LEFT JOIN v_aluno_cotic v ON a.cd_aluno = v.cd_aluno
LEFT JOIN tipo_raca_cor trc ON trc.tp_raca_cor = a.tp_raca_cor
"""

SQL_RESPONSAVEL = """
SELECT
     ra.cd_identificador_responsavel AS codigo_responsavel
   , ra.cd_aluno AS codigo_aluno
   , ra.tp_pessoa_responsavel AS tipo_responsavel
   , ra.nm_responsavel AS nome
   , ra.cd_cpf_responsavel AS cpf
   , ra.email_responsavel AS email
   , ra.cd_ddd_celular_responsavel AS ddd_celular
   , ra.nr_celular_responsavel AS numero_celular
   , ra.in_autoriza_envio_sms AS autoriza_sms
   , e.nm_logradouro AS logradouro
   , e.cd_cep AS cep
   , ra.dt_fim AS data_fim_vinculo_aluno
FROM responsavel_aluno ra
LEFT JOIN endereco e ON e.ci_endereco = ra.ci_endereco
"""

SQL_NEE_ALUNO = """
SELECT
    cd_identificador_necessidade_especial_aluno
        AS codigo_necessidade_especial_aluno
  , cd_aluno AS codigo_aluno
  , tp_necessidade_especial AS codigo_necessidade_especial
  , dt_inicio
  , dt_fim
FROM necessidade_especial_aluno
"""

SQL_MATRICULA = """
SELECT
    q.cd_matricula, q.cd_aluno, q.codigo_ue, q.data_status, q.ano_letivo,
    q.codigo_situacao_matricula, q.situacao_matricula
FROM (
    SELECT
        cd_matricula
      , cd_aluno
      , cd_escola AS codigo_ue
      , dt_status_matricula AS data_status
      , an_letivo AS ano_letivo
      , st_matricula AS codigo_situacao_matricula
      , CASE
            WHEN st_matricula = 1  THEN 'Ativo'
            WHEN st_matricula = 2  THEN 'Desistente'
            WHEN st_matricula = 3  THEN 'Transferido'
            WHEN st_matricula = 4  THEN 'Vínculo Indevido'
            WHEN st_matricula = 5  THEN 'Concluído'
            WHEN st_matricula = 6  THEN 'Pendente de Rematrícula'
            WHEN st_matricula = 7  THEN 'Falecido'
            WHEN st_matricula = 8  THEN 'Não Compareceu'
            WHEN st_matricula = 10 THEN 'Rematriculado'
            WHEN st_matricula = 11 THEN 'Deslocamento'
            WHEN st_matricula = 12 THEN 'Cessado'
            WHEN st_matricula = 13 THEN 'Sem continuidade'
            WHEN st_matricula = 14 THEN 'Remanejado Saída'
            WHEN st_matricula = 15 THEN 'Reclassificado Saída'
            WHEN st_matricula = 16 THEN 'Transferido SED'
            WHEN st_matricula = 17 THEN 'Dispensado Ed. Física'
            ELSE 'Fora do domínio liberado pela PRODAM'
        END situacao_matricula
    FROM v_matricula_cotic
    UNION ALL
    SELECT
        cd_matricula
      , cd_aluno
      , cd_escola AS codigo_ue
      , dt_status_matricula AS data_status
      , an_letivo AS ano_letivo
      , st_matricula AS codigo_situacao_matricula
      , CASE
            WHEN st_matricula = 1  THEN 'Ativo'
            WHEN st_matricula = 2  THEN 'Desistente'
            WHEN st_matricula = 3  THEN 'Transferido'
            WHEN st_matricula = 4  THEN 'Vínculo Indevido'
            WHEN st_matricula = 5  THEN 'Concluído'
            WHEN st_matricula = 6  THEN 'Pendente de Rematrícula'
            WHEN st_matricula = 7  THEN 'Falecido'
            WHEN st_matricula = 8  THEN 'Não Compareceu'
            WHEN st_matricula = 10 THEN 'Rematriculado'
            WHEN st_matricula = 11 THEN 'Deslocamento'
            WHEN st_matricula = 12 THEN 'Cessado'
            WHEN st_matricula = 13 THEN 'Sem continuidade'
            WHEN st_matricula = 14 THEN 'Remanejado Saída'
            WHEN st_matricula = 15 THEN 'Reclassificado Saída'
            WHEN st_matricula = 16 THEN 'Transferido SED'
            WHEN st_matricula = 17 THEN 'Dispensado Ed. Física'
            ELSE 'Fora do domínio liberado pela PRODAM'
        END situacao_matricula
    FROM v_historico_matricula_cotic
) AS q
ORDER BY q.cd_matricula
"""

SQL_MATRICULA_TURMA = """
WITH CteMatriculaTurma AS (
    SELECT
        mt.cd_matricula
      , mt.cd_turma_escola AS codigo_turma
      , mt.nr_chamada_aluno AS numero_chamada
      , mt.dt_situacao_aluno AS data_situacao
      , m.cd_aluno
    FROM matricula_turma_escola mt
    INNER JOIN v_matricula_cotic m ON m.cd_matricula = mt.cd_matricula
    UNION ALL
    SELECT
        mt.cd_matricula
      , mt.cd_turma_escola AS codigo_turma
      , mt.nr_chamada_aluno AS numero_chamada
      , mt.dt_situacao_aluno AS data_situacao
      , m.cd_aluno
    FROM historico_matricula_turma_escola mt
    INNER JOIN v_historico_matricula_cotic m
        ON m.cd_matricula = mt.cd_matricula
)
SELECT mt.cd_matricula, mt.codigo_turma, mt.numero_chamada, mt.data_situacao
FROM CteMatriculaTurma mt
"""


class EtlAlunosService(BaseEtlService):
    """Serviço de ETL otimizado para Alunos.

    Define as 6 fases do domínio e aponta ``_iter_chunks`` para o EOL.
    Todo o pipeline Producer-Consumer, particionamento e auditoria são
    herdados de ``BaseEtlService``.
    """

    _dominio = "ALUNOS"

    def __init__(
        self,
        db_alias: str,
        id_execucao: UUID | None = None,
        repositorio_auditoria: Any | None = None,
        id_min: int | None = None,
        id_max: int | None = None,
        particao: int = 0,
        total_particoes: int = 1,
        eol: EOLService | None = None,
        primeiro_run: bool = False,
    ) -> None:
        super().__init__(
            db_alias=db_alias,
            id_execucao=id_execucao,
            repositorio_auditoria=repositorio_auditoria,
            id_min=id_min,
            id_max=id_max,
            particao=particao,
            total_particoes=total_particoes,
            primeiro_run=primeiro_run,
        )
        self.eol = eol or EOLService()
        self._fases = self._init_fases()

    def _iter_chunks(self, sql: str) -> Iterator[list[tuple]]:
        """Delega a extração para o EOLService (SQL Server)."""
        return self.eol.iter_query(sql)

    def _init_fases(self) -> list[PhaseConfig]:
        """Define as 6 fases do ETL de Alunos."""
        return [
            PhaseConfig(
                nome="tipo_nee",
                sql=SQL_TIPO_NEE,
                table_name="tipo_necessidade_especial",
                source_table="tipo_necessidade_especial",
                model_class=TipoNecessidadeEspecial,
                dto_in=TipoNecessidadeEspecialIn,
                pk_field="codigo_necessidade_especial",
                update_fields=(
                    "descricao",
                    "codigo_estado",
                    "ativo",
                    "data_cancelamento",
                ),
                unique_fields=("codigo_necessidade_especial",),
                suporta_bulk_insert=False,
            ),
            PhaseConfig(
                nome="aluno",
                sql=self._get_partition_sql(SQL_ALUNO, "a.cd_aluno"),
                table_name="aluno",
                source_table="aluno",
                model_class=Aluno,
                dto_in=AlunoIn,
                pk_field="codigo_aluno",
                update_fields=(
                    "nome",
                    "nome_social",
                    "data_nascimento",
                    "sexo",
                    "nacionalidade",
                    "nis",
                    "cpf",
                    "raca_cor",
                ),
                unique_fields=("codigo_aluno",),
                suporta_bulk_insert=True,
            ),
            PhaseConfig(
                nome="responsavel",
                sql=self._get_partition_sql(SQL_RESPONSAVEL, "ra.cd_aluno"),
                table_name="responsavel_aluno",
                source_table="responsavel_aluno",
                model_class=ResponsavelAluno,
                dto_in=ResponsavelAlunoIn,
                pk_field="codigo_responsavel",
                update_fields=(
                    "tipo_responsavel",
                    "nome",
                    "cpf",
                    "ddd_celular",
                    "numero_celular",
                    "email",
                    "autoriza_sms",
                    "logradouro",
                    "cep",
                    "data_fim_vinculo",
                ),
                unique_fields=("codigo_responsavel",),
                suporta_bulk_insert=True,
            ),
            PhaseConfig(
                nome="nee_aluno",
                sql=self._get_partition_sql(SQL_NEE_ALUNO, "cd_aluno"),
                table_name="necessidade_especial_aluno",
                source_table="necessidade_especial_aluno",
                model_class=NecessidadeEspecialAluno,
                dto_in=NecessidadeEspecialAlunoIn,
                pk_field="codigo_necessidade_especial_aluno",
                update_fields=(
                    "aluno_id",
                    "necessidade_especial_id",
                    "data_inicio",
                    "data_fim",
                ),
                unique_fields=("codigo_necessidade_especial_aluno",),
                suporta_bulk_insert=True,
            ),
            PhaseConfig(
                nome="matricula",
                sql=self._get_partition_sql(SQL_MATRICULA, "q.cd_aluno"),
                table_name="matricula",
                source_table="v_matricula_cotic",
                model_class=Matricula,
                dto_in=MatriculaIn,
                pk_field="codigo_matricula",
                update_fields=(
                    "codigo_ue",
                    "ano_letivo",
                    "data_status",
                    "codigo_situacao_matricula",
                    "situacao_matricula",
                ),
                unique_fields=("codigo_matricula",),
                suporta_bulk_insert=False,
            ),
            PhaseConfig(
                nome="matricula_turma",
                sql=self._get_partition_sql(
                    SQL_MATRICULA_TURMA, "mt.cd_aluno"
                ),
                table_name="matricula_turma",
                source_table="matricula_turma_escola",
                model_class=MatriculaTurma,
                dto_in=MatriculaTurmaIn,
                pk_field=["codigo_matricula", "codigo_turma"],
                update_fields=("numero_chamada", "data_situacao_aluno"),
                unique_fields=("matricula_id", "codigo_turma"),
                suporta_bulk_insert=False,
            ),
        ]
