"""Modelos do banco destino ALUNOS_DB."""

from django.db import models


class TipoNecessidadeEspecial(models.Model):
    """Tipos de necessidades especiais."""

    codigo_necessidade_especial = models.SmallIntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)
    codigo_estado = models.SmallIntegerField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    data_cancelamento = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "alunos"
        db_table = "tipo_necessidade_especial"
        verbose_name = "tipo de necessidade especial"
        verbose_name_plural = "tipos de necessidades especiais"

    def __str__(self) -> str:
        return f"{self.codigo_necessidade_especial} - {self.descricao}"


class Aluno(models.Model):
    """Informações do aluno."""

    codigo_aluno = models.BigIntegerField(primary_key=True)
    nome = models.CharField(max_length=200)
    nome_social = models.CharField(max_length=200, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=1, null=True, blank=True)
    cpf = models.CharField(max_length=11, null=True, blank=True)
    nome_mae = models.CharField(max_length=200, null=True, blank=True)
    nacionalidade = models.CharField(max_length=100, null=True, blank=True)
    nis = models.CharField(max_length=20, null=True, blank=True)
    raca_cor = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        app_label = "alunos"
        db_table = "aluno"
        verbose_name = "aluno"
        verbose_name_plural = "alunos"
        indexes = [
            models.Index(fields=["nome"], name="idx_aluno_nome"),
        ]

    def __str__(self) -> str:
        return f"{self.codigo_aluno} - {self.nome}"


class ResponsavelAluno(models.Model):
    """Responsáveis pelo aluno."""

    codigo_responsavel = models.BigIntegerField(primary_key=True)
    aluno = models.ForeignKey(
        Aluno,
        db_column="codigo_aluno",
        on_delete=models.CASCADE,
        related_name="responsaveis",
    )
    tipo_responsavel = models.SmallIntegerField(null=True, blank=True)
    nome = models.CharField(max_length=200, null=True, blank=True)
    cpf = models.CharField(max_length=11, null=True, blank=True)
    ddd_celular = models.CharField(max_length=4, null=True, blank=True)
    numero_celular = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=200, null=True, blank=True)
    autoriza_sms = models.CharField(max_length=1, null=True, blank=True)
    logradouro = models.CharField(max_length=255, null=True, blank=True)
    cep = models.IntegerField(null=True, blank=True)
    data_fim_vinculo = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "alunos"
        db_table = "responsavel_aluno"
        verbose_name = "responsável"
        verbose_name_plural = "responsáveis"

    def __str__(self) -> str:
        return f"{self.nome} (Aluno: {self.aluno_id})"


class NecessidadeEspecialAluno(models.Model):
    """Necessidades especiais do aluno."""

    codigo_necessidade_especial_aluno = models.BigIntegerField(
        primary_key=True, help_text="ID original do EOL (cd_identificador...)"
    )
    aluno = models.ForeignKey(
        Aluno,
        db_column="codigo_aluno",
        on_delete=models.CASCADE,
        related_name="necessidades",
    )
    necessidade_especial = models.ForeignKey(
        TipoNecessidadeEspecial,
        db_column="codigo_necessidade_especial",
        on_delete=models.CASCADE,
    )
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "alunos"
        db_table = "necessidade_especial_aluno"

    def __str__(self) -> str:
        return f"Aluno {self.aluno_id} - NEE {self.necessidade_especial_id}"


class Matricula(models.Model):
    """Matrícula escolar."""

    codigo_matricula = models.BigIntegerField(primary_key=True)
    aluno = models.ForeignKey(
        Aluno,
        db_column="codigo_aluno",
        on_delete=models.CASCADE,
        related_name="matriculas",
    )
    codigo_ue = models.CharField(max_length=20)
    ano_letivo = models.SmallIntegerField()
    data_status = models.DateField(null=True, blank=True)
    codigo_situacao_matricula = models.SmallIntegerField()
    situacao_matricula = models.CharField(max_length=100)

    class Meta:
        app_label = "alunos"
        db_table = "matricula"
        verbose_name = "matrícula"
        verbose_name_plural = "matrículas"
        indexes = [
            models.Index(fields=["codigo_ue"], name="idx_matricula_codigo_ue"),
            models.Index(
                fields=["ano_letivo"], name="idx_matricula_ano_letivo"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.codigo_matricula} ({self.ano_letivo})"


class MatriculaTurma(models.Model):
    """Matricula do aluno em turma."""

    id = models.BigAutoField(primary_key=True)
    matricula = models.ForeignKey(
        Matricula,
        db_column="codigo_matricula",
        on_delete=models.CASCADE,
        related_name="matriculas_turmas",
    )
    codigo_turma = models.BigIntegerField()
    numero_chamada = models.CharField(max_length=5, null=True, blank=True)
    data_situacao_aluno = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "alunos"
        db_table = "matricula_turma"
        unique_together = [("matricula", "codigo_turma")]
        indexes = [
            models.Index(
                fields=["codigo_turma"], name="idx_matricula_turma_codigo"
            )
        ]

    def __str__(self) -> str:
        return f"M: {self.matricula_id} - T: {self.codigo_turma}"
