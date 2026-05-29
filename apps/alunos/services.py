"""Serviço de ETL do domínio Alunos."""

from collections.abc import Iterator
from typing import Any
from uuid import UUID

from apps.alunos.dtos.model_in import (
    AlunoIn,
    DadosAlunoAcompanhamentoEscolarIn,
    MatriculaAnoLetivoIn,
    MatriculaComponenteCurricularAnoLetivoIn,
    MatriculaIn,
    MatriculaTurmaIn,
    NecessidadeEspecialAlunoIn,
    ResponsavelAlunoIn,
    TipoNecessidadeEspecialIn,
)
from apps.alunos.models import (
    Aluno,
    DadosAlunoAcompanhamentoEscolar,
    Matricula,
    MatriculaAnoLetivo,
    MatriculaComponenteCurricularAnoLetivo,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
    TipoNecessidadeEspecial,
)
from apps.alunos.queries import (
    SQL_ALUNO,
    SQL_DADOS_ALUNO_ACOMPANHAMENTO_ESCOLAR,
    SQL_MATRICULA,
    SQL_MATRICULA_ANO_LETIVO,
    SQL_MATRICULA_COMPONENTE_CURRICULAR_ANO_LETIVO,
    SQL_MATRICULA_TURMA,
    SQL_NEE_ALUNO,
    SQL_RESPONSAVEL,
    SQL_TIPO_NEE,
)
from apps.core.libs.base_etl_service import BaseEtlService, PhaseConfig
from apps.eol_connection.libs.servico_eol import EOLService

_FILTROS_ANO_VAZIOS = {
    "/*FILTRO_ANO_LETIVO_ALUNO*/": "",
    "/*FILTRO_ANO_LETIVO_RESPONSAVEL*/": "",
    "/*FILTRO_ANO_LETIVO_NEE*/": "",
    "/*FILTRO_ANO_LETIVO_MATRICULA_ATUAL*/": "",
    "/*FILTRO_ANO_LETIVO_MATRICULA_HISTORICA*/": "",
    "/*FILTRO_ANO_LETIVO_MATRICULA_TURMA_ATUAL*/": "",
    "/*FILTRO_ANO_LETIVO_MATRICULA_TURMA_HISTORICA*/": "",
    "/*FILTRO_ANO_LETIVO_MATRICULA_ANO*/": "",
    "/*FILTRO_ANO_LETIVO_MATRICULA_COMPONENTE*/": "",
    "/*FILTRO_ANO_LETIVO_ACOMPANHAMENTO*/": (
        "and an_letivo = year(getdate())"
    ),
}


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
        fases: list[str] | None = None,
    ) -> None:
        super().__init__(
            db_alias=db_alias,
            id_execucao=id_execucao,
            repositorio_auditoria=repositorio_auditoria,
            primeiro_run=primeiro_run,
            fases=fases,
        )
        self.eol = eol or EOLService()
        self._fases = self._init_fases()

    def _iter_chunks(self, sql: str) -> Iterator[list[tuple]]:
        """Lê os dados brutos da origem em chunks."""
        return self.eol.iter_query(sql)

    def _sql_com_filtro_ano_letivo(self, sql: str) -> str:
        """Substitui os marcadores de filtro de ano pelos valores padrão.

        Args:
            sql: SQL com marcadores de filtro a substituir.

        Returns:
            SQL com os marcadores substituídos pelos valores padrão.
        """
        for marcador, filtro in _FILTROS_ANO_VAZIOS.items():
            sql = sql.replace(marcador, filtro)
        return sql

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
                sql=self._sql_com_filtro_ano_letivo(SQL_ALUNO),
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
                    "nome_mae",
                    "raca_cor",
                    "cns",
                    "data_atualizacao_contato",
                    "possui_deficiencia",
                ),
                unique_fields=("codigo_aluno",),
                suporta_bulk_insert=True,
            ),
            PhaseConfig(
                nome="responsavel_aluno",
                sql=self._sql_com_filtro_ano_letivo(SQL_RESPONSAVEL),
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
                sql=self._sql_com_filtro_ano_letivo(SQL_NEE_ALUNO),
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
                sql=self._sql_com_filtro_ano_letivo(SQL_MATRICULA),
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
                sql=self._sql_com_filtro_ano_letivo(SQL_MATRICULA_TURMA),
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
            PhaseConfig(
                nome="matricula_ano_letivo",
                sql=self._sql_com_filtro_ano_letivo(SQL_MATRICULA_ANO_LETIVO),
                table_name="matricula_ano_letivo",
                source_table="v_matricula_cotic",
                model_class=MatriculaAnoLetivo,
                dto_in=MatriculaAnoLetivoIn,
                pk_field=[
                    "codigo_dre",
                    "codigo_ue",
                    "tipo_escola",
                    "ano_letivo",
                    "modalidade",
                    "ano",
                    "turma",
                ],
                update_fields=("quantidade",),
                unique_fields=(
                    "codigo_dre",
                    "codigo_ue",
                    "tipo_escola",
                    "ano_letivo",
                    "modalidade",
                    "ano",
                    "turma",
                ),
                suporta_bulk_insert=True,
            ),
            PhaseConfig(
                nome="matricula_componente_curricular_ano_letivo",
                sql=self._sql_com_filtro_ano_letivo(
                    SQL_MATRICULA_COMPONENTE_CURRICULAR_ANO_LETIVO
                ),
                table_name=("matricula_componente_curricular_ano_letivo"),
                source_table="v_matricula_cotic",
                model_class=MatriculaComponenteCurricularAnoLetivo,
                dto_in=MatriculaComponenteCurricularAnoLetivoIn,
                pk_field=[
                    "codigo_ue",
                    "codigo_dre",
                    "ano_letivo",
                    "modalidade",
                    "componente_curricular_id",
                    "ano",
                ],
                update_fields=("quantidade",),
                unique_fields=(
                    "codigo_ue",
                    "codigo_dre",
                    "ano_letivo",
                    "modalidade",
                    "componente_curricular_id",
                    "ano",
                ),
                suporta_bulk_insert=True,
            ),
            PhaseConfig(
                nome="dados_aluno_acompanhamento_escolar",
                sql=self._sql_com_filtro_ano_letivo(
                    SQL_DADOS_ALUNO_ACOMPANHAMENTO_ESCOLAR
                ),
                table_name="dados_aluno_acompanhamento_escolar",
                source_table="v_aluno_cotic",
                model_class=DadosAlunoAcompanhamentoEscolar,
                dto_in=DadosAlunoAcompanhamentoEscolarIn,
                pk_field=[
                    "codigo_aluno",
                    "codigo_turma",
                    "tipo_responsavel",
                ],
                update_fields=(
                    "nome",
                    "nome_social",
                    "nome_responsavel",
                    "cpf_responsavel",
                    "data_nascimento",
                    "descricao_tipo_escola",
                    "codigo_dre",
                    "sigla_dre",
                    "codigo_ue",
                    "unidade_educacional",
                    "turma",
                    "codigo_tipo_escola",
                    "situacao_matricula",
                    "data_situacao_matricula",
                    "codigo_etapa_ensino",
                    "codigo_ciclo_ensino",
                    "serie_resumida",
                    "codigo_modalidade_turma",
                ),
                unique_fields=(
                    "codigo_aluno",
                    "codigo_turma",
                    "tipo_responsavel",
                ),
                suporta_bulk_insert=True,
            ),
        ]
