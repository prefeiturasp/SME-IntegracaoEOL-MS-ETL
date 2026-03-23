"""Modelos do app institucional — banco destino INSTITUCIONAL_DB.

Entidades extraídas das queries do EOL (EolConnection):
    - unidade_administrativa         → DRE
    - sub_prefeitura                 → SubPrefeitura
    - tipo_escola                    → TipoEscola
    - v_cadastro_unidade_educacao    → UnidadeEducacional

Referências cruzadas de entrada (campos que outros domínios usam para referenciar):
    - UnidadeEducacional.codigo_ue   → PROFESSORES_DB (codigo_unidade_educacao)
    - UnidadeEducacional.codigo_ue   → PEDAGOGICO_DB  (codigo_escola)
    - UnidadeEducacional.codigo_ue   → ALUNOS_DB      (via turma_escola)

Ordem de carga ETL:
    1. DRE                   (sem dependências internas)
    2. TipoEscola            (sem dependências internas)
    3. SubPrefeitura         (depende de: DRE)
    4. UnidadeEducacional    (depende de: DRE, TipoEscola, SubPrefeitura)
"""

from django.db import models


class DRE(models.Model):
    """Diretoria Regional de Educação.

    Fonte EOL: tabela `unidade_administrativa`
    filtrada por tp_unidade_administrativa = 'DRE'.
    """

    codigo_dre = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=200)
    sigla = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "institucional"
        db_table = "dre"
        verbose_name = "diretoria regional de educação"
        verbose_name_plural = "diretorias regionais de educação"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_dre} - {self.sigla or self.nome}"


class TipoEscola(models.Model):
    """Tipo de unidade educacional (EMEF, EMEI, CEI, CIEJA, etc.).

    Fonte EOL: tabela `tipo_escola`.
    """

    codigo_tipo_escola = models.IntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)

    class Meta:
        """Metadados do modelo."""

        app_label = "institucional"
        db_table = "tipo_escola"
        verbose_name = "tipo de escola"
        verbose_name_plural = "tipos de escola"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_tipo_escola} - {self.descricao}"


class SubPrefeitura(models.Model):
    """Sub-prefeitura vinculada a uma DRE.

    Fonte EOL: tabela `sub_prefeitura`.
    """

    codigo_subprefeitura = models.IntegerField(primary_key=True)
    nome = models.CharField(max_length=200)
    dre = models.ForeignKey(
        DRE,
        on_delete=models.CASCADE,
        related_name="subprefeituras",
    )

    class Meta:
        """Metadados do modelo."""

        app_label = "institucional"
        db_table = "sub_prefeitura"
        verbose_name = "sub-prefeitura"
        verbose_name_plural = "sub-prefeituras"

    def __str__(self) -> str:
        """Representação string."""
        return str(self.nome)


class UnidadeEducacional(models.Model):
    """Unidade educacional (escola) da rede municipal.

    Fonte EOL: view `v_cadastro_unidade_educacao`.

    O campo `codigo_ue` é o identificador referenciado pelos outros domínios:
        - PROFESSORES_DB usa como `codigo_unidade_educacao`
        - PEDAGOGICO_DB  usa como `codigo_escola`
    """

    codigo_ue = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=200)
    sigla = models.CharField(max_length=50, null=True, blank=True)
    dre = models.ForeignKey(
        DRE,
        on_delete=models.CASCADE,
        related_name="unidades",
    )
    tipo_escola = models.ForeignKey(
        TipoEscola,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unidades",
    )
    subprefeitura = models.ForeignKey(
        SubPrefeitura,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unidades",
    )

    class Meta:
        """Metadados do modelo."""

        app_label = "institucional"
        db_table = "unidade_educacional"
        verbose_name = "unidade educacional"
        verbose_name_plural = "unidades educacionais"
        indexes = [
            models.Index(fields=["dre"], name="idx_ue_dre"),
            models.Index(fields=["tipo_escola"], name="idx_ue_tipo_escola"),
        ]

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_ue} - {self.nome}"
