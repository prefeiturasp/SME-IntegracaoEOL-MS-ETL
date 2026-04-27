from django.db import models

from apps.core.models import ModeloBase


class ComponenteCurricular(ModeloBase):
    """Catálogo de componentes curriculares ativos no EOL.

    É a fonte de verdade para código e descrição de cada componente.
    Todas as outras tabelas do domínio referenciam o código daqui.

    Alimenta: GET /componentes-curriculares
    """

    codigo = models.IntegerField(unique=True)
    descricao = models.CharField(max_length=300)

    class Meta:
        db_table = "componente_curricular"
        verbose_name = "componente curricular"
        verbose_name_plural = "componentes curriculares"

    def __str__(self) -> str:
        return f"{self.codigo} - {self.descricao}"


class ComponenteCurricularPorTurma(ModeloBase):
    """Atribuição real de componente a uma turma e professor.

    Registra quais componentes curriculares um professor leciona em
    cada turma. Inclui flags que classificam o componente: se é de
    regência, se é território do saber e se entra no planejamento.

    Componentes com `territorio_saber=True` também aparecem em
    ComponenteCurricularAgrupamento quando fazem parte de um
    agrupamento (professor atribuído a mais de um componente de
    território na mesma turma).

    Alimenta:
    - funcionarios/{login}?codigoTurma=...
    - turmas (codigoTurmas[])
    - turmas/brutos
    - ues/{ueId}/turmas

    Upsert: (codigo, turma_codigo, professor) com nulls_distinct=False.
    """

    codigo = models.IntegerField()
    codigo_componente_territorio_saber = models.IntegerField(null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    codigo_componente_curricular_pai = models.IntegerField(null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    descricao = models.CharField(max_length=300)
    regencia = models.BooleanField()
    planejamento_regencia = models.BooleanField()
    territorio_saber = models.BooleanField()
    turma_codigo = models.CharField(
        max_length=20, null=True, blank=True
    )  # NOSONAR
    exibir_componente_eol = models.BooleanField()
    professor = models.CharField(
        max_length=20, null=True, blank=True
    )  # NOSONAR
    ano_letivo = models.IntegerField()

    class Meta:
        db_table = "componente_curricular_por_turma"
        verbose_name = "componente curricular por turma"
        verbose_name_plural = "componentes curriculares por turma"
        constraints = [
            models.UniqueConstraint(
                fields=["codigo", "turma_codigo", "professor"],
                name="uq_componente_por_turma",
                nulls_distinct=False,
            ),
        ]
        indexes = [
            models.Index(
                fields=["turma_codigo"], name="idx_ccpt_turma_codigo"
            ),
            models.Index(fields=["codigo"], name="idx_ccpt_codigo"),
            models.Index(fields=["ano_letivo"], name="idx_ccpt_ano_letivo"),
            models.Index(
                fields=["professor", "ano_letivo"], name="idx_ccpt_prof_ano"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.codigo} turma={self.turma_codigo}"
            f" professor={self.professor}"
        )


class ComponenteCurricularAgrupamento(ModeloBase):
    """Itens de um agrupamento de território do saber.

    Quando um professor é atribuído a múltiplos componentes de
    território numa mesma turma, esses componentes são agrupados.
    Esta tabela detalha cada componente do agrupamento — uma linha
    por componente.

    Derivada do split do CSV `cod_componentes_curriculares` de
    AgrupamentoAtribuicaoTerritorioSaber, que registra o agrupamento
    como um todo.

    Alimenta o array `codigosTerritoriosAgrupamento` retornado por:
    - funcionarios/{login}?codigoTurma=...
    """

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
                ],
                name="uq_componente_agrupamento",
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


class ComponenteInicioTurma(ModeloBase):
    """Vigência de cada componente curricular numa turma concreta.

    Registra quando cada componente começa a ser ministrado em cada turma
    e qual a periodicidade da turma. Os campos de filtro são desnormalizados
    para evitar JOINs em tempo de consulta:
    - `componente_codigo` → chave natural da tabela
    - `ue_codigo` → de te.cd_escola
    - `ano_letivo` → de te.an_letivo
    - `tipo_periodicidade` → de te.cd_tipo_periodicidade
      (semestre para EJA/CIEJA)

    Alimenta: GET /api/v1/componentes-curriculares/turmas/vigencia
    """

    componente_codigo = models.CharField(max_length=20)
    componente_descricao = models.CharField(max_length=300)
    turma_codigo = models.CharField(max_length=20)
    data_inicio_turma = models.DateTimeField(null=True, blank=True)
    ue_codigo = models.CharField(
        max_length=10, null=True, blank=True
    )  # NOSONAR
    ano_letivo = models.IntegerField(null=True, blank=True)
    tipo_periodicidade = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "componente_inicio_turma"
        verbose_name = "componente início turma"
        verbose_name_plural = "componentes início turma"
        constraints = [
            models.UniqueConstraint(
                fields=["componente_codigo", "turma_codigo"],
                name="uq_componente_inicio_turma",
            ),
        ]
        indexes = [
            models.Index(
                fields=["ue_codigo", "ano_letivo"],
                name="idx_dat_ue_ano_letivo",
            ),
            models.Index(fields=["turma_codigo"], name="idx_dat_turma_codigo"),
        ]

    def __str__(self) -> str:
        return f"{self.componente_codigo} turma={self.turma_codigo}"


class GradeCurricularSerie(ModeloBase):
    """Catálogo de componentes previstos na grade por série e modalidade.

    Representa o que a grade curricular prevê para cada série/modalidade
    num dado ano letivo — independente de haver atribuição de professor
    ou turma. Diferente de ComponenteCurricularPorTurma, que registra
    atribuições reais, esta tabela é um catálogo de oferta curricular.

    `modalidade` via CASE na query: 1=EI | 3=EJA | 4=CIEJA | 5=EF | 6=EM.

    Alimenta:
    - GET ues/{ueId}/modalidades/{mod}/anos/{ano}
    - GET ues/{ueId}/modalidades/{mod}/anos/{ano}/turmas-programa
    Upsert: (codigo_componente_curricular, ano_letivo, modalidade)
            com nulls_distinct=False.
    """

    codigo_componente_curricular = models.IntegerField()
    descricao_componente_curricular = models.CharField(max_length=300)
    codigo_ano_turma = models.CharField(max_length=10, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    descricao_serie_ensino = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    codigo_serie_ensino = models.IntegerField(null=True, blank=True)
    modalidade = models.IntegerField(null=True, blank=True)
    ano_letivo = models.IntegerField()

    class Meta:
        db_table = "grade_curricular_serie"
        verbose_name = "grade curricular série"
        verbose_name_plural = "grades curriculares série"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "codigo_componente_curricular",
                    "ano_letivo",
                    "modalidade",
                ],
                name="uq_grade_curricular_serie",
                nulls_distinct=False,
            ),
        ]
        indexes = [
            models.Index(
                fields=["ano_letivo", "modalidade"],
                name="idx_gcs_ano_letivo_modalidade",
            ),
            models.Index(
                fields=["codigo_ano_turma"], name="idx_gcs_codigo_ano_turma"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.codigo_componente_curricular} "
            f"ano_letivo={self.ano_letivo} "
            f"modalidade={self.modalidade}"
        )


class AgrupamentoAtribuicaoTerritorioSaber(ModeloBase):
    """Agrupamento de componentes de território atribuídos a um professor.

    Quando um professor é atribuído a múltiplos componentes de território
    do saber na mesma turma, o conjunto forma um agrupamento identificado
    por `cod_agrupamento` (hash MD5 determinístico da chave natural).

    `cod_componentes_curriculares` armazena os códigos como CSV. O ETL
    faz o split e popula ComponenteCurricularAgrupamento com uma linha
    por componente.

    Alimenta:
    - GET  territorio-saber/agrupamentos-correlacionados
    - POST territorio-saber/agrupamentos-correlacionados
    - POST territorio-saber/agrupamentos
    """

    cod_agrupamento = models.BigIntegerField(unique=True)
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
    cod_componentes_curriculares = models.CharField(max_length=500, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    ano_letivo = models.IntegerField()
    cod_motivo_disponibilizacao = models.IntegerField(null=True, blank=True)
    desc_territorio_saber = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    desc_experiencia_pedagogica = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    encerramento_atribuicao_agrupamento_atualizado = models.BooleanField(null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip

    class Meta:
        db_table = "agrupamento_atribuicao_territorio_saber"
        verbose_name = "agrupamento atribuição território saber"
        verbose_name_plural = "agrupamentos atribuição território saber"
        indexes = [
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


class RegenciaComponenteCurricular(models.Model):
    """Alimenta: GET anos/{anoTurma}/regencia."""

    id_componente_curricular = models.IntegerField()
    turno = models.IntegerField(null=True, blank=True)
    ano = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "regenciacomponentecurricular"


class ComponenteCurricularPAP(models.Model):
    """Alimenta: turmas/{codigoTurma}/funcionarios/{login}/validar/pap."""

    id_componente_curricular = models.IntegerField(unique=True)

    class Meta:
        db_table = "componentecurricularpap"
