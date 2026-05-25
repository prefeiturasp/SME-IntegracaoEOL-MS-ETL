"""Modelos do app programas — banco destino PROGRAMAS_DB.

Domínio: programas com, atualmente, PAP (Programa de Apoio Pedagógico) e PAEE
(Programa de Atendimento Educacional Especializado / SRM).

Hierarquia de modelos:
    TipoPrograma
        └── TurmaPrograma  (turmas cd_tipo_turma=3 do EOL)
                ├── TurmaProgramaComponenteCurricular
                └── MatriculaTurmaPrograma

Configuração de componentes por categoria:
    ComponenteCurricularPrograma
    (substitui as constantes hardcoded IDS_COMPONENTES_CURRICULARES_PAP_NOVO
    e COMPONENTE_CURRICULAR_ID_SRM do Pedagogico-API)

Referências cruzadas (sem FK física, integridade pela camada de aplicação):
    - codigo_turma                 → turma_programa.codigo_turma (mesmo banco)
    - codigo_componente_curricular → componente_curricular_programa (mesmo banco)
    - codigo_aluno                 → PEDAGOGICO_DB (aluno.codigo_aluno)
    - codigo_ue / codigo_dre       → PEDAGOGICO_DB (escola_unidade / unidade_administrativa)

Ordem de carga ETL:
    1. TipoPrograma                          (seed — dados estáticos do EOL)
    2. ComponenteCurricularPrograma          (seed — substituem constantes hardcoded)
    3. TurmaPrograma                         (ETL incremental)
    4. TurmaProgramaComponenteCurricular     (depende de: TurmaPrograma)
    5. MatriculaTurmaPrograma                (depende de: TurmaPrograma)
    6. MatriculaTurmaProgramaHistorico       (lê v_historico_matricula_cotic)
"""

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
    """Subtipos de programa do EOL (cd_tipo_programa), agrupados por categoria.

    O id preserva o mesmo valor do EOL — nenhum mapeamento necessário no ETL.
    O campo categoria discrimina PAP de PAEE sem necessidade de JOIN.

    Dados esperados (seed):
        649 → PAP Recuperação        (PAP)
        650 → PAP Colaborativo       (PAP)
        656 → PAEE SRM               (PAEE)
        657 → PAEE Colaborativo      (PAEE)
        658 → PAEE Itinerante        (PAEE)
    """

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
    """Componentes curriculares que caracterizam uma categoria de programa.

    Camada de configuração — substitui as constantes hardcoded no Pedagogico-API.
    Responde: "quais componentes identificam o PAP? quais identificam o PAEE?"

    Dados esperados (seed — PAP vigentes):
        1322 → PAP Recuperação de Aprendizagens
        1770 → PAP Projeto Colaborativo
        1804 → PAP 2º Ano Alfabetização
        1805 → PAP 2º Ano Colaborativo Alfabetização
    Dados esperados (seed — PAP legados) (deixei pra melhor visualização de como era o PAP antigo, sem os novos componentes de alfabetização):
        1033 → Recuperação Paralela Matemática
        1051 → Recuperação Paralela Ciências
        1052 → Recuperação Paralela Geografia
        1053 → Recuperação Paralela História
        1054 → Recuperação Paralela Português
    Dados esperados (seed — PAEE vigente):
        1030 → Sala de Recursos Multifuncionais
    """

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
    """Turmas de programa (cd_tipo_turma=3 no EOL) extraídas do EOL.

    Tabela central do domínio — referência lógica para TurmaProgramaComponenteCurricular
    e MatriculaTurmaPrograma. Cobre os endpoints de listagem de turmas PAP/SRM.

    Sem FK física para TipoPrograma — categoria é desnormalizada para permitir
    filtros PAP/PAEE diretos sem JOIN (ex: turmas-pap/{anoLetivo}/ues/{codigoEscola}).

    Os campos descricao_turno, codigo_ue e codigo_dre são desnormalizados para
    evitar JOINs nos endpoints que retornam dados de turma com informações de escola.

    situacao espelha SituacaoTurma do EOL:
        O = Organizada
        A = Não Organizada
        C = Concluída
        E = Extinta
    """

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
    """Componentes curriculares que uma turma de programa efetivamente oferece.

    Equivale à cadeia turma_escola_grade_programa → grade → grade_componente_curricular
    do EOL. Responde: "quais componentes essa turma específica cobre?"

    Cobre o endpoint {codigoAluno}/turmas-programa/{anoLetivo}/componentes-curriculares
    (ComponenteTurmaAlunoDto.NomeComponenteCurricular).

    Sem FK física — integridade garantida pela ordem de carga do ETL.
    """

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
    """Campos comuns às matrículas em turmas de programa (live e histórico).

    ``data_matricula`` é definida nas subclasses pois difere em nullability.
    """

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
    """Matrículas de alunos em turmas de programa, por componente curricular.

    Tabela principal para consultas — cobre os endpoints:
        - srm-paee/aluno/{codigoAluno}             → DadosSrmPaeeColaborativoDto
        - paee/turma-srm-e-regular/aluno/{cod}     → TurmasDoAlunoDTO
        - alunos-pap/{anoLetivo}                   → AlunosTurmaProgramaPapDto
        - pap/ano-letivo/{anoLetivo}               → AlunoTurmaPapDto

    Os campos ano_letivo, codigo_ue, codigo_dre e categoria são desnormalizados
    para permitir filtros diretos sem JOIN.

    codigo_situacao_matricula:
        1  → Ativo
        5  → Concluído
        6  → Pend. Rematrícula
        10 → Rematriculado
        13 → Sem continuidade
    """

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
    """Matrículas históricas em turmas de programa, por componente curricular.

    Espelha MatriculaTurmaPrograma, mas é carregada a partir de
    ``v_historico_matricula_cotic`` em vez de ``v_matricula_cotic`` (live).
    Permite que EP-05 (pap/ano-letivo/{anoLetivo}) retorne dados coerentes
    com o legado, que também lia do histórico.

    ``data_matricula`` é nullable — a view histórica pode não registrar essa
    data em todos os casos.
    """

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
            models.Index(
                fields=["ano_letivo"], name="idx_hist_matricula_ano"
            ),
            models.Index(
                fields=["codigo_ue"], name="idx_hist_matricula_ue"
            ),
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
