"""Modelos do app professores - banco destino PROFESSORES_DB."""

import datetime

from django.db import models

_HELP_UE = "ID da unidade educacional — ref. domínio institucional."
_HELP_GRADE = "ID da escola_grade — ref. domínio pedagógico."
_HELP_COMP = "ID do componente curricular — ref. domínio curricular."
_HELP_TURMA = "ID da turma escolar — ref. domínio pedagógico."


def _data_chave_padrao() -> datetime.datetime:
    """Retorna data sentinela para chaves sem data informada."""
    return datetime.datetime(1900, 1, 1, tzinfo=datetime.UTC)


class Professor(models.Model):
    """Servidor público com perfil de professor na rede municipal."""

    codigo_rf = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=200)
    nome_social = models.CharField(
        max_length=200,
        null=True,  # NOSONAR nome_social:models:Professor
        blank=True,
    )
    cpf = models.CharField(
        max_length=14,
        null=True,  # NOSONAR cpf:models:Professor
        blank=True,
        help_text=(
            "cd_cpf_pessoa do servidor — retornado como CPF"
            " em consultas de perfil."
        ),
    )

    class Meta:

        app_label = "professores"
        db_table = "professor"
        verbose_name = "professor"
        verbose_name_plural = "professores"

    def __str__(self) -> str:
        return f"{self.codigo_rf} - {self.nome}"


class CargoBaseServidor(models.Model):
    """Nomeação/cargo base do servidor no quadro funcional."""

    id = models.BigAutoField(primary_key=True)
    professor = models.ForeignKey(
        Professor,
        on_delete=models.CASCADE,
        related_name="cargos_base",
        db_column="codigo_rf",
        db_constraint=False,
    )
    codigo_cargo = models.IntegerField(
        help_text="ID do cargo — ref. domínio RH/funcional.",
    )
    descricao_cargo = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Descrição do cargo (dc_cargo via JOIN cargo).",
    )
    situacao_funcional = models.IntegerField(
        null=True,
        blank=True,
        help_text=(
            "cd_situacao_funcional — usado em VerificarValidadeProfessorAsync"
            " (filtro situacao = 6)."
        ),
    )
    dt_posse = models.DateField(null=True, blank=True)
    dt_fim_nomeacao = models.DateField(null=True, blank=True)
    dt_cancelamento = models.DateField(null=True, blank=True)

    class Meta:

        app_label = "professores"
        db_table = "cargo_base_servidor"
        verbose_name = "cargo base do servidor"
        verbose_name_plural = "cargos base dos servidores"
        indexes = [
            models.Index(fields=["professor"], name="idx_cbs_professor"),
            models.Index(fields=["codigo_cargo"], name="idx_cbs_cargo"),
            models.Index(
                fields=["dt_fim_nomeacao"],
                name="idx_cbs_fim_nomeacao",
            ),
        ]

    def __str__(self) -> str:
        return f"CargoBase #{self.pk} RF={self.professor_id}"


class LotacaoServidor(models.Model):
    """Lotação do servidor em unidade educacional."""

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="lotacoes",
        db_constraint=False,
    )
    codigo_unidade_educacao = models.CharField(
        max_length=20,
        help_text=_HELP_UE,
    )
    dt_inicio = models.DateField(null=True, blank=True)
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:

        app_label = "professores"
        db_table = "lotacao_servidor"
        verbose_name = "lotação do servidor"
        verbose_name_plural = "lotações dos servidores"
        indexes = [
            models.Index(fields=["codigo_unidade_educacao"], name="idx_ls_ue"),
            models.Index(fields=["dt_fim"], name="idx_ls_dt_fim"),
        ]


class CargoSobrepostoServidor(models.Model):
    """Cargo sobreposto exercido sobre o cargo base."""

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="cargos_sobrepostos",
        db_constraint=False,
    )
    codigo_cargo = models.IntegerField(
        help_text="ID do cargo sobreposto — ref. domínio RH/funcional.",
    )
    codigo_unidade_local_servico = models.CharField(
        max_length=20,
        help_text="ID da UE onde o cargo sobreposto é exercido.",
    )
    dt_fim_cargo_sobreposto = models.DateField(null=True, blank=True)

    class Meta:

        app_label = "professores"
        db_table = "cargo_sobreposto_servidor"
        verbose_name = "cargo sobreposto do servidor"
        verbose_name_plural = "cargos sobrepostos dos servidores"
        indexes = [
            models.Index(
                fields=["dt_fim_cargo_sobreposto"],
                name="idx_css_dt_fim",
            ),
        ]


class FuncaoAtividadeCargoServidor(models.Model):
    """Função de atividade exercida pelo servidor em determinada unidade."""

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="funcoes_atividade",
        db_constraint=False,
    )
    codigo_unidade_local_servico = models.CharField(
        max_length=20,
        help_text="ID da UE onde a função é exercida.",
    )
    dt_fim_funcao_atividade = models.DateField(null=True, blank=True)

    class Meta:

        app_label = "professores"
        db_table = "funcao_atividade_cargo_servidor"
        verbose_name = "função de atividade do cargo do servidor"
        verbose_name_plural = "funções de atividade dos cargos dos servidores"


class LaudoMedico(models.Model):
    """Registro de laudo médico que impede atribuição de aulas ao servidor."""

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="laudos_medicos",
        db_constraint=False,
    )

    class Meta:

        app_label = "professores"
        db_table = "laudo_medico"
        verbose_name = "laudo médico"
        verbose_name_plural = "laudos médicos"


class Pessoa(models.Model):
    """Pessoa física que atua como professor contratado (externo)."""

    codigo_pessoa = models.BigIntegerField(primary_key=True)
    cpf = models.CharField(max_length=14, unique=True)
    nome = models.CharField(max_length=200)
    nome_social = models.CharField(
        max_length=200,
        null=True,  # NOSONAR nome_social:models:Pessoa
        blank=True,
    )

    class Meta:

        app_label = "professores"
        db_table = "pessoa"
        verbose_name = "pessoa"
        verbose_name_plural = "pessoas"

    def __str__(self) -> str:
        return f"{self.cpf} - {self.nome}"


class ContratoExterno(models.Model):
    """Contrato de professor externo/terceirizado com a rede municipal."""

    codigo_contrato = models.BigIntegerField(primary_key=True)
    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.CASCADE,
        related_name="contratos",
        db_constraint=False,
    )
    codigo_tipo_funcao = models.IntegerField(
        help_text="ID do tipo de função do funcionário externo.",
    )
    codigo_unidade_educacao = models.CharField(
        max_length=20,
        help_text=_HELP_UE,
    )
    dt_cancelamento = models.DateField(null=True, blank=True)
    codigo_motivo_desligamento = models.IntegerField(null=True, blank=True)

    class Meta:

        app_label = "professores"
        db_table = "contrato_externo"
        verbose_name = "contrato externo"
        verbose_name_plural = "contratos externos"
        indexes = [
            models.Index(fields=["codigo_unidade_educacao"], name="idx_ce_ue"),
            models.Index(
                fields=["dt_cancelamento"],
                name="idx_ce_cancelamento",
            ),
        ]


class AtribuicaoAula(models.Model):
    """Atribuição de aulas ao professor efetivo (servidor concursado)."""

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="atribuicoes",
        db_constraint=False,
    )
    codigo_unidade_educacao = models.CharField(
        max_length=20,
        help_text=_HELP_UE,
    )
    codigo_turma_escola = models.BigIntegerField(
        null=True,
        blank=True,
        help_text=_HELP_TURMA,
    )
    codigo_turma_escola_grade_programa = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="ID da grade/programa da turma.",
    )
    descricao_turma_escola = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Descrição da turma escolar.",
    )
    codigo_grade = models.IntegerField(
        help_text=_HELP_GRADE,
    )
    codigo_componente_curricular = models.IntegerField(
        help_text=_HELP_COMP,
    )
    descricao_componente_curricular = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Descrição do componente curricular.",
    )
    codigo_serie_grade = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID de série-grade — ref. domínio pedagógico.",
    )
    ano_escolar = models.CharField(max_length=5, null=True, blank=True)
    ano_atribuicao = models.IntegerField()
    codigo_etapa_ensino = models.IntegerField(null=True, blank=True)
    dt_atribuicao_aula = models.DateField()
    dt_disponibilizacao_aulas = models.DateField(null=True, blank=True)
    dt_inicio_turma = models.DateField(null=True, blank=True)
    dt_fim_turma = models.DateField(null=True, blank=True)
    codigo_motivo_disponibilizacao = models.IntegerField(null=True, blank=True)
    dt_cancelamento = models.DateField(null=True, blank=True)
    codigo_dre = models.CharField(max_length=20, null=True, blank=True)
    nome_dre = models.CharField(max_length=200, null=True, blank=True)
    abreviacao_dre = models.CharField(max_length=100, null=True, blank=True)
    nome_unidade_educacional = models.CharField(
        max_length=200, null=True, blank=True
    )
    codigo_tipo_escola = models.IntegerField(null=True, blank=True)
    codigo_tipo_turma = models.IntegerField(null=True, blank=True)
    modalidade = models.CharField(max_length=50, null=True, blank=True)
    codigo_modalidade = models.IntegerField(null=True, blank=True)
    semestre = models.IntegerField(null=True, blank=True)
    duracao_turno = models.IntegerField(null=True, blank=True)
    tipo_turno = models.IntegerField(null=True, blank=True)

    class Meta:

        app_label = "professores"
        db_table = "atribuicao_aula"
        verbose_name = "atribuição de aula"
        verbose_name_plural = "atribuições de aulas"
        indexes = [
            models.Index(fields=["codigo_unidade_educacao"], name="idx_aa_ue"),
            models.Index(fields=["codigo_turma_escola"], name="idx_aa_turma"),
            models.Index(
                fields=["codigo_componente_curricular"],
                name="idx_aa_componente",
            ),
            models.Index(fields=["ano_atribuicao"], name="idx_aa_ano"),
            models.Index(
                fields=["dt_cancelamento"],
                name="idx_aa_cancelamento",
            ),
        ]


class AtribuicaoExterno(models.Model):
    """Atribuição de aulas ao professor externo/contratado."""

    id = models.BigAutoField(primary_key=True)
    contrato_externo = models.ForeignKey(
        ContratoExterno,
        on_delete=models.CASCADE,
        related_name="atribuicoes",
        db_constraint=False,
    )
    codigo_unidade_educacao = models.CharField(
        max_length=20,
        help_text=_HELP_UE,
    )
    codigo_turma_escola = models.BigIntegerField(
        null=True,
        blank=True,
        help_text=_HELP_TURMA,
    )
    descricao_turma_escola = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Descrição da turma escolar.",
    )
    codigo_grade = models.IntegerField(
        help_text=_HELP_GRADE,
    )
    codigo_componente_curricular = models.IntegerField(
        help_text=_HELP_COMP,
    )
    descricao_componente_curricular = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Descrição do componente curricular.",
    )
    codigo_serie_grade = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID de série-grade — ref. domínio pedagógico.",
    )
    codigo_turma_escola_grade_programa = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="ID da grade/programa da turma.",
    )
    ano_escolar = models.CharField(max_length=5, null=True, blank=True)
    ano_atribuicao = models.IntegerField()
    codigo_etapa_ensino = models.IntegerField(null=True, blank=True)
    dt_atribuicao = models.DateField()
    dt_disponibilizacao = models.DateField(null=True, blank=True)
    dt_inicio_turma = models.DateField(null=True, blank=True)
    dt_fim_turma = models.DateField(null=True, blank=True)
    codigo_motivo_disponibilizacao_externo = models.IntegerField(
        null=True, blank=True
    )
    dt_cancelamento = models.DateField(null=True, blank=True)

    class Meta:

        app_label = "professores"
        db_table = "atribuicao_externo"
        verbose_name = "atribuição de professor externo"
        verbose_name_plural = "atribuições de professores externos"
        indexes = [
            models.Index(fields=["codigo_unidade_educacao"], name="idx_ae_ue"),
            models.Index(fields=["codigo_turma_escola"], name="idx_ae_turma"),
            models.Index(
                fields=["codigo_componente_curricular"],
                name="idx_ae_componente",
            ),
            models.Index(fields=["ano_atribuicao"], name="idx_ae_ano"),
            models.Index(
                fields=["dt_cancelamento"],
                name="idx_ae_cancelamento",
            ),
        ]


class FuncionarioUnidadeEducacional(models.Model):
    """Funcionario consolidado por unidade educacional."""

    id = models.BigAutoField(primary_key=True)
    codigo_rf = models.CharField(max_length=20)
    nome = models.CharField(max_length=200)
    nome_social = models.CharField(max_length=200, null=True, blank=True)
    cpf = models.CharField(
        max_length=14,
        null=True,
        blank=True,
    )
    codigo_ue = models.CharField(max_length=20)
    data_inicio = models.DateTimeField(default=_data_chave_padrao)
    data_fim = models.DateTimeField(null=True, blank=True)
    codigo_cargo = models.IntegerField(null=True, blank=True)
    cargo = models.CharField(max_length=100, null=True, blank=True)
    codigo_tipo_funcao_atividade = models.IntegerField(default=0)
    eh_professor = models.BooleanField(default=False)
    esta_afastado = models.BooleanField(default=False)
    funcao_externo = models.IntegerField(default=0)
    tipo_funcao_externo = models.IntegerField(default=0)

    class Meta:

        app_label = "professores"
        db_table = "funcionario_unidade_educacional"
        verbose_name = "funcionario"
        verbose_name_plural = "funcionarios"
        indexes = [
            models.Index(fields=["codigo_ue"], name="idx_funcionario_ue"),
            models.Index(
                fields=["codigo_cargo"], name="idx_funcionario_cargo"
            ),
            models.Index(fields=["codigo_rf"], name="idx_funcionario_rf"),
            models.Index(
                fields=["codigo_ue", "codigo_cargo"],
                name="idx_funcionario_ue_cargo",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "codigo_rf",
                    "codigo_ue",
                    "codigo_cargo",
                    "codigo_tipo_funcao_atividade",
                    "data_inicio",
                    "data_fim",
                    "funcao_externo",
                    "tipo_funcao_externo",
                ],
                name="uq_funcionario_rf_ue_cargo_funcao_vinculo",
                nulls_distinct=False,
            ),
        ]
