from django.db import models

from apps.core.models import ModeloBase


class ComponenteCurricular(ModeloBase):
    """Catálogo de componentes curriculares não cancelados.

    Fonte: `componente_curricular WHERE dt_cancelamento IS NULL`.
    Upsert por `codigo`.
    """

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
    """Estrutura turma × componente, sem professor.

    Fonte: `SQL_COMPONENTE_TURMA` — dois branches via UNION ALL:
    - turmas com série:
      `serie_turma_escola → serie_turma_grade → grade`
    - turmas de programa: `turma_escola_grade_programa`

    Ambos filtram `st_turma_escola IN ('O','A','C','E')`.

    Upsert: (turma_codigo, componente_codigo).
    """

    turma_codigo = models.CharField(max_length=20)
    componente_codigo = models.IntegerField()
    codigo_componente_territorio_saber = models.IntegerField(
        null=True,
        blank=True,
    )

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
    """Atribuições de professor a turma/componente, SME e externos.

    Fonte:
        `SQL_ATRIBUICAO_COMPONENTE`, composta por branches via `UNION`:
        SME ativo por série, SME ativo por programa, externo ativo, externo
        ativo por programa, SME histórico com disponibilização e externo
        histórico com disponibilização.

    Filtros:
        Todos os branches consideram turmas com situação `O`, `A`, `C` ou
        `E`, excluem motivo de disponibilização por erro de cadastro (`26`) e
        limitam externos aos tipos de escola `11`, `12`, `32` e `33`.

    Observações:
        `professor = NULL` não ocorre; ausência de linha indica componente
        sem professor atribuído.

    Upsert:
        Usa `turma_codigo`, `componente_codigo` e `professor`.
    """

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


class ComponenteCurricularAgrupamento(ModeloBase):
    """Componentes individuais de um agrupamento de território do saber.

    Derivada de `AgrupamentoAtribuicaoTerritorioSaber`: o ETL faz split
    do CSV `cod_componentes_curriculares` e gera uma linha por componente
    por agrupamento.

    Upsert: (componente_codigo, turma_codigo, codigo_agrupamento).
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


class GradeComponenteCurricular(ModeloBase):
    """Catálogo de componentes previstos na grade.

    Fonte: `SQL_GRADE_COMPONENTE_CURRICULAR`.
    Caminho: `turma_escola → escola → grade`.
    Inclui JOIN com `unidade_administrativa` (DRE).
    Exclui extintas: `st_turma_escola IN ('O','A','C')` (sem 'E').
    Exige série válida: `sg_resumida_serie IS NOT NULL`.
    Inclui turmas de programa via `turma_escola_grade_programa` (LEFT JOIN).

    Representa o CATÁLOGO de oferta curricular. Existe mesmo antes de
    turmas serem abertas para o ano letivo, diferente de `ComponenteTurma`.

    `modalidade` via CASE: 1=EI | 3=EJA | 4=CIEJA | 5=EF | 6=EM.

    Upsert: (codigo_componente_curricular, ano_letivo,
    modalidade, codigo_ano_turma).
    """

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
                    "codigo_ano_turma",
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
    """Agrupamento de atribuições de território do saber.

    Fonte: `SQL_ATRIBUICOES_TERRITORIO_SABER` — dois branches via UNION ALL:
    - SME: `atribuicao_aula + v_cargo_base_cotic + v_servidor_cotic`
    - Externo: `atribuicao_externo + contrato_externo + pessoa`.

    Ambos resolvem território via `turma_grade_territorio_experiencia`.
    Filtram `st_turma_escola IN ('O','A','C','E')`.

    `cod_agrupamento` é um hash MD5 determinístico da chave natural.
    `cod_componentes_curriculares` armazena os códigos como CSV. O ETL
    faz o split e popula `ComponenteCurricularAgrupamento`.

    Upsert: cod_agrupamento (unique).
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
    """Dados cadastrais de turmas do EOL.

    Fonte: `SQL_TURMAS` — `turma_escola`.
    Filtra `st_turma_escola IN ('O','A','E','C')`.

    Campos calculados na query:
    - `Ano`: primeiro char de `dc_turma_escola` se numérico, senão '0'
    - `Extinta`: `st_turma_escola = 'E'`
    - `Modalidade` e `CodigoModalidade`: derivados da etapa e tipo escola.
    - `Semestre`: EJA conforme mês de `dt_inicio_turma`; demais → 0
    - `EnsinoEspecial`: `cd_etapa_ensino = 13 AND cd_modalidade_ensino = 2`

    Upsert: codigo (unique).
    """

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
    ensino_especial = models.BooleanField(default=False)
    codigo_modalidade_etapa = models.IntegerField(null=True, blank=True)
    serie_ensino = models.CharField(max_length=200, null=True, blank=True)
    codigo_serie_ensino = models.IntegerField(null=True, blank=True)
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


class TurmaItinerarioEnsinoMedio(models.Model):
    """Fixture estática de itinerários do Ensino Médio.

    Não requer query ao SQL Server — populada via fixture Django.
    Alimenta: GET itinerario/ensino-medio
    """

    nome = models.CharField(max_length=100)
    serie = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self) -> str:
        return str(self.nome)

    class Meta:
        db_table = "turma_itinerario_ensino_medio"


class ComponenteCurricularPlanejamentoRegencia(models.Model):
    """Define componentes curriculares do planejamento de regência.

    Pode restringir a aplicação por turno e ano escolar da turma.

    Não representa os componentes que são regência; esses são identificados
    separadamente pelo cadastro de componente curricular.
    """

    id_componente_curricular = models.IntegerField()
    turno = models.IntegerField(null=True, blank=True)
    ano = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "componente_curricular_planejamento_regencia"


class ComponenteCurricularHierarquia(models.Model):
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


class ComponenteCurricularPAP(models.Model):
    """Alimenta: turmas/{codigoTurma}/funcionarios/{login}/validar/pap."""

    id_componente_curricular = models.IntegerField(unique=True)

    class Meta:
        db_table = "componente_curricular_pap"
