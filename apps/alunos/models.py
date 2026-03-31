"""Modelos do app alunos — banco destino ALUNOS_DB.

Domínio autossuficiente (v2.0): todas as tabelas de referência necessárias
para responder as queries do AlunoController são embarcadas aqui pelo ETL.
Nenhuma consulta a INSTITUCIONAL_DB ou PEDAGOGICO_DB em runtime.

Tabelas de referência embarcadas (copiadas pelo ETL da origem):
    - unidade_administrativa / tipo_escola      → DRE, TipoEscola
    - v_cadastro_unidade_educacao               → UnidadeEducacional
    - turma_escola                              → TurmaEscola

Entidades próprias extraídas do EOL (EolConnection):
    - v_aluno_cotic                    → Aluno
    - v_matricula_cotic                → Matricula
    - matricula_turma_escola           → MatriculaTurmaEscola
    - v_historico_matricula_cotic      → HistoricoMatricula
    - historico_matricula_turma_escola → HistoricoMatriculaTurmaEscola
    - responsavel_aluno                → ResponsavelAluno
    - necessidade_especial_aluno       → NecessidadeEspecialAluno

Situações de matrícula (cd_situacao_aluno):
    1=Ativo, 2=Desistente, 3=Transferido, 4=Vínculo Indevido,
    5=Concluído, 6=Pendente de Rematrícula, 7=Falecido,
    8=Não Compareceu, 10=Rematriculado, 11=Deslocamento,
    12=Cessado, 13=Sem continuidade, 14=Remanejado Saída,
    15=Reclassificado Saída, 16=Transferido SED,
    17=Dispensado Ed. Física

Ordem de carga ETL:
    1.  DRE                         (embarcado — sem dependências)
    2.  TipoEscola                  (embarcado — sem dependências)
    3.  UnidadeEducacional          (embarcado — depende de: DRE, TipoEscola)
    4.  TurmaEscola                 (embarcado — depende de: UnidadeEducacional)
    5.  Aluno
    6.  Matricula                   (depende de: Aluno)
    7.  HistoricoMatricula          (depende de: Aluno)
    8.  MatriculaTurmaEscola        (depende de: Matricula, TurmaEscola)
    9.  HistoricoMatriculaTurmaEscola (depende de: HistoricoMatricula)
    10. ResponsavelAluno            (depende de: Aluno)
    11. NecessidadeEspecialAluno    (depende de: Aluno)
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
    sigla = models.CharField(max_length=20, null=True, blank=True)  # NOSONAR alunos:models:60 - Manter compatilidade com o legado

    class Meta:
        """Metadados do modelo."""

        app_label = "alunos"
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
    sigla = models.CharField(max_length=10, null=True, blank=True)  # NOSONAR alunos:models:84 - Manter compatilidade com o legado

    class Meta:
        """Metadados do modelo."""

        app_label = "alunos"
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
    para evitar JOINs adicionais nas queries do AlunoController.
    """

    codigo_ue = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=200)
    sigla = models.CharField(max_length=50, null=True, blank=True)  # NOSONAR alunos:models:109 - Manter compatilidade com o legado
    codigo_dre = models.CharField(max_length=20)
    nome_dre = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR alunos:models:111 - Manter compatilidade com o legado
    sigla_dre = models.CharField(max_length=20, null=True, blank=True)  # NOSONAR alunos:models:112 - Manter compatilidade com o legado
    codigo_tipo_escola = models.IntegerField(null=True, blank=True)
    sigla_tipo_escola = models.CharField(max_length=10, null=True, blank=True)  # NOSONAR alunos:models:114 - Manter compatilidade com o legado

    class Meta:
        """Metadados do modelo."""

        app_label = "alunos"
        db_table = "unidade_educacional"
        verbose_name = "unidade educacional"
        verbose_name_plural = "unidades educacionais"
        indexes = [
            models.Index(fields=["codigo_dre"], name="alu_idx_ue_dre"),
            models.Index(fields=["codigo_tipo_escola"], name="alu_idx_ue_tipo_escola"),
        ]

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_ue} - {self.nome}"


class TurmaEscola(models.Model):
    """Turma escolar embarcada do PEDAGOGICO_DB.

    Fonte EOL: tabela `turma_escola`.
    Embarcada para permitir filtros por turma/escola/ano nas queries
    do AlunoController sem depender do PEDAGOGICO_DB em runtime.
    Status: 'O'=Aberta, 'A'=Ativa, 'E'=Extinta, 'C'=Cancelada.
    """

    codigo_turma = models.BigIntegerField(primary_key=True)
    codigo_escola = models.CharField(
        max_length=20,
        help_text="Código da escola — ref. UnidadeEducacional neste DB.",
    )
    ano_letivo = models.IntegerField()
    nome_turma = models.CharField(max_length=200)
    codigo_tipo_turma = models.IntegerField()
    status = models.CharField(max_length=1)

    class Meta:
        """Metadados do modelo."""

        app_label = "alunos"
        db_table = "turma_escola"
        verbose_name = "turma escolar"
        verbose_name_plural = "turmas escolares"
        indexes = [
            models.Index(fields=["codigo_escola"], name="alu_idx_te_escola"),
            models.Index(fields=["ano_letivo"], name="alu_idx_te_ano"),
            models.Index(
                fields=["codigo_escola", "ano_letivo"],
                name="alu_idx_te_escola_ano",
            ),
        ]

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_turma} - {self.nome_turma} ({self.ano_letivo})"


# ---------------------------------------------------------------------------
# Tabelas próprias do domínio alunos
# ---------------------------------------------------------------------------


class Aluno(models.Model):
    """Aluno da rede municipal de ensino.

    Fonte EOL: view `v_aluno_cotic` + tabela `aluno`
    (para nm_mae_aluno e dt_atualizacao).
    """

    codigo_aluno = models.BigIntegerField(primary_key=True)
    nome = models.CharField(max_length=200)
    nome_social = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR alunos:models:187 - Manter compatilidade com o legado
    dt_nascimento = models.DateField(null=True, blank=True)
    nome_mae = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR alunos:models:189 - Manter compatilidade com o legado
    dt_atualizacao_contato = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "alunos"
        db_table = "aluno"
        verbose_name = "aluno"
        verbose_name_plural = "alunos"
        indexes = [
            models.Index(fields=["nome"], name="idx_aluno_nome"),
        ]

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_aluno} - {self.nome}"


class Matricula(models.Model):
    """Matrícula ativa do aluno (ano corrente).

    Fonte EOL: view `v_matricula_cotic`.
    """

    codigo_matricula = models.BigIntegerField(primary_key=True)
    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name="matriculas",
    )
    ano_letivo = models.IntegerField()
    dt_status_matricula = models.DateField(null=True, blank=True)
    status_matricula = models.IntegerField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "alunos"
        db_table = "matricula"
        verbose_name = "matrícula"
        verbose_name_plural = "matrículas"
        indexes = [
            models.Index(fields=["ano_letivo"], name="idx_matricula_ano"),
        ]


class MatriculaTurmaEscola(models.Model):
    """Vínculo da matrícula ativa com turma escolar.

    Fonte EOL: tabela `matricula_turma_escola`.
    Situações ativas: 1 (Ativo), 6 (Pendente Rematrícula),
    10 (Rematriculado), 13 (Sem continuidade).
    """

    id = models.BigAutoField(primary_key=True)
    matricula = models.ForeignKey(
        Matricula,
        on_delete=models.CASCADE,
        related_name="turmas",
    )
    codigo_turma_escola = models.BigIntegerField(
        help_text="Código da turma — ref. TurmaEscola neste DB.",
    )
    codigo_situacao_aluno = models.IntegerField()
    dt_situacao_aluno = models.DateField(null=True, blank=True)
    nr_chamada_aluno = models.CharField(max_length=10, null=True, blank=True) # NOSONAR

    class Meta:
        """Metadados do modelo."""

        app_label = "alunos"
        db_table = "matricula_turma_escola"
        verbose_name = "matrícula em turma"
        verbose_name_plural = "matrículas em turmas"
        indexes = [
            models.Index(fields=["codigo_turma_escola"], name="idx_mte_turma"),
            models.Index(
                fields=["codigo_situacao_aluno"],
                name="idx_mte_situacao",
            ),
        ]


class HistoricoMatricula(models.Model):
    """Matrícula histórica do aluno (anos anteriores).

    Fonte EOL: view `v_historico_matricula_cotic`.
    """

    codigo_matricula = models.BigIntegerField(primary_key=True)
    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name="historico_matriculas",
    )
    ano_letivo = models.IntegerField()
    dt_status_matricula = models.DateField(null=True, blank=True)
    status_matricula = models.IntegerField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "alunos"
        db_table = "historico_matricula"
        verbose_name = "histórico de matrícula"
        verbose_name_plural = "históricos de matrículas"
        indexes = [
            models.Index(fields=["ano_letivo"], name="idx_hm_ano"),
        ]


class HistoricoMatriculaTurmaEscola(models.Model):
    """Vínculo de matrícula histórica com turma escolar.

    Fonte EOL: tabela `historico_matricula_turma_escola`.
    """

    id = models.BigAutoField(primary_key=True)
    historico_matricula = models.ForeignKey(
        HistoricoMatricula,
        on_delete=models.CASCADE,
        related_name="turmas",
    )
    codigo_turma_escola = models.BigIntegerField(
        help_text="Código da turma — ref. TurmaEscola neste DB.",
    )
    codigo_situacao_aluno = models.IntegerField()
    dt_situacao_aluno = models.DateField(null=True, blank=True)
    nr_chamada_aluno = models.CharField(max_length=10, null=True, blank=True) # NOSONAR

    class Meta:
        """Metadados do modelo."""

        app_label = "alunos"
        db_table = "historico_matricula_turma_escola"
        verbose_name = "histórico matrícula em turma"
        verbose_name_plural = "históricos matrículas em turmas"
        indexes = [
            models.Index(fields=["codigo_turma_escola"], name="idx_hmte_turma"),
        ]


class ResponsavelAluno(models.Model):
    """Responsável pelo aluno (pais/guardiões).

    Fonte EOL: tabela `responsavel_aluno`.
    Registros com dt_fim IS NULL representam o responsável atual ativo.
    """

    id = models.BigAutoField(primary_key=True)
    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name="responsaveis",
    )
    nome = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR alunos:models:345 - Manter compatilidade com o legado
    tipo_pessoa_responsavel = models.IntegerField(null=True, blank=True)
    ddd_celular = models.CharField(max_length=4, null=True, blank=True)  # NOSONAR alunos:models:347 - Manter compatilidade com o legado
    nr_celular = models.CharField(max_length=20, null=True, blank=True)  # NOSONAR alunos:models:348 - Manter compatilidade com o legado
    dt_atualizacao = models.DateTimeField(null=True, blank=True)
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "alunos"
        db_table = "responsavel_aluno"
        verbose_name = "responsável pelo aluno"
        verbose_name_plural = "responsáveis pelos alunos"
        indexes = [
            models.Index(fields=["dt_fim"], name="idx_ra_dt_fim"),
        ]


class NecessidadeEspecialAluno(models.Model):
    """Necessidade educacional especial (NEE) do aluno.

    Fonte EOL: tabela `necessidade_especial_aluno`.
    Existência de registro indica que o aluno possui deficiência
    (PossuiDeficiencia = 1).
    """

    id = models.BigAutoField(primary_key=True)
    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name="necessidades_especiais",
    )
    tipo_necessidade_especial = models.IntegerField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "alunos"
        db_table = "necessidade_especial_aluno"
        verbose_name = "necessidade especial do aluno"
        verbose_name_plural = "necessidades especiais dos alunos"
