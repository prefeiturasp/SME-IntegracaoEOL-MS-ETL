from django.db import models

from apps.core.models import ModeloBase


class ComponenteCurricular(ModeloBase):
    """Catálogo de componentes curriculares."""

    codigo = models.IntegerField(unique=True)
    descricao = models.CharField(max_length=300)
    regencia = models.BooleanField(default=False)

    class Meta:
        db_table = "componente_curricular"
        verbose_name = "componente curricular"
        verbose_name_plural = "componentes curriculares"

    def __str__(self) -> str:
        return f"{self.codigo} - {self.descricao}"


class ComponenteTurma(ModeloBase):
    """Vínculo curricular entre turma e componente."""

    turma_codigo = models.CharField(max_length=20)
    componente_codigo = models.IntegerField()
    codigo_componente_territorio_saber = models.IntegerField(
        null=True,
        blank=True,
    )
    desc_territorio_saber = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )
    desc_experiencia_pedagogica = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )
    tipo_escola = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = "componente_turma"
        verbose_name = "componente turma"
        verbose_name_plural = "componentes turma"
        constraints = [
            models.UniqueConstraint(
                fields=["turma_codigo", "componente_codigo"],
                name="uq_componente_turma",
            ),
        ]
        indexes = [
            models.Index(fields=["turma_codigo"], name="idx_ct_turma_codigo"),
            models.Index(
                fields=["componente_codigo"], name="idx_ct_componente_codigo"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.componente_codigo} turma={self.turma_codigo}"


class AtribuicaoComponente(ModeloBase):
    """Atribuição de professor a turma e componente curricular."""

    turma_codigo = models.CharField(max_length=20)
    componente_codigo = models.IntegerField()
    professor = models.CharField(
        max_length=20, null=True, blank=True
    )  # NOSONAR
    atribuicao_externa = models.BooleanField(default=False)
    ano_letivo = models.IntegerField()
    id_atribuicao_origem = models.BigIntegerField(null=True, blank=True)
    dt_atribuicao = models.DateTimeField(null=True, blank=True)
    dt_cancelamento = models.DateTimeField(null=True, blank=True)
    dt_disponibilizacao = models.DateTimeField(null=True, blank=True)
    cd_motivo_disponibilizacao = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "atribuicao_componente"
        verbose_name = "atribuição componente"
        verbose_name_plural = "atribuições componente"
        constraints = [
            models.UniqueConstraint(
                fields=["turma_codigo", "componente_codigo", "professor"],
                name="uq_atribuicao_componente",
                nulls_distinct=False,
            ),
        ]
        indexes = [
            models.Index(fields=["turma_codigo"], name="idx_ac_turma_codigo"),
            models.Index(
                fields=["componente_codigo"], name="idx_ac_componente_codigo"
            ),
            models.Index(
                fields=["professor", "ano_letivo"], name="idx_ac_prof_ano"
            ),
            models.Index(
                fields=["professor", "ano_letivo"],
                name="idx_ac_prof_ano_vigente",
                condition=models.Q(
                    dt_cancelamento__isnull=True,
                    dt_disponibilizacao__isnull=True,
                ),
            ),
            models.Index(
                fields=["professor", "ano_letivo", "componente_codigo"],
                name="idx_ac_prof_ano_comp_vig",
                condition=models.Q(dt_cancelamento__isnull=True),
            ),
            models.Index(
                fields=[
                    "turma_codigo",
                    "professor",
                    "componente_codigo",
                    "ano_letivo",
                ],
                name="idx_ac_turma_prof_comp_ano",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.componente_codigo} turma={self.turma_codigo}"
            f" professor={self.professor}"
        )


class AtribuicaoTerritorioSaber(ModeloBase):
    """Atribuição individual de componente de Território do Saber."""

    turma_codigo = models.CharField(max_length=20)
    componente_codigo = models.IntegerField()
    professor = models.CharField(
        max_length=20, null=True, blank=True
    )  # NOSONAR
    codigo_territorio_saber = models.IntegerField()
    codigo_experiencia_pedagogica = models.IntegerField(null=True, blank=True)
    desc_territorio_saber = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )
    desc_experiencia_pedagogica = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )
    atribuicao_externa = models.BooleanField(default=False)
    ano_letivo = models.IntegerField()
    dt_atribuicao = models.DateTimeField(null=True, blank=True)
    dt_disponibilizacao = models.DateTimeField(null=True, blank=True)
    cd_motivo_disponibilizacao = models.IntegerField(null=True, blank=True)
    dt_fim_turma = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "atribuicao_territorio_saber"
        verbose_name = "atribuição território saber"
        verbose_name_plural = "atribuições território saber"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "turma_codigo",
                    "componente_codigo",
                    "professor",
                    "codigo_territorio_saber",
                    "codigo_experiencia_pedagogica",
                    "dt_atribuicao",
                    "dt_disponibilizacao",
                ],
                name="uq_atribuicao_territorio_saber",
                nulls_distinct=False,
            ),
        ]
        indexes = [
            models.Index(fields=["turma_codigo"], name="idx_ats_turma"),
            models.Index(fields=["professor"], name="idx_ats_professor"),
            models.Index(fields=["ano_letivo"], name="idx_ats_ano_letivo"),
            models.Index(
                fields=["turma_codigo", "componente_codigo"],
                name="idx_ats_turma_comp",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.componente_codigo} turma={self.turma_codigo}"
            f" professor={self.professor}"
        )


class ComponenteCurricularAgrupamento(ModeloBase):
    """Item de componente em agrupamento de território do saber."""

    componente_codigo = models.IntegerField()
    turma_codigo = models.CharField(max_length=20)
    codigo_agrupamento = models.BigIntegerField()
    rf_professor = models.CharField(
        max_length=20, null=True, blank=True
    )  # NOSONAR
    ano_letivo = models.IntegerField()

    class Meta:
        db_table = "componente_curricular_agrupamento"
        verbose_name = "componente curricular agrupamento"
        verbose_name_plural = "componentes curriculares agrupamento"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "componente_codigo",
                    "turma_codigo",
                    "codigo_agrupamento",
                    "rf_professor",
                ],
                name="uq_componente_agrupamento",
                nulls_distinct=False,
            ),
        ]
        indexes = [
            models.Index(fields=["turma_codigo"], name="idx_cca_turma_codigo"),
            models.Index(
                fields=["componente_codigo"], name="idx_cca_componente_codigo"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"componente={self.componente_codigo} "
            f"turma={self.turma_codigo} "
            f"agrupamento={self.codigo_agrupamento}"
        )


class GradeComponenteCurricular(ModeloBase):
    """Catálogo de componentes previstos na grade curricular."""

    codigo_componente_curricular = models.IntegerField()
    descricao_componente_curricular = models.CharField(max_length=300)
    codigo_ano_turma = models.CharField(
        max_length=10,
        null=True,
        blank=True,
    )
    descricao_serie_ensino = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )
    codigo_serie_ensino = models.IntegerField(null=True, blank=True)
    modalidade = models.IntegerField(null=True, blank=True)
    ano_letivo = models.IntegerField()

    class Meta:
        db_table = "grade_componente_curricular"
        verbose_name = "grade componente curricular"
        verbose_name_plural = "grades componente curricular"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "codigo_componente_curricular",
                    "ano_letivo",
                    "modalidade",
                    "codigo_serie_ensino",
                ],
                name="uq_grade_componente_curricular",
                nulls_distinct=False,
            ),
        ]
        indexes = [
            models.Index(
                fields=["ano_letivo", "modalidade"],
                name="idx_gcc_ano_letivo_modalidade",
            ),
            models.Index(
                fields=["codigo_ano_turma"], name="idx_gcc_codigo_ano_turma"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.codigo_componente_curricular} "
            f"ano_letivo={self.ano_letivo} "
            f"modalidade={self.modalidade}"
        )


class AgrupamentoAtribuicaoTerritorioSaber(ModeloBase):
    """Agrupamento de atribuições de território do saber."""

    cod_agrupamento = models.BigIntegerField()
    cod_territorio_saber = models.IntegerField()
    cod_experiencia_pedagogica = models.IntegerField(null=True, blank=True)
    dt_inicio_atribuicao = models.DateTimeField()
    ano_atribuicao = models.IntegerField()
    dt_fim_atribuicao = models.DateTimeField(null=True, blank=True)
    dt_fim_turma = models.DateTimeField(null=True, blank=True)
    rf_professor = models.CharField(
        max_length=20, null=True, blank=True
    )  # NOSONAR
    cod_turma = models.CharField(
        max_length=20, null=True, blank=True
    )  # NOSONAR
    cod_componentes_curriculares = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    ano_letivo = models.IntegerField()
    cod_motivo_disponibilizacao = models.IntegerField(null=True, blank=True)
    desc_territorio_saber = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )
    desc_experiencia_pedagogica = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )
    encerramento_atribuicao_agrupamento_atualizado = models.BooleanField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "agrupamento_atribuicao_territorio_saber"
        verbose_name = "agrupamento atribuição território saber"
        verbose_name_plural = "agrupamentos atribuição território saber"
        indexes = [
            models.Index(
                fields=["cod_agrupamento"], name="idx_aats_cod_agrupamento"
            ),
            models.Index(fields=["cod_turma"], name="idx_aats_cod_turma"),
            models.Index(
                fields=["rf_professor"], name="idx_aats_rf_professor"
            ),
            models.Index(fields=["ano_letivo"], name="idx_aats_ano_letivo"),
        ]

    def __str__(self) -> str:
        return (
            f"agrupamento={self.cod_agrupamento} "
            f"territorio={self.cod_territorio_saber} "
            f"ano_letivo={self.ano_letivo}"
        )


class Turma(ModeloBase):
    """Dados cadastrais de turma do EOL."""

    codigo = models.BigIntegerField(unique=True)
    ano_letivo = models.IntegerField()
    ano = models.CharField(max_length=5, null=True, blank=True)
    tipo_turma = models.IntegerField()
    nome_turma = models.CharField(max_length=200)
    duracao_turno = models.IntegerField(null=True, blank=True)
    tipo_turno = models.IntegerField(null=True, blank=True)
    data_inicio_turma = models.DateTimeField(null=True, blank=True)
    data_fim = models.DateTimeField(null=True, blank=True)
    extinta = models.BooleanField(default=False)
    situacao = models.CharField(max_length=1, null=True, blank=True)
    ue_codigo = models.CharField(max_length=20)
    modalidade = models.CharField(max_length=50, null=True, blank=True)
    codigo_modalidade = models.IntegerField(null=True, blank=True)
    codigo_tipo_programa = models.IntegerField(null=True, blank=True)
    semestre = models.IntegerField(null=True, blank=True, default=0)
    codigo_tipo_periodicidade = models.IntegerField(null=True, blank=True)
    ensino_especial = models.BooleanField(default=False)
    codigo_modalidade_etapa = models.IntegerField(null=True, blank=True)
    serie_ensino = models.CharField(max_length=200, null=True, blank=True)
    codigo_serie_ensino = models.IntegerField(null=True, blank=True)
    codigo_etapa_ensino = models.IntegerField(null=True, blank=True)
    codigo_ciclo_ensino = models.IntegerField(null=True, blank=True)
    tipo_escola = models.IntegerField(default=0)
    codigo_grade_programa = models.IntegerField(default=0)
    descricao_grade_programa = models.CharField(
        max_length=200, default="NAO INFORMADA"
    )
    tipo_grade_programa = models.IntegerField(default=0)
    data_atualizacao = models.DateTimeField(null=True, blank=True)
    data_status_turma_escola = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "turma"
        verbose_name = "turma"
        verbose_name_plural = "turmas"
        indexes = [
            models.Index(
                fields=["ue_codigo", "ano_letivo"], name="idx_turma_ue_ano"
            ),
            models.Index(
                fields=[
                    "ue_codigo",
                    "ano_letivo",
                    "codigo_modalidade_etapa",
                    "codigo",
                ],
                name="idx_turma_ue_ano_mod_codigo",
            ),
            models.Index(
                fields=[
                    "ue_codigo",
                    "ano_letivo",
                    "codigo_tipo_programa",
                ],
                name="idx_turma_ue_ano_programa",
            ),
            models.Index(fields=["tipo_turma"], name="idx_turma_tipo"),
            models.Index(fields=["ano_letivo"], name="idx_turma_ano_letivo"),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nome_turma}"


class TurmaAtribuidaDreUe(ModeloBase):
    """Turma consolidada por DRE e UE."""

    codigo_escola = models.CharField(max_length=6)
    codigo_turma = models.BigIntegerField()
    ano_letivo = models.IntegerField()
    modalidade = models.CharField(max_length=15, null=True, blank=True)
    semestre = models.IntegerField(null=True, blank=True)
    codigo_modalidade = models.IntegerField(null=True, blank=True)
    codigo_dre = models.CharField(max_length=6)
    dre = models.CharField(max_length=60, null=True, blank=True)
    dre_abreviacao = models.CharField(max_length=60, null=True, blank=True)
    ue = models.CharField(max_length=60, null=True, blank=True)
    ue_abreviacao = models.CharField(max_length=60, null=True, blank=True)
    nome_turma = models.CharField(max_length=15, null=True, blank=True)
    ano = models.CharField(max_length=18, null=True, blank=True)
    tipo_ue = models.CharField(max_length=25, null=True, blank=True)
    codigo_tipo_ue = models.IntegerField(null=True, blank=True)
    codigo_tipo_escola = models.IntegerField(null=True, blank=True)
    tipo_escola = models.CharField(max_length=12, null=True, blank=True)
    duracao_turno = models.IntegerField(null=True, blank=True)
    tipo_turno = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "turma_atribuida_dre_ue"
        verbose_name = "turma atribuída DRE UE"
        verbose_name_plural = "turmas atribuídas DRE UE"
        indexes = [
            models.Index(
                fields=["codigo_escola"], name="idx_tadu_codigo_escola"
            ),
            models.Index(fields=["codigo_dre"], name="idx_tadu_codigo_dre"),
            models.Index(fields=["ano_letivo"], name="idx_tadu_ano_letivo"),
            models.Index(fields=["codigo_turma"], name="idx_tadu_turma"),
        ]

    def __str__(self) -> str:
        return f"{self.codigo_turma} - {self.codigo_escola}"


class TurmaItinerarioEnsinoMedio(ModeloBase):
    """Itinerário estático do Ensino Médio."""

    nome = models.CharField(max_length=100)
    serie = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self) -> str:
        return str(self.nome)

    class Meta:
        db_table = "turma_itinerario_ensino_medio"


class ComponenteCurricularPlanejamentoRegencia(ModeloBase):
    """Componente curricular aplicável ao planejamento de regência."""

    id_componente_curricular = models.IntegerField()
    turno = models.IntegerField(null=True, blank=True)
    ano = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "componente_curricular_planejamento_regencia"


class ComponenteCurricularHierarquia(ModeloBase):
    """Mapeia componentes filhos para seus componentes curriculares pais."""

    id_componente_curricular_pai = models.IntegerField(
        db_column="idcomponentecurricularpai"
    )
    id_componente_curricular = models.IntegerField(
        db_column="idcomponentecurricular"
    )
    vigencia = models.DateTimeField()

    class Meta:
        db_table = "componente_curricular_hierarquia"
        indexes = [
            models.Index(
                fields=["id_componente_curricular", "-vigencia"],
                name="idx_cch_comp_vigencia",
            ),
        ]


class ComponenteCurricularPAP(ModeloBase):
    """Componente curricular reconhecido como PAP."""

    id_componente_curricular = models.IntegerField(unique=True)

    class Meta:
        db_table = "componente_curricular_pap"
