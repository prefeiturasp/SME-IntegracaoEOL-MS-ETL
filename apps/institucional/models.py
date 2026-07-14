"""Modelos do app institucional — banco destino INSTITUCIONAL_DB.

Entidades extraídas das queries do EOL (EolConnection):
    - tipo_escola                    → TipoEscola
    - sub_prefeitura                 → SubPrefeitura
    - unidade_administrativa         → DRE
    - v_unidade_educacao_dados_gerais → UnidadeEducacional

Ordem de carga ETL:
    1. TipoEscola        (sem dependências internas)
    2. DRE               (sem dependências internas)
    3. SubPrefeitura     (sem dependências internas)
    4. UnidadeEducacional (depende de: DRE, TipoEscola, SubPrefeitura)

Modelos de auditoria (roteados para `default` via DominioRouter):
    - InstitucionalConsultaLog
"""

from django.db import models


class TipoEscola(models.Model):
    """Tipo de unidade educacional (EMEF, EMEI, CEI, CIEJA, etc.).

    Fonte EOL: tabela `tipo_escola`.
    """

    codigo_tipo_escola = models.IntegerField(primary_key=True)
    sigla = models.CharField(max_length=20, null=True, blank=True)  # NOSONAR
    descricao = models.CharField(max_length=200)
    data_atualizacao = models.DateTimeField(null=True, blank=True)

    class Meta:

        app_label = "institucional"
        db_table = "tipo_escola"
        verbose_name = "tipo de escola"
        verbose_name_plural = "tipos de escola"

    def __str__(self) -> str:
        return f"{self.codigo_tipo_escola} - {self.descricao}"


class DRE(models.Model):
    """Diretoria Regional de Educação.

    Fonte EOL: tabela `unidade_administrativa`
    filtrada por tp_unidade_administrativa = 24.
    """

    codigo_dre = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=200)
    sigla = models.CharField(max_length=100, null=True, blank=True)  # NOSONAR
    tipo_unidade_adm = models.IntegerField(null=True, blank=True)
    descricao_unidade_adm = models.CharField(
        max_length=200, null=True, blank=True  # NOSONAR
    )  # fmt: skip

    class Meta:

        app_label = "institucional"
        db_table = "dre"
        verbose_name = "diretoria regional de educação"
        verbose_name_plural = "diretorias regionais de educação"

    def __str__(self) -> str:
        return f"{self.codigo_dre} - {self.sigla or self.nome}"


class SubPrefeitura(models.Model):
    """Sub-prefeitura do município de São Paulo.

    Fonte EOL: tabela `sub_prefeitura`.
    """

    codigo_sub_prefeitura = models.IntegerField(primary_key=True)
    sigla = models.CharField(max_length=20, null=True, blank=True)  # NOSONAR
    nome = models.CharField(max_length=200)

    class Meta:

        app_label = "institucional"
        db_table = "sub_prefeitura"
        verbose_name = "sub-prefeitura"
        verbose_name_plural = "sub-prefeituras"

    def __str__(self) -> str:
        return str(self.nome)


class UnidadeEducacional(models.Model):
    """Unidade educacional (escola) da rede municipal.

    Fonte EOL: view `v_unidade_educacao_dados_gerais` + joins.

    O campo `codigo_ue` é o identificador referenciado pelos outros domínios:
        - PROFESSORES_DB usa como `codigo_unidade_educacao`
        - PEDAGOGICO_DB  usa como `codigo_escola`
    """

    codigo_ue = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=200)
    nome_nao_oficial = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    tipo_ue = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    tipo_logradouro = models.CharField(max_length=100, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    codigo_logradouro = models.IntegerField(null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    logradouro = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    numero = models.CharField(max_length=20, null=True, blank=True)  # NOSONAR
    bairro = models.CharField(max_length=100, null=True, blank=True)  # NOSONAR
    cep = models.CharField(max_length=10, null=True, blank=True)  # NOSONAR
    municipio = models.CharField(max_length=100, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    distrito = models.CharField(max_length=100, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    email = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR
    telefone_1 = models.CharField(max_length=50, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    telefone_2 = models.CharField(max_length=50, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    ano_construcao = models.IntegerField(null=True, blank=True)
    propriedade = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    organizacao_parceira = models.BooleanField(default=False)
    eh_ceu = models.BooleanField(default=False)
    data_atualizacao = models.DateTimeField(null=True, blank=True)
    vagas_matutino = models.IntegerField(default=0)
    vagas_vespertino = models.IntegerField(default=0)
    vagas_noturno = models.IntegerField(default=0)
    vagas_intermediario = models.IntegerField(default=0)
    vagas_integral = models.IntegerField(default=0)
    vagas_total = models.IntegerField(default=0)
    quantidade_funcionarios = models.IntegerField(default=0)
    status = models.CharField(max_length=10, null=True, blank=True)  # NOSONAR
    codigo_inep = models.IntegerField(null=True, blank=True)
    codigo_tp_equipamento = models.IntegerField(null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    codigo_tipo_unidade_educacao = models.IntegerField(null=True, blank=True)  # NOSONAR  # noqa: E501  # fmt: skip
    codigo_ue_integracao = models.CharField(
        max_length=50, null=True, blank=True  # NOSONAR
    )  # fmt: skip
    dre = models.ForeignKey(
        DRE,
        on_delete=models.CASCADE,
        related_name="unidades",
        db_column="codigo_dre",
    )
    tipo_escola = models.ForeignKey(
        TipoEscola,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unidades",
        db_column="codigo_tipo_escola",
    )
    subprefeitura = models.ForeignKey(
        SubPrefeitura,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unidades",
        db_column="codigo_sub_prefeitura",
    )

    class Meta:

        app_label = "institucional"
        db_table = "unidade_educacional"
        verbose_name = "unidade educacional"
        verbose_name_plural = "unidades educacionais"
        indexes = [
            models.Index(fields=["dre"], name="idx_ue_dre"),
            models.Index(fields=["tipo_escola"], name="idx_ue_tipo_escola"),
            models.Index(
                fields=["subprefeitura"], name="idx_ue_subprefeitura"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.codigo_ue} - {self.nome}"


class InstitucionalConsultaLog(models.Model):
    """Histórico de consultas paginadas do domínio institucional.

    Roteado para o banco `default` (sinc_rec_db) via DominioRouter.
    """

    id = models.BigAutoField(primary_key=True)
    limite = models.IntegerField()
    offset_inicial = models.IntegerField()
    total_retorno = models.IntegerField()
    executado_em = models.DateTimeField(auto_now_add=True)

    class Meta:

        app_label = "controle_auditoria"

        db_table = "institucional_consulta_log"
        verbose_name = "log de consulta institucional"
        verbose_name_plural = "logs de consulta institucional"

    def __str__(self) -> str:
        return f"offset={self.offset_inicial} limite={self.limite}"
