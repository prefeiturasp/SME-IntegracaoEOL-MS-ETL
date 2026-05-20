"""Modelos do app programas — banco destino PROGRAMAS_DB."""

from django.db import models

from apps.programas.enums import CategoriaPrograma

_HT_ATUALIZADO_EM = "Última atualização pelo ETL — usado no incremental."
_HT_FK_TURMA = "FK lógica → turma_programa.codigo_turma."
_HT_FK_COMPONENTE = (
    "FK lógica → componente_curricular_programa"
    ".codigo_componente_curricular."
)
_HT_NOME_COMPONENTE = (
    "EOL dc_componente_curricular — desnormalizado para evitar JOIN."
)
_HT_PAP_DTO = "Desnormalizado da turma — exigido por AlunoTurmaPapDto."


class TipoPrograma(models.Model):
    """Subtipos de programa do EOL agrupados por categoria PAP/PAEE."""

    codigo_tipo_programa = models.IntegerField(
        primary_key=True,
        help_text="Mesmo ID do EOL (cd_tipo_programa).",
    )
    nome = models.CharField(max_length=100)
    categoria = models.CharField(
        max_length=10,
        choices=CategoriaPrograma.choices,
        help_text="'PAP' ou 'PAEE'.",
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        app_label = "programas"
        db_table = "tipo_programa"
        verbose_name = "tipo de programa"
        verbose_name_plural = "tipos de programa"

    def __str__(self) -> str:
        return f"{self.nome} ({self.codigo_tipo_programa})"


class ComponenteCurricularPrograma(models.Model):
    """Componentes curriculares que caracterizam uma categoria de programa."""

    codigo_componente_curricular = models.BigIntegerField(
        unique=True,
        help_text="EOL cd_componente_curricular.",
    )
    nome_componente_curricular = models.CharField(
        max_length=200,
        help_text="EOL dc_componente_curricular.",
    )
    categoria = models.CharField(
        max_length=10,
        choices=CategoriaPrograma.choices,
        help_text="'PAP' ou 'PAEE'.",
    )
    vigente = models.BooleanField(
        help_text="True = componente ativo; False = legado (substituído por versão mais nova).",
    )

    class Meta:
        app_label = "programas"
        db_table = "componente_curricular_programa"
        verbose_name = "componente curricular de programa"
        verbose_name_plural = "componentes curriculares de programa"

    def __str__(self) -> str:
        return (
            f"{self.nome_componente_curricular} ({self.codigo_componente_curricular})"
            f" — {self.categoria}"
        )


class TurmaPrograma(models.Model):
    """Turma de programa (PAP/PAEE) extraída do EOL."""

    codigo_turma = models.BigIntegerField(
        unique=True,
        help_text="EOL cd_turma_escola.",
    )
    nome_turma = models.CharField(
        max_length=200,
        help_text="EOL dc_turma_escola — equivale a TurmaNome / NomeFiltro do Elastic.",
    )
    codigo_ue = models.CharField(
        max_length=20,
        help_text="EOL escola.cd_escola.",
    )
    codigo_dre = models.CharField(
        max_length=20,
        help_text="EOL unidade_administrativa.cd_unidade_administrativa.",
    )
    ano_letivo = models.SmallIntegerField(
        help_text="EOL turma_escola.an_letivo."
    )
    tipo_turno = models.SmallIntegerField(
        null=True,
        blank=True,
        help_text="EOL cd_tipo_turno.",
    )
    descricao_turno = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="EOL tipo_turno.dc_exibicao_portal — desnormalizado para evitar JOIN.",
    )
    descricao_grade = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text=(
            "EOL grade.dc_grade da grade vinculada à turma "
            "(turma_escola_grade_programa → escola_grade → grade). "
            "Usado para compor o turmaNome legado no formato "
            "'<dc_turma_escola> - <dc_grade>' "
            "(ex: 'PAP COLABORATIVO 3 / 4 E 5 ANO'). "
            "Quando a turma tem mais de uma grade ativa, é trazida "
            "uma (TOP 1 / OUTER APPLY) — fiel ao comportamento legado."
        ),
    )
    situacao = models.CharField(
        max_length=1,
        help_text="O=Organizada, A=Não Organizada, C=Concluída, E=Extinta.",
    )
    codigo_tipo_programa = models.IntegerField(
        null=True,
        blank=True,
        help_text=(
            "EOL cd_tipo_programa — FK lógica para tipo_programa. "
            "Pode ser NULL: a categoria PAP/PAEE é determinada pelo componente "
            "curricular da turma, não pelo tipo de programa."
        ),
    )
    categoria = models.CharField(
        max_length=10,
        choices=CategoriaPrograma.choices,
        help_text="'PAP' ou 'PAEE' — desnormalizado de TipoPrograma para filtros diretos.",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_HT_ATUALIZADO_EM,
    )

    class Meta:
        app_label = "programas"
        db_table = "turma_programa"
        verbose_name = "turma de programa"
        verbose_name_plural = "turmas de programa"
        indexes = [
            models.Index(fields=["ano_letivo"], name="idx_turma_prog_ano"),
            models.Index(fields=["codigo_ue"], name="idx_turma_prog_ue"),
            models.Index(
                fields=["categoria"], name="idx_turma_prog_categoria"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nome_turma} ({self.codigo_turma}) — {self.ano_letivo}"


class TurmaProgramaComponenteCurricular(models.Model):
    """Componentes curriculares oferecidos por uma turma de programa."""

    codigo_turma = models.BigIntegerField(
        help_text=_HT_FK_TURMA,
    )
    codigo_componente_curricular = models.BigIntegerField(
        help_text=_HT_FK_COMPONENTE,
    )
    nome_componente_curricular = models.CharField(
        max_length=200,
        help_text=_HT_NOME_COMPONENTE,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "programas"
        db_table = "turma_programa_componente_curricular"
        verbose_name = "componente curricular da turma"
        verbose_name_plural = "componentes curriculares das turmas"
        constraints = [
            models.UniqueConstraint(
                fields=["codigo_turma", "codigo_componente_curricular"],
                name="uq_turma_prog_componente",
            )
        ]
        indexes = [
            models.Index(
                fields=["codigo_turma"], name="idx_turma_prog_comp_turma"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Turma {self.codigo_turma}"
            f" — {self.nome_componente_curricular} ({self.codigo_componente_curricular})"
        )


_HT_CODIGO_ALUNO = (
    "EOL cd_aluno — FK lógica para aluno (PEDAGOGICO_DB — banco diferente)."
)
_HT_SITUACAO_MATRICULA = "EOL st_matricula."
_HT_DESC_SITUACAO = (
    "Ex: 'Ativo', 'Concluído' — desnormalizado para evitar mapeamento em código."
)
_HT_DATA_SITUACAO = "EOL dt_situacao_aluno."
_HT_ANO_LETIVO_MATRICULA = (
    "Desnormalizado da turma — necessário para filtros diretos por ano."
)
_HT_CATEGORIA_MATRICULA = (
    "'PAP' ou 'PAEE' — desnormalizado da turma para filtros diretos."
)


class MatriculaTurmaProgramaBase(models.Model):
    """Campos comuns às matrículas em turmas de programa."""

    codigo_aluno = models.BigIntegerField(help_text=_HT_CODIGO_ALUNO)
    codigo_turma = models.BigIntegerField(help_text=_HT_FK_TURMA)
    codigo_componente_curricular = models.BigIntegerField(
        help_text=_HT_FK_COMPONENTE,
    )
    nome_componente_curricular = models.CharField(
        max_length=200,
        help_text=_HT_NOME_COMPONENTE,
    )
    codigo_situacao_matricula = models.SmallIntegerField(
        help_text=_HT_SITUACAO_MATRICULA,
    )
    descricao_situacao_matricula = models.CharField(
        max_length=50,
        help_text=_HT_DESC_SITUACAO,
    )
    data_situacao = models.DateField(
        null=True,
        blank=True,
        help_text=_HT_DATA_SITUACAO,
    )
    ano_letivo = models.SmallIntegerField(help_text=_HT_ANO_LETIVO_MATRICULA)
    codigo_ue = models.CharField(max_length=20, help_text=_HT_PAP_DTO)
    codigo_dre = models.CharField(max_length=20, help_text=_HT_PAP_DTO)
    categoria = models.CharField(
        max_length=10,
        choices=CategoriaPrograma.choices,
        help_text=_HT_CATEGORIA_MATRICULA,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_HT_ATUALIZADO_EM,
    )

    class Meta:
        abstract = True


class MatriculaTurmaPrograma(MatriculaTurmaProgramaBase):
    """Matrículas de alunos em turmas de programa, por componente curricular."""

    data_matricula = models.DateField(help_text="EOL dt_status_matricula.")

    class Meta:
        app_label = "programas"
        db_table = "matricula_turma_programa"
        verbose_name = "matrícula em turma de programa"
        verbose_name_plural = "matrículas em turmas de programa"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ],
                name="uq_matricula_turma_aluno_componente",
            )
        ]
        indexes = [
            models.Index(fields=["codigo_aluno"], name="idx_matricula_aluno"),
            models.Index(fields=["ano_letivo"], name="idx_matricula_ano"),
            models.Index(fields=["codigo_ue"], name="idx_matricula_ue"),
            models.Index(
                fields=["categoria"], name="idx_matricula_categoria"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Aluno {self.codigo_aluno}"
            f" — turma {self.codigo_turma}"
            f" / CC {self.codigo_componente_curricular}"
        )


class MatriculaTurmaProgramaHistorico(MatriculaTurmaProgramaBase):
    """Matrículas históricas em turmas de programa, por componente curricular."""

    data_matricula = models.DateField(
        null=True,
        blank=True,
        help_text="EOL dt_status_matricula — nullable no histórico.",
    )

    class Meta:
        app_label = "programas"
        db_table = "matricula_turma_programa_historico"
        verbose_name = "matrícula histórica em turma de programa"
        verbose_name_plural = "matrículas históricas em turmas de programa"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ],
                name="uq_hist_matricula_turma_aluno_componente",
            )
        ]
        indexes = [
            models.Index(
                fields=["codigo_aluno"], name="idx_hist_matricula_aluno"
            ),
            models.Index(fields=["ano_letivo"], name="idx_hist_matricula_ano"),
            models.Index(fields=["codigo_ue"], name="idx_hist_matricula_ue"),
            models.Index(
                fields=["categoria"], name="idx_hist_matricula_categoria"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Aluno {self.codigo_aluno}"
            f" — turma {self.codigo_turma}"
            f" / CC {self.codigo_componente_curricular}"
            f" (histórico)"
        )


class AlunoPapAnoLetivo(models.Model):
    """Alunos PAP por ano letivo, pré-agregados (carga live)."""

    codigo_aluno = models.BigIntegerField(
        help_text="EOL cd_aluno — FK lógica para aluno (PEDAGOGICO_DB).",
    )
    codigo_turma = models.BigIntegerField(
        help_text="FK lógica → turma_programa.codigo_turma.",
    )
    codigo_componente_curricular = models.BigIntegerField(
        help_text=(
            "FK lógica → componente_curricular_programa"
            ".codigo_componente_curricular."
        ),
    )
    ano_letivo = models.SmallIntegerField(
        help_text="EOL turma_escola.an_letivo — chave do filtro do endpoint.",
    )
    codigo_ue = models.CharField(
        max_length=20,
        help_text="EOL escola.cd_escola — desnormalizado.",
    )
    codigo_dre = models.CharField(
        max_length=20,
        help_text=(
            "EOL unidade_administrativa.cd_unidade_administrativa "
            "— desnormalizado."
        ),
    )

    class Meta:
        app_label = "programas"
        db_table = "aluno_pap_ano_letivo"
        verbose_name = "aluno PAP por ano letivo"
        verbose_name_plural = "alunos PAP por ano letivo"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "ano_letivo",
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ],
                name="uq_aluno_pap_ano_turma_aluno_cc",
            )
        ]
        indexes = [
            models.Index(fields=["ano_letivo"], name="idx_aluno_pap_ano"),
        ]

    def __str__(self) -> str:
        return (
            f"Aluno {self.codigo_aluno}"
            f" — turma {self.codigo_turma}"
            f" / CC {self.codigo_componente_curricular}"
            f" ({self.ano_letivo})"
        )


class AlunoPapAnoLetivoHistorico(models.Model):
    """Alunos PAP por ano letivo, pré-agregados (carga histórica)."""

    codigo_aluno = models.BigIntegerField(
        help_text="EOL cd_aluno — FK lógica para aluno (PEDAGOGICO_DB).",
    )
    codigo_turma = models.BigIntegerField(
        help_text="FK lógica → turma_programa.codigo_turma.",
    )
    codigo_componente_curricular = models.BigIntegerField(
        help_text=(
            "FK lógica → componente_curricular_programa"
            ".codigo_componente_curricular."
        ),
    )
    ano_letivo = models.SmallIntegerField(
        help_text="EOL turma_escola.an_letivo — chave do filtro do endpoint.",
    )
    codigo_ue = models.CharField(
        max_length=20,
        help_text="EOL escola.cd_escola — desnormalizado.",
    )
    codigo_dre = models.CharField(
        max_length=20,
        help_text=(
            "EOL unidade_administrativa.cd_unidade_administrativa "
            "— desnormalizado."
        ),
    )

    class Meta:
        app_label = "programas"
        db_table = "aluno_pap_ano_letivo_historico"
        verbose_name = "aluno PAP por ano letivo (histórico)"
        verbose_name_plural = "alunos PAP por ano letivo (histórico)"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "ano_letivo",
                    "codigo_turma",
                    "codigo_aluno",
                    "codigo_componente_curricular",
                ],
                name="uq_aluno_pap_hist_ano_turma_aluno_cc",
            )
        ]
        indexes = [
            models.Index(fields=["ano_letivo"], name="idx_aluno_pap_hist_ano"),
        ]

    def __str__(self) -> str:
        return (
            f"Aluno {self.codigo_aluno}"
            f" — turma {self.codigo_turma}"
            f" / CC {self.codigo_componente_curricular}"
            f" ({self.ano_letivo}, histórico)"
        )
