"""Serviço de ETL do domínio Alunos (ALUNOS_DB)."""

import logging
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
from apps.alunos.dtos.model_out import (
    AlunoOut,
    MatriculaOut,
    MatriculaTurmaOut,
    NecessidadeEspecialAlunoOut,
    ResponsavelAlunoOut,
    TipoNecessidadeEspecialOut,
)
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
    TipoNecessidadeEspecial,
)
from apps.core.libs.base_etl_service import BaseEtlService, PipelineMetrics
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
INNER JOIN aluno a ON a.cd_aluno = ra.cd_aluno
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

_SQL_MATRICULA_UNION = """
        SELECT
            cd_matricula, cd_aluno, cd_escola, dt_status_matricula,
            an_letivo, st_matricula
        FROM v_matricula_cotic
        UNION ALL
        SELECT
            cd_matricula, cd_aluno, cd_escola, dt_status_matricula,
            an_letivo, st_matricula
        FROM v_historico_matricula_cotic"""

SQL_MATRICULA = """
SELECT
    mt.cd_matricula AS codigo_matricula,
    mt.cd_aluno AS codigo_aluno,
    mt.codigo_ue, mt.data_status, mt.ano_letivo,
    mt.codigo_situacao_matricula,
    CASE
        WHEN mt.codigo_situacao_matricula = 1  THEN 'Ativo'
        WHEN mt.codigo_situacao_matricula = 2  THEN 'Desistente'
        WHEN mt.codigo_situacao_matricula = 3  THEN 'Transferido'
        WHEN mt.codigo_situacao_matricula = 4  THEN 'Vínculo Indevido'
        WHEN mt.codigo_situacao_matricula = 5  THEN 'Concluído'
        WHEN mt.codigo_situacao_matricula = 6  THEN 'Pendente de Rematrícula'
        WHEN mt.codigo_situacao_matricula = 7  THEN 'Falecido'
        WHEN mt.codigo_situacao_matricula = 8  THEN 'Não Compareceu'
        WHEN mt.codigo_situacao_matricula = 10 THEN 'Rematriculado'
        WHEN mt.codigo_situacao_matricula = 11 THEN 'Deslocamento'
        WHEN mt.codigo_situacao_matricula = 12 THEN 'Cessado'
        WHEN mt.codigo_situacao_matricula = 13 THEN 'Sem continuidade'
        WHEN mt.codigo_situacao_matricula = 14 THEN 'Remanejado Saída'
        WHEN mt.codigo_situacao_matricula = 15 THEN 'Reclassificado Saída'
        WHEN mt.codigo_situacao_matricula = 16 THEN 'Transferido SED'
        WHEN mt.codigo_situacao_matricula = 17 THEN 'Dispensado Ed. Física'
        ELSE 'Fora do domínio liberado pela PRODAM'
    END AS situacao_matricula
FROM (
    SELECT
        cd_matricula, cd_aluno, cd_escola AS codigo_ue,
        dt_status_matricula AS data_status, an_letivo AS ano_letivo,
        st_matricula AS codigo_situacao_matricula,
        ROW_NUMBER() OVER(
            PARTITION BY cd_matricula
            ORDER BY dt_status_matricula DESC, an_letivo DESC
        ) AS rn
    FROM ({inner_union}) AS q_inner
) AS mt
WHERE rn = 1
"""

SQL_MATRICULA_TURMA = """
SELECT
    cd_matricula AS codigo_matricula,
    codigo_turma, numero_chamada, data_situacao
FROM (
    SELECT
        cd_matricula, cd_turma_escola AS codigo_turma,
        nr_chamada_aluno AS numero_chamada, dt_situacao_aluno AS data_situacao
    FROM matricula_turma_escola
    UNION ALL
    SELECT
        cd_matricula, cd_turma_escola AS codigo_turma,
        nr_chamada_aluno AS numero_chamada, dt_situacao_aluno AS data_situacao
    FROM historico_matricula_turma_escola
) AS mt_inner
"""


class EtlAlunosService(BaseEtlService):
    """Orquestra o ETL Turbo para o domínio de Alunos (ALUNOS_DB)."""

    def __init__(
        self,
        eol: EOLService | None = None,
        id_execucao: UUID | None = None,
        repositorio_auditoria: Any | None = None,
        id_min: int | None = None,
        id_max: int | None = None,
        primeiro_run: bool = False,
    ) -> None:
        super().__init__(
            db_alias="alunos_db",
            id_execucao=id_execucao,
            repositorio_auditoria=repositorio_auditoria,
            id_min=id_min,
            id_max=id_max,
            primeiro_run=primeiro_run,
        )
        self.eol = eol or EOLService()

    def popular_tipos_nee(self) -> PipelineMetrics:
        """Fase 1: Tipos de NEEs (Global)."""
        extractor = self.eol.iter_query(SQL_TIPO_NEE)
        return self.sync_table(
            db_table="tipo_necessidade_especial",
            update_fields=[
                "descricao",
                "codigo_estado",
                "ativo",
                "data_cancelamento",
            ],
            extractor_iterator=extractor,
            transform_func=self.create_transformer(
                TipoNecessidadeEspecialIn,
                TipoNecessidadeEspecialOut,
                TipoNecessidadeEspecial,
                "codigo_necessidade_especial",
            ),
            unique_fields=["codigo_necessidade_especial"],
            model_class=TipoNecessidadeEspecial,
        )

    def popular_alunos(self) -> PipelineMetrics:
        """Fase 2: Alunos (Particionado)."""
        sql = self._get_partition_sql(SQL_ALUNO, "a.cd_aluno")
        extractor = self.eol.iter_query(sql)
        return self.sync_table(
            db_table="aluno",
            update_fields=[
                "nome",
                "nome_social",
                "data_nascimento",
                "sexo",
                "nacionalidade",
                "nis",
                "cpf",
                "raca_cor",
            ],
            extractor_iterator=extractor,
            transform_func=self.create_transformer(
                AlunoIn, AlunoOut, Aluno, "codigo_aluno"
            ),
            unique_fields=["codigo_aluno"],
            model_class=Aluno,
        )

    def popular_responsaveis(self) -> PipelineMetrics:
        """Fase 3: Responsáveis (Particionado por cd_aluno)."""
        sql = self._get_partition_sql(SQL_RESPONSAVEL, "a.cd_aluno")
        extractor = self.eol.iter_query(sql)
        return self.sync_table(
            db_table="responsavel_aluno",
            update_fields=[
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
            ],
            extractor_iterator=extractor,
            transform_func=self.create_transformer(
                ResponsavelAlunoIn,
                ResponsavelAlunoOut,
                ResponsavelAluno,
                "codigo_responsavel",
            ),
            unique_fields=["codigo_responsavel"],
            model_class=ResponsavelAluno,
        )

    def popular_nee_alunos(self) -> PipelineMetrics:
        """Fase 4: Vínculo Aluno x NEE (Particionado)."""
        sql = self._get_partition_sql(SQL_NEE_ALUNO, "cd_aluno")
        extractor = self.eol.iter_query(sql)
        return self.sync_table(
            db_table="necessidade_especial_aluno",
            update_fields=["data_inicio", "data_fim"],
            extractor_iterator=extractor,
            transform_func=self.create_transformer(
                NecessidadeEspecialAlunoIn,
                NecessidadeEspecialAlunoOut,
                NecessidadeEspecialAluno,
                "codigo_necessidade_especial_aluno",
            ),
            unique_fields=["codigo_necessidade_especial_aluno"],
            model_class=NecessidadeEspecialAluno,
        )

    def popular_matriculas(self) -> PipelineMetrics:
        """Fase 5: Matrículas (Particionado)."""
        inner = self._get_union_partition_sql(_SQL_MATRICULA_UNION, "cd_aluno")
        sql = SQL_MATRICULA.format(inner_union=inner)
        extractor = self.eol.iter_query(sql)
        return self.sync_table(
            db_table="matricula",
            update_fields=[
                "codigo_ue",
                "ano_letivo",
                "data_status",
                "codigo_situacao_matricula",
                "situacao_matricula",
            ],
            extractor_iterator=extractor,
            transform_func=self.create_transformer(
                MatriculaIn, MatriculaOut, Matricula, "codigo_matricula"
            ),
            unique_fields=["codigo_matricula"],
            model_class=Matricula,
        )

    def popular_matricula_turmas(self) -> PipelineMetrics:
        """Fase 6: Enturmação (Particionado por cd_aluno)."""
        join_sql = f"""
            SELECT mt.* FROM ({SQL_MATRICULA_TURMA}) mt
            INNER JOIN v_matricula_cotic vmc
                ON vmc.cd_matricula = mt.codigo_matricula
        """
        sql = self._get_partition_sql(join_sql, "vmc.cd_aluno")
        extractor = self.eol.iter_query(sql)
        return self.sync_table(
            db_table="matricula_turma",
            update_fields=["numero_chamada", "data_situacao_aluno"],
            extractor_iterator=extractor,
            transform_func=self.create_transformer(
                MatriculaTurmaIn,
                MatriculaTurmaOut,
                MatriculaTurma,
                ["codigo_matricula", "codigo_turma"],
            ),
            unique_fields=["matricula", "codigo_turma"],
            model_class=MatriculaTurma,
        )

    def executar(self, fase_inicial: int = 1) -> dict[str, int]:
        """Executa as fases do ETL com métricas Turbo."""
        metodos = [
            ("tipo_nee", self.popular_tipos_nee),
            ("aluno", self.popular_alunos),
            ("responsavel", self.popular_responsaveis),
            ("nee_aluno", self.popular_nee_alunos),
            ("matricula", self.popular_matriculas),
            ("matricula_turma", self.popular_matricula_turmas),
        ]

        resultados: dict[str, int] = {}
        for i, (nome, metodo) in enumerate(metodos, 1):
            if i >= fase_inicial:
                logger.info("[ETL ALUNOS] Iniciando Fase %d: %s", i, nome)
                m = metodo()
                resultados[nome] = m.total_escritos
                logger.info(
                    "[ETL ALUNOS] Fase %d concluída. Escritos: %d, Lidos: %d",
                    i,
                    m.total_escritos,
                    m.total_lidos,
                )

        return resultados
