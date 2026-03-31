"""Modelos do app programas — banco destino PROGRAMAS_DB.

Entidades extraídas das queries do ApiEolConnection (PostgreSQL da API EOL):
    - ComponenteCurricular      → ComponenteCurricularApi
    - componentecurricularpai   → ComponenteCurricularPai
    - componentecurricularpap   → ComponenteCurricularPap
    - RegenciaComponenteCurricular → RegenciaComponenteCurricular
    - agrupamentoatribuicaoterritoriosaber → AgrupamentoAtribuicaoTerritorioSaber
    - parametros                → Parametro
    - turma_tipo_itinerario     → TurmaTipoItinerario
    - grupos                    → Grupo
    - grupocargos               → GrupoCargo
    - grupofuncoesatividades    → GrupoFuncaoAtividade

Referências cruzadas (sem FK física):
    - rf_professor    → PROFESSORES_DB (professor.codigo_rf)
    - codigo_turma    → PEDAGOGICO_DB  (turma_escola.codigo_turma)

Ordem de carga ETL:
    1. Parametro
    2. TurmaTipoItinerario
    3. Grupo
    4. ComponenteCurricularApi
    5. ComponenteCurricularPai     (depende de: ComponenteCurricularApi)
    6. ComponenteCurricularPap     (depende de: ComponenteCurricularApi)
    7. RegenciaComponenteCurricular (depende de: ComponenteCurricularApi)
    8. GrupoCargo                  (depende de: Grupo)
    9. GrupoFuncaoAtividade        (depende de: Grupo)
    10. AgrupamentoAtribuicaoTerritorioSaber
"""

from django.db import models


class Parametro(models.Model):
    """Parâmetros de configuração do sistema (ApiEolConnection).

    Fonte: tabela `parametros` (ApiEolConnection).
    Usada para configurações como tipos de modalidade, etc.
    """

    nome = models.CharField(max_length=200, primary_key=True)
    valor = models.TextField()

    class Meta:
        """Metadados do modelo."""

        app_label = "programas"
        db_table = "parametro"
        verbose_name = "parâmetro"
        verbose_name_plural = "parâmetros"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.nome}={self.valor}"


class TurmaTipoItinerario(models.Model):
    """Tipo de itinerário formativo para turmas (ApiEolConnection).

    Fonte: tabela `turma_tipo_itinerario` (ApiEolConnection).
    """

    id = models.IntegerField(primary_key=True)
    nome = models.CharField(max_length=200)
    serie = models.CharField(max_length=50, null=True, blank=True)  # NOSONAR programas:models:66 - Manter compatilidade com o legado

    class Meta:
        """Metadados do modelo."""

        app_label = "programas"
        db_table = "turma_tipo_itinerario"
        verbose_name = "tipo de itinerário de turma"
        verbose_name_plural = "tipos de itinerários de turmas"


class ComponenteCurricularApi(models.Model):
    """Componente curricular conforme catálogo da API EOL (ApiEolConnection).

    Fonte: tabela `ComponenteCurricular` (ApiEolConnection).
    Difere da tabela `componente_curricular` do EolConnection (SQL Server):
    contém flags de regência e território, além do código de integração.
    """

    id = models.IntegerField(primary_key=True)
    codigo_componente = models.IntegerField(
        unique=True,
        help_text="Código do componente no EolConnection — IdComponenteCurricular.",
    )
    eh_regencia = models.BooleanField(default=False)
    eh_territorio = models.BooleanField(default=False)
    descricao = models.CharField(max_length=200)

    class Meta:
        """Metadados do modelo."""

        app_label = "programas"
        db_table = "componente_curricular_api"
        verbose_name = "componente curricular (API)"
        verbose_name_plural = "componentes curriculares (API)"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_componente} - {self.descricao}"


class ComponenteCurricularPai(models.Model):
    """Relacionamento pai-filho entre componentes curriculares.

    Fonte: tabela `componentecurricularpai` (ApiEolConnection).
    """

    id = models.IntegerField(primary_key=True)
    componente = models.ForeignKey(
        ComponenteCurricularApi,
        on_delete=models.CASCADE,
        related_name="relacoes_pai",
        to_field="codigo_componente",
    )
    codigo_componente_pai = models.IntegerField(null=True, blank=True)
    vigencia = models.CharField(max_length=20, null=True, blank=True)  # NOSONAR programas:models:121 - Manter compatilidade com o legado

    class Meta:
        """Metadados do modelo."""

        app_label = "programas"
        db_table = "componente_curricular_pai"
        verbose_name = "componente curricular pai"
        verbose_name_plural = "componentes curriculares pai"


class ComponenteCurricularPap(models.Model):
    """Componentes curriculares elegíveis ao PAP (Prog. de Acompanhamento Pedagógico).

    Fonte: tabela `componentecurricularpap` (ApiEolConnection).
    """

    id = models.IntegerField(primary_key=True)
    componente = models.ForeignKey(
        ComponenteCurricularApi,
        on_delete=models.CASCADE,
        related_name="pap",
        to_field="codigo_componente",
    )

    class Meta:
        """Metadados do modelo."""

        app_label = "programas"
        db_table = "componente_curricular_pap"
        verbose_name = "componente curricular PAP"
        verbose_name_plural = "componentes curriculares PAP"


class RegenciaComponenteCurricular(models.Model):
    """Componentes de regência por turno e ano (ApiEolConnection).

    Fonte: tabela `RegenciaComponenteCurricular` (ApiEolConnection).
    Define quais componentes compõem a regência em cada turno/ano.
    """

    id = models.BigAutoField(primary_key=True)
    codigo_componente = models.IntegerField(
        help_text="Ref. ComponenteCurricularApi.codigo_componente.",
    )
    turno = models.IntegerField(null=True, blank=True)
    ano = models.IntegerField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "programas"
        db_table = "regencia_componente_curricular"
        verbose_name = "regência de componente curricular"
        verbose_name_plural = "regências de componentes curriculares"


class AgrupamentoAtribuicaoTerritorioSaber(models.Model):
    """Agrupamento de atribuição do programa Território do Saber (ApiEolConnection).

    Fonte: tabela `agrupamentoatribuicaoterritoriosaber` (ApiEolConnection).
    Agrupa atribuições de professores de TdS por turma, território e experiência.
    codigos_componentes_curriculares armazena lista separada por vírgula.
    """

    codigo_agrupamento = models.BigIntegerField(primary_key=True)
    codigo_territorio_saber = models.IntegerField(null=True, blank=True)
    codigo_experiencia_pedagogica = models.IntegerField(null=True, blank=True)
    dt_inicio_atribuicao = models.DateField(null=True, blank=True)
    ano_atribuicao = models.IntegerField(null=True, blank=True)
    dt_fim_atribuicao = models.DateField(null=True, blank=True)
    dt_fim_turma = models.DateField(null=True, blank=True)
    rf_professor = models.CharField(
        max_length=20,
        null=True,  # NOSONAR programas:models:195 - Manter compatilidade com o legado
        blank=True,
        help_text="RF do professor — ref. PROFESSORES_DB.",
    )
    codigo_turma = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Código da turma — ref. PEDAGOGICO_DB.",
    )
    codigos_componentes_curriculares = models.TextField(
        null=True,  # NOSONAR programas:models:205 - Manter compatilidade com o legado
        blank=True,
        help_text="Lista de códigos separados por vírgula.",
    )
    ano_letivo = models.IntegerField(null=True, blank=True)
    codigo_motivo_disponibilizacao = models.IntegerField(null=True, blank=True)
    descricao_territorio_saber = models.CharField(max_length=200, null=True, blank=True)  # NOSONAR programas:models:211 - Manter compatilidade com o legado
    descricao_experiencia_pedagogica = models.CharField(
        max_length=200, null=True, blank=True  # NOSONAR programas:models:213 - Manter compatilidade com o legado
    )
    encerramento_atribuicao_agrupamento_atualizado = models.BooleanField(
        null=True, blank=True
    )
    criado_em = models.DateTimeField(null=True, blank=True)
    alterado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "programas"
        db_table = "agrupamento_atribuicao_territorio_saber"
        verbose_name = "agrupamento de atribuição TdS"
        verbose_name_plural = "agrupamentos de atribuições TdS"
        indexes = [
            models.Index(fields=["rf_professor"], name="prog_idx_aats_professor"),
            models.Index(fields=["codigo_turma"], name="prog_idx_aats_turma"),
            models.Index(fields=["ano_letivo"], name="prog_idx_aats_ano"),
        ]


class Grupo(models.Model):
    """Grupo de permissão/perfil no sistema (ApiEolConnection).

    Fonte: tabela `grupos` (ApiEolConnection).
    Define perfis de acesso como professores, diretores, coordenadores, etc.
    """

    id = models.IntegerField(primary_key=True)
    guid_perfil = models.UUIDField(null=True, blank=True)
    id_abrangencia = models.IntegerField(null=True, blank=True)
    eh_perfil_manual = models.BooleanField(default=False)

    class Meta:
        """Metadados do modelo."""

        app_label = "programas"
        db_table = "grupo"
        verbose_name = "grupo"
        verbose_name_plural = "grupos"


class GrupoCargo(models.Model):
    """Cargos associados a um grupo de perfil (ApiEolConnection).

    Fonte: tabela `grupocargos` (ApiEolConnection).
    """

    id = models.BigAutoField(primary_key=True)
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name="cargos",
    )
    codigo_cargo = models.IntegerField(
        help_text="Código do cargo — ref. PROFESSORES_DB.",
    )

    class Meta:
        """Metadados do modelo."""

        app_label = "programas"
        db_table = "grupo_cargo"
        verbose_name = "cargo do grupo"
        verbose_name_plural = "cargos dos grupos"


class GrupoFuncaoAtividade(models.Model):
    """Funções de atividade associadas a um grupo de perfil (ApiEolConnection).

    Fonte: tabela `grupofuncoesatividades` (ApiEolConnection).
    """

    id = models.BigAutoField(primary_key=True)
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name="funcoes_atividade",
    )
    codigo_tipo_funcao_atividade = models.IntegerField()

    class Meta:
        """Metadados do modelo."""

        app_label = "programas"
        db_table = "grupo_funcao_atividade"
        verbose_name = "função de atividade do grupo"
        verbose_name_plural = "funções de atividade dos grupos"
