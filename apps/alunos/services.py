"""Serviço de ETL do domínio Alunos."""

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
   , a.nm_mae_aluno AS nome_mae
   , a.cd_nacionalidade_aluno AS nacionalidade
   , a.cd_identificacao_social AS nis
   , a.cd_cpf_aluno AS cpf
   , csus.nr_cns AS cns
   , trc.dc_raca_cor AS raca_cor
   , CASE
        WHEN EXISTS (
            SELECT 1
            FROM necessidade_especial_aluno nea
            WHERE nea.cd_aluno = a.cd_aluno
              AND (nea.dt_fim IS NULL OR nea.dt_fim >= GETDATE())
        ) THEN 1
        ELSE 0
     END AS possui_deficiencia
FROM aluno a
LEFT JOIN v_aluno_cotic v ON a.cd_aluno = v.cd_aluno
LEFT JOIN tipo_raca_cor trc ON trc.tp_raca_cor = a.tp_raca_cor
LEFT JOIN aluno_Codigo_Sus csus
    ON csus.cd_aluno = a.cd_aluno
   AND (csus.dt_fim IS NULL OR csus.dt_fim >= GETDATE())
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
   , e.ci_endereco AS endereco_id
   , e.cd_nr_endereco AS numero_endereco
   , e.dc_complemento_endereco AS complemento
   , e.nm_bairro AS bairro
   , e.nm_logradouro AS logradouro
   , e.cd_cep AS cep
   , e.nm_municipio AS nome_municipio
   , e.sg_uf AS sigla_uf
   , e.dc_tp_logradouro AS tipo_logradouro
   , ra.dt_atualizacao_tabela AS data_atualizacao_tabela
   , ra.dt_fim AS data_fim_vinculo_aluno
FROM responsavel_aluno ra
LEFT JOIN endereco e ON e.ci_endereco = ra.ci_endereco
"""

SQL_NEE_ALUNO = """
SELECT
    nee.cd_identificador_necessidade_especial_aluno
        AS codigo_necessidade_especial_aluno
  , nee.cd_aluno AS codigo_aluno
  , nee.tp_necessidade_especial AS codigo_necessidade_especial
  , nee.dt_inicio
  , nee.dt_fim
  , recurso.cd_tipo_recurso AS codigo_tipo_recurso
  , tipo_recurso.dc_tipo_recurso AS descricao_tipo_recurso
FROM necessidade_especial_aluno nee
OUTER APPLY (
    SELECT TOP 1 r.cd_tipo_recurso
    FROM recurso_aluno r
    WHERE r.cd_aluno = nee.cd_aluno
      AND (r.dt_fim IS NULL OR r.dt_fim >= GETDATE())
    ORDER BY r.dt_inicio DESC, r.cd_tipo_recurso
) recurso
LEFT JOIN tipo_recurso_aluno tipo_recurso
    ON tipo_recurso.cd_tipo_recurso = recurso.cd_tipo_recurso
"""

SQL_MATRICULA = """
WITH Combined AS (
    SELECT
        cd_matricula
      , cd_aluno
      , cd_escola AS codigo_ue
      , dt_status_matricula AS data_situacao_matricula
      , dt_status_matricula AS data_situacao_matricula_data_hora
      , an_letivo AS ano_letivo
      , st_matricula AS codigo_situacao_matricula
      , 0 AS prioridade
      , CAST(1 AS bit) AS origem_atual
    FROM v_matricula_cotic
    UNION ALL
    SELECT
        cd_matricula
      , cd_aluno
      , cd_escola AS codigo_ue
      , dt_status_matricula AS data_situacao_matricula
      , dt_status_matricula AS data_situacao_matricula_data_hora
      , an_letivo AS ano_letivo
      , st_matricula AS codigo_situacao_matricula
      , 1 AS prioridade
      , CAST(0 AS bit) AS origem_atual
    FROM v_historico_matricula_cotic
), Ranked AS (
    SELECT
        cd_matricula, cd_aluno, codigo_ue, data_situacao_matricula,
        data_situacao_matricula_data_hora, ano_letivo,
        codigo_situacao_matricula, origem_atual,
        ROW_NUMBER() OVER (
            PARTITION BY cd_matricula ORDER BY prioridade
        ) AS rn
    FROM Combined
)
SELECT cd_matricula, cd_aluno, codigo_ue, data_situacao_matricula,
       data_situacao_matricula_data_hora, ano_letivo,
       codigo_situacao_matricula, origem_atual
FROM Ranked
WHERE rn = 1
ORDER BY cd_matricula
"""

SQL_MATRICULA_TURMA = """
SELECT mt.cd_matricula, mt.cd_turma_escola AS codigo_turma,
       mt.nr_chamada_aluno AS numero_chamada,
       mt.dt_situacao_aluno AS data_situacao,
       mt.dt_situacao_aluno AS data_situacao_data_hora,
       mt.cd_situacao_aluno AS codigo_situacao_aluno,
       te.cd_tipo_turma AS codigo_tipo_turma,
       mt.dt_atlz_tab AS data_atualizacao_tabela
FROM matricula_turma_escola mt
LEFT JOIN turma_escola te ON te.cd_turma_escola = mt.cd_turma_escola
UNION ALL
SELECT mt.cd_matricula, mt.cd_turma_escola AS codigo_turma,
       mt.nr_chamada_aluno AS numero_chamada,
       mt.dt_situacao_aluno AS data_situacao,
       mt.dt_situacao_aluno AS data_situacao_data_hora,
       mt.cd_situacao_aluno AS codigo_situacao_aluno,
       te.cd_tipo_turma AS codigo_tipo_turma,
       mt.dt_atlz_tab AS data_atualizacao_tabela
FROM historico_matricula_turma_escola mt
LEFT JOIN turma_escola te ON te.cd_turma_escola = mt.cd_turma_escola
WHERE NOT EXISTS (
    SELECT 1 FROM matricula_turma_escola c
    WHERE c.cd_matricula = mt.cd_matricula
      AND c.cd_turma_escola = mt.cd_turma_escola
)
"""


class EtlAlunosService(BaseEtlService):
    """Pipeline ETL de Alunos."""

    _dominio = "ALUNOS"

    def __init__(
        self,
        db_alias: str,
        id_execucao: UUID | None = None,
        repositorio_auditoria: Any | None = None,
        eol: EOLService | None = None,
        primeiro_run: bool = False,
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
        """Lê os dados brutos da origem em chunks."""
        return self.eol.iter_query(sql)

    def _init_fases(self) -> list[PhaseConfig]:
        """Define as fases do domínio Alunos."""
        return [
            PhaseConfig(
                nome="tipo_necessidade_especial",
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
                suporta_bulk_insert=True,
                truncate_on_full_sync=True,
            ),
            PhaseConfig(
                nome="aluno",
                sql=SQL_ALUNO,
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
                    "nome_mae",
                    "cns",
                    "possui_deficiencia",
                ),
                unique_fields=("codigo_aluno",),
                suporta_bulk_insert=True,
            ),
            PhaseConfig(
                nome="responsavel_aluno",
                sql=SQL_RESPONSAVEL,
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
                    "endereco_id",
                    "numero_endereco",
                    "complemento",
                    "bairro",
                    "logradouro",
                    "cep",
                    "nome_municipio",
                    "sigla_uf",
                    "tipo_logradouro",
                    "data_atualizacao_tabela",
                    "data_fim_vinculo",
                ),
                unique_fields=("codigo_responsavel",),
                suporta_bulk_insert=True,
            ),
            PhaseConfig(
                nome="nee_aluno",
                sql=SQL_NEE_ALUNO,
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
                    "codigo_tipo_recurso",
                    "descricao_tipo_recurso",
                ),
                unique_fields=("codigo_necessidade_especial_aluno",),
                suporta_bulk_insert=True,
            ),
            PhaseConfig(
                nome="matricula",
                sql=SQL_MATRICULA,
                table_name="matricula",
                source_table="v_matricula_cotic",
                model_class=Matricula,
                dto_in=MatriculaIn,
                pk_field="codigo_matricula",
                update_fields=(
                    "codigo_ue",
                    "ano_letivo",
                    "data_situacao_matricula",
                    "data_situacao_matricula_data_hora",
                    "codigo_situacao_matricula",
                    "situacao_matricula",
                    "origem_atual",
                ),
                unique_fields=("codigo_matricula",),
                suporta_bulk_insert=False,
            ),
            PhaseConfig(
                nome="matricula_turma",
                sql=SQL_MATRICULA_TURMA,
                table_name="matricula_turma",
                source_table="matricula_turma_escola",
                model_class=MatriculaTurma,
                dto_in=MatriculaTurmaIn,
                pk_field=["codigo_matricula", "codigo_turma"],
                update_fields=(
                    "numero_chamada",
                    "data_situacao_aluno",
                    "data_situacao_aluno_data_hora",
                    "codigo_situacao_aluno",
                    "codigo_tipo_turma",
                    "data_atualizacao_tabela",
                ),
                unique_fields=("codigo_matricula", "codigo_turma"),
                suporta_bulk_insert=False,
            ),
        ]
