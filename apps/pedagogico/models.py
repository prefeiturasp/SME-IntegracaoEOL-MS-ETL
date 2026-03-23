"""Modelos do app pedagogico — banco destino PEDAGOGICO_DB.

Domínio autossuficiente (v2.0): todas as tabelas de referência necessárias
para responder as queries do PedagogicoController são embarcadas aqui pelo ETL.
Nenhuma consulta a INSTITUCIONAL_DB ou DOMINIOS_AUXILIAR_DB em runtime.

Tabelas de referência embarcadas (copiadas pelo ETL da origem):
    - unidade_administrativa / tipo_escola      → DRE, TipoEscola
    - v_cadastro_unidade_educacao               → UnidadeEducacional
    - serie_ensino                              → SerieEnsino
    - componente_curricular                     → ComponenteCurricular

Entidades próprias extraídas do EOL (EolConnection):
    - turma_escola                        → TurmaEscola
    - turma_escola_grade_programa         → TurmaEscolaGradePrograma
    - serie_turma_escola                  → SerieTurmaEscola
    - serie_turma_grade                   → SerieTurmaGrade
    - escola_grade                        → EscolaGrade
    - grade                               → Grade
    - grade_componente_curricular         → GradeComponenteCurricular
    - turma_grade_territorio_experiencia  → TurmaGradeTerritorioExperiencia
    - território_saber                    → TerritorioSaber
    - tipo_experiencia_pedagogica         → TipoExperienciaPedagogica
    - duracao_tipo_turno                  → DuracaoTipoTurno

Status da turma (st_turma_escola):
    'O' = Aberta, 'A' = Ativa, 'E' = Extinta, 'C' = Cancelada

Ordem de carga ETL:
    1.  DRE                         (embarcado — sem dependências)
    2.  TipoEscola                  (embarcado — sem dependências)
    3.  UnidadeEducacional          (embarcado — depende de: DRE, TipoEscola)
    4.  SerieEnsino                 (embarcado — sem dependências)
    5.  ComponenteCurricular        (embarcado — sem dependências)
    6.  TerritorioSaber
    7.  TipoExperienciaPedagogica
    8.  DuracaoTipoTurno
    9.  Grade                       (depende de: SerieEnsino, DuracaoTipoTurno)
    10. GradeComponenteCurricular   (depende de: Grade, ComponenteCurricular)
    11. EscolaGrade                 (depende de: Grade)
    12. TurmaEscola                 (depende de: UnidadeEducacional)
    13. SerieTurmaEscola            (depende de: TurmaEscola, SerieEnsino)
    14. SerieTurmaGrade             (depende de: TurmaEscola, EscolaGrade)
    15. TurmaEscolaGradePrograma    (depende de: TurmaEscola, EscolaGrade)
    16. TurmaGradeTerritorioExperiencia (depende de: SerieTurmaGrade,
        ComponenteCurricular, TerritorioSaber, TipoExperienciaPedagogica)
"""

from django.db import models

# ---------------------------------------------------------------------------
# Tabelas de referência embarcadas
# ---------------------------------------------------------------------------


class DRE(models.Model):
    """Diretoria Regional de Educação (embarcada do INSTITUCIONAL_DB).

    Fonte EOL: tabela `unidade_administrativa`
    (tp_unidade_administrativa = 'DRE').
    Embarcada para dispensar JOIN com INSTITUCIONAL_DB em runtime.
    """

    codigo_dre = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=200)
    sigla = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "dre"
        verbose_name = "diretoria regional de educação"
        verbose_name_plural = "diretorias regionais de educação"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_dre} - {self.sigla or self.nome}"


class TipoEscola(models.Model):
    """Tipo de unidade educacional (embarcado do INSTITUCIONAL_DB).

    Fonte EOL: tabela `tipo_escola`.
    Embarcado para dispensar JOIN com INSTITUCIONAL_DB em runtime.
    """

    codigo_tipo_escola = models.IntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)
    sigla = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "tipo_escola"
        verbose_name = "tipo de escola"
        verbose_name_plural = "tipos de escola"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_tipo_escola} - {self.descricao}"


class UnidadeEducacional(models.Model):
    """Unidade educacional (escola) embarcada do INSTITUCIONAL_DB.

    Fonte EOL: view `v_cadastro_unidade_educacao`.
    Campos nome_dre, sigla_dre e sigla_tipo_escola são desnormalizados
    para evitar JOINs adicionais nas queries do PedagogicoController.
    """

    codigo_ue = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=200)
    sigla = models.CharField(max_length=50, null=True, blank=True)
    codigo_dre = models.CharField(max_length=20)
    nome_dre = models.CharField(max_length=200, null=True, blank=True)
    sigla_dre = models.CharField(max_length=20, null=True, blank=True)
    codigo_tipo_escola = models.IntegerField(null=True, blank=True)
    sigla_tipo_escola = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "unidade_educacional"
        verbose_name = "unidade educacional"
        verbose_name_plural = "unidades educacionais"
        indexes = [
            models.Index(fields=["codigo_dre"], name="idx_ue_dre"),
            models.Index(fields=["codigo_tipo_escola"], name="idx_ue_tipo_escola"),
        ]

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_ue} - {self.nome}"


class SerieEnsino(models.Model):
    """Série de ensino (embarcada — era DOMINIOS_AUXILIAR_DB).

    Fonte EOL: tabela `serie_ensino`.
    Necessária para nomear séries em Grade, SerieTurmaEscola e SerieTurmaGrade
    sem depender de outro banco em runtime.
    """

    codigo_serie = models.IntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "serie_ensino"
        verbose_name = "série de ensino"
        verbose_name_plural = "séries de ensino"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_serie} - {self.descricao}"


class ComponenteCurricular(models.Model):
    """Componente curricular (disciplina) embarcado — era DOMINIOS_AUXILIAR_DB.

    Fonte EOL: tabela `componente_curricular` (EolConnection SQL Server).
    Necessário para nomear componentes em GradeComponenteCurricular e
    TurmaGradeTerritorioExperiencia sem depender de outro banco em runtime.
    """

    codigo_componente = models.IntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)
    descricao_sgp = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "componente_curricular"
        verbose_name = "componente curricular"
        verbose_name_plural = "componentes curriculares"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_componente} - {self.descricao}"


# ---------------------------------------------------------------------------
# Tabelas próprias do domínio pedagógico
# ---------------------------------------------------------------------------


class TerritorioSaber(models.Model):
    """Território do Saber — agrupamento temático do currículo de TdS.

    Fonte EOL: tabela `território_saber`.
    """

    codigo_territorio = models.IntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "territorio_saber"
        verbose_name = "território do saber"
        verbose_name_plural = "territórios do saber"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_territorio} - {self.descricao}"


class TipoExperienciaPedagogica(models.Model):
    """Tipo de experiência pedagógica vinculada ao Território do Saber.

    Fonte EOL: tabela `tipo_experiencia_pedagogica`.
    """

    codigo_experiencia = models.IntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "tipo_experiencia_pedagogica"
        verbose_name = "tipo de experiência pedagógica"
        verbose_name_plural = "tipos de experiências pedagógicas"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_experiencia} - {self.descricao}"


class DuracaoTipoTurno(models.Model):
    """Duração em horas por tipo de turno.

    Fonte EOL: tabela `duracao_tipo_turno`.
    Usada para determinar TurnoTurma (qt_hora_duracao).
    """

    id = models.BigAutoField(primary_key=True)
    codigo_tipo_turno = models.IntegerField()
    codigo_duracao = models.IntegerField()
    horas_duracao = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "duracao_tipo_turno"
        verbose_name = "duração por tipo de turno"
        verbose_name_plural = "durações por tipo de turno"
        unique_together = [("codigo_tipo_turno", "codigo_duracao")]


class TurmaEscola(models.Model):
    """Turma escolar — unidade fundamental de organização pedagógica.

    Fonte EOL: tabela `turma_escola`.
    Status: 'O'=Aberta, 'A'=Ativa, 'E'=Extinta, 'C'=Cancelada.
    Tipo: 1=Regular, 3=Programa.
    """

    codigo_turma = models.BigIntegerField(primary_key=True)
    codigo_escola = models.CharField(
        max_length=20,
        help_text="Código da escola — ref. UnidadeEducacional neste DB.",
    )
    ano_letivo = models.IntegerField()
    nome_turma = models.CharField(max_length=200)
    codigo_tipo_turma = models.IntegerField()
    codigo_duracao = models.IntegerField(null=True, blank=True)
    codigo_tipo_turno = models.IntegerField(null=True, blank=True)
    dt_fim = models.DateField(null=True, blank=True)
    dt_inicio_turma = models.DateField(null=True, blank=True)
    dt_fim_turma = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=1)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "turma_escola"
        verbose_name = "turma escolar"
        verbose_name_plural = "turmas escolares"
        indexes = [
            models.Index(fields=["codigo_escola"], name="idx_te_escola"),
            models.Index(fields=["ano_letivo"], name="idx_te_ano"),
            models.Index(fields=["status"], name="idx_te_status"),
            models.Index(
                fields=["codigo_escola", "ano_letivo"],
                name="idx_te_escola_ano",
            ),
        ]

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_turma} - {self.nome_turma} ({self.ano_letivo})"


class EscolaGrade(models.Model):
    """Associação entre escola e grade curricular.

    Fonte EOL: tabela `escola_grade`.
    """

    codigo_escola_grade = models.IntegerField(primary_key=True)
    codigo_escola = models.CharField(
        max_length=20,
        help_text="Código da escola — ref. UnidadeEducacional neste DB.",
    )
    codigo_grade = models.IntegerField()

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "escola_grade"
        verbose_name = "grade da escola"
        verbose_name_plural = "grades das escolas"
        indexes = [
            models.Index(fields=["codigo_escola"], name="idx_eg_escola"),
        ]


class Grade(models.Model):
    """Grade curricular — organiza séries, componentes e turnos.

    Fonte EOL: tabela `grade`.
    """

    codigo_grade = models.IntegerField(primary_key=True)
    codigo_serie_ensino = models.IntegerField(
        help_text="Série de ensino — ref. SerieEnsino neste DB.",
    )
    codigo_tipo_turno = models.IntegerField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "grade"
        verbose_name = "grade curricular"
        verbose_name_plural = "grades curriculares"


class GradeComponenteCurricular(models.Model):
    """Componente curricular (disciplina) associado a uma grade.

    Fonte EOL: tabela `grade_componente_curricular`.
    """

    id = models.BigAutoField(primary_key=True)
    codigo_grade = models.IntegerField(
        help_text="Grade curricular — ref. Grade neste DB.",
    )
    codigo_componente_curricular = models.IntegerField(
        help_text=("Componente curricular — ref. ComponenteCurricular neste DB."),
    )

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "grade_componente_curricular"
        verbose_name = "componente curricular da grade"
        verbose_name_plural = "componentes curriculares das grades"
        unique_together = [("codigo_grade", "codigo_componente_curricular")]
        indexes = [
            models.Index(
                fields=["codigo_componente_curricular"],
                name="idx_gcc_componente",
            ),
        ]


class SerieTurmaEscola(models.Model):
    """Série de ensino associada a uma turma.

    Fonte EOL: tabela `serie_turma_escola`.
    """

    id = models.BigAutoField(primary_key=True)
    turma = models.ForeignKey(
        TurmaEscola,
        on_delete=models.CASCADE,
        related_name="series",
    )
    codigo_serie_ensino = models.IntegerField(
        help_text="Série de ensino — ref. SerieEnsino neste DB.",
    )
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "serie_turma_escola"
        verbose_name = "série da turma"
        verbose_name_plural = "séries das turmas"


class SerieTurmaGrade(models.Model):
    """Série-grade associada a uma turma — chave de atribuição de aulas.

    Fonte EOL: tabela `serie_turma_grade`.
    É a entidade central de ligação entre TurmaEscola, EscolaGrade e
    AtribuicaoAula. Registros com dt_fim IS NULL estão ativos.
    """

    codigo_serie_grade = models.IntegerField(primary_key=True)
    turma = models.ForeignKey(
        TurmaEscola,
        on_delete=models.CASCADE,
        related_name="serie_grades",
    )
    codigo_escola = models.CharField(
        max_length=20,
        help_text="Escola da grade — ref. UnidadeEducacional neste DB.",
    )
    escola_grade = models.ForeignKey(
        EscolaGrade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="serie_turma_grades",
    )
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "serie_turma_grade"
        verbose_name = "série-grade da turma"
        verbose_name_plural = "séries-grade das turmas"
        indexes = [
            models.Index(fields=["dt_fim"], name="idx_stg_dt_fim"),
        ]


class TurmaEscolaGradePrograma(models.Model):
    """Grade/programa associado a uma turma (turmas de programa).

    Fonte EOL: tabela `turma_escola_grade_programa`.
    Usada para turmas do tipo cd_tipo_turma=3 (Programa).
    """

    codigo = models.BigIntegerField(primary_key=True)
    turma = models.ForeignKey(
        TurmaEscola,
        on_delete=models.CASCADE,
        related_name="grade_programas",
    )
    escola_grade = models.ForeignKey(
        EscolaGrade,
        on_delete=models.CASCADE,
        related_name="turma_programas",
    )
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "turma_escola_grade_programa"
        verbose_name = "grade/programa da turma"
        verbose_name_plural = "grades/programas das turmas"


class TurmaGradeTerritorioExperiencia(models.Model):
    """Vínculo entre série-grade, componente, território e experiência.

    Fonte EOL: tabela `turma_grade_territorio_experiencia`.
    Define quais componentes de uma grade pertencem ao currículo Território
    do Saber, e a qual experiência pedagógica estão associados.
    """

    id = models.BigAutoField(primary_key=True)
    serie_grade = models.ForeignKey(
        SerieTurmaGrade,
        on_delete=models.CASCADE,
        related_name="territorios_experiencias",
    )
    codigo_componente_curricular = models.IntegerField(
        help_text=("Componente curricular — ref. ComponenteCurricular neste DB."),
    )
    territorio_saber = models.ForeignKey(
        TerritorioSaber,
        on_delete=models.CASCADE,
        related_name="grade_territorios",
    )
    experiencia_pedagogica = models.ForeignKey(
        TipoExperienciaPedagogica,
        on_delete=models.CASCADE,
        related_name="grade_experiencias",
    )
    dt_inicio = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "pedagogico"
        db_table = "turma_grade_territorio_experiencia"
        verbose_name = "território/experiência da grade de turma"
        verbose_name_plural = "territórios/experiências das grades de turmas"
        indexes = [
            models.Index(
                fields=["codigo_componente_curricular"],
                name="idx_tgte_componente",
            ),
        ]
