"""Modelos do app professores — banco destino PROFESSORES_DB.

Domínio autossuficiente: todas as tabelas de referência necessárias para
responder as queries do ProfessorController estão embarcadas neste banco.
Nenhuma consulta a outros serviços ou bancos é necessária em tempo de execução.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TABELAS DE REFERÊNCIA EMBARCADAS (origens externas, copiadas pelo ETL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Origem institucional (EolConnection):
    unidade_administrativa (tp=DRE) → DRE
    tipo_escola              → TipoEscola
    v_cadastro_unidade_educacao → UnidadeEducacional

  Origem dominios_auxiliar (EolConnection):
    componente_curricular    → ComponenteCurricular
    serie_ensino             → SerieEnsino

  Origem pedagogico (EolConnection):
    território_saber         → TerritorioSaber
    tipo_experiencia_pedagogica → TipoExperienciaPedagogica
    grade                    → Grade
    escola_grade             → EscolaGrade
    turma_escola             → TurmaEscola
    serie_turma_grade        → SerieTurmaGrade
    turma_escola_grade_programa → TurmaEscolaGradePrograma
    turma_grade_territorio_experiencia → TurmaGradeTerritorioExperiencia

  Origem programas (ApiEolConnection):
    agrupamentoatribuicaoterritoriosaber → AgrupamentoAtribuicaoTerritorioSaber

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TABELAS DE DOMÍNIO (dados específicos de professores — EolConnection)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cargo                           → Cargo
    v_servidor_cotic                → Professor
    v_cargo_base_cotic              → CargoBaseServidor
    lotacao_servidor                → LotacaoServidor
    cargo_sobreposto_servidor       → CargoSobrepostoServidor
    funcao_atividade_cargo_servidor → FuncaoAtividadeCargoServidor
    laudo_medico                    → LaudoMedico
    funcao_funcionario_externo      → FuncaoFuncionarioExterno
    pessoa                          → Pessoa
    contrato_externo                → ContratoExterno
    atribuicao_aula                 → AtribuicaoAula
    atribuicao_externo              → AtribuicaoExterno

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORDEM DE CARGA ETL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Fase 1 — referências sem dependências:
     1. DRE
     2. TipoEscola
     3. ComponenteCurricular
     4. SerieEnsino
     5. TerritorioSaber
     6. TipoExperienciaPedagogica
     7. Grade
     8. Cargo
     9. FuncaoFuncionarioExterno

  Fase 2 — dependem de fase 1:
    10. UnidadeEducacional     (→ DRE, TipoEscola)
    11. EscolaGrade            (→ Grade)
    12. TurmaEscola
    13. Professor              (→ Cargo)
    14. Pessoa

  Fase 3 — dependem de fase 2:
    15. SerieTurmaGrade                 (→ TurmaEscola, EscolaGrade)
    16. TurmaEscolaGradePrograma        (→ TurmaEscola, EscolaGrade)
    17. CargoBaseServidor               (→ Professor, Cargo)
    18. ContratoExterno                 (→ Pessoa, FuncaoFuncionarioExterno)

  Fase 4 — dependem de fase 3:
    19. TurmaGradeTerritorioExperiencia (→ SerieTurmaGrade, TerritorioSaber,
                                           TipoExperienciaPedagogica)
    20. LotacaoServidor                 (→ CargoBaseServidor)
    21. CargoSobrepostoServidor         (→ CargoBaseServidor, Cargo)
    22. FuncaoAtividadeCargoServidor    (→ CargoBaseServidor)
    23. LaudoMedico                     (→ CargoBaseServidor)
    24. AtribuicaoAula                  (→ CargoBaseServidor)
    25. AtribuicaoExterno               (→ ContratoExterno)
    26. AgrupamentoAtribuicaoTerritorioSaber  (ref: rf_professor, codigo_turma)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CARGOS DE PROFESSOR (cd_cargo):
    3239, 3247, 3255, 3263, 3271, 3280, 3298, 3301,
    3336, 3344, 3840, 3859, 3867, 3874, 3883, 3884
CARGOS QUE NÃO IMPEDEM ATRIBUIÇÃO (cargo_sobreposto):
    3379, 3085, 3360
"""

from django.db import models

# ===========================================================================
# REFERÊNCIAS INSTITUCIONAIS (embarcadas de institucional / EolConnection)
# ===========================================================================


class DRE(models.Model):
    """Diretoria Regional de Educação.

    Fonte EOL: tabela `unidade_administrativa`
    (tp_unidade_administrativa = 24).
    Necessária para retornar CodigoDre / NomeDre / SiglaDre nas queries
    do ProfessorController.
    """

    codigo_dre = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=200)
    sigla = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "dre"
        verbose_name = "diretoria regional de educação"
        verbose_name_plural = "diretorias regionais de educação"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_dre} - {self.sigla or self.nome}"


class TipoEscola(models.Model):
    """Tipo de unidade educacional (EMEF, EMEI, CEI, CIEJA, etc.).

    Fonte EOL: tabela `tipo_escola`.
    Usado no filtro `tp_escola IN @tiposEscola` das queries do
    ProfessorController.
    """

    codigo_tipo_escola = models.IntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)
    sigla = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "tipo_escola"
        verbose_name = "tipo de escola"
        verbose_name_plural = "tipos de escola"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_tipo_escola} - {self.sigla or self.descricao}"


class UnidadeEducacional(models.Model):
    """Unidade educacional (escola) da rede municipal.

    Fonte EOL: view `v_cadastro_unidade_educacao`
    + `unidade_administrativa` (DRE).

    Armazena dados da escola e da DRE desnormalizados para evitar joins:
      - CodigoEscola / NomeEscola / SiglaEscola
      - CodigoDREEscola / NomeDre / SiglaDre
      - tp_escola (para filtros WHERE tp_escola IN @tiposEscola)
    """

    codigo_ue = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=200)
    sigla = models.CharField(max_length=50, null=True, blank=True)
    dre = models.ForeignKey(
        DRE,
        on_delete=models.CASCADE,
        related_name="unidades",
        db_column="codigo_dre",
    )
    # Desnormalizados da DRE para evitar JOIN ao retornar NomeDre/SiglaDre
    nome_dre = models.CharField(max_length=200)
    sigla_dre = models.CharField(max_length=20, null=True, blank=True)
    tipo_escola = models.ForeignKey(
        TipoEscola,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unidades",
        db_column="codigo_tipo_escola",
    )
    # Desnormalizado para filtros rápidos por tipo
    sigla_tipo_escola = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "unidade_educacional"
        verbose_name = "unidade educacional"
        verbose_name_plural = "unidades educacionais"
        indexes = [
            models.Index(fields=["dre"], name="prof_idx_ue_dre"),
            models.Index(fields=["tipo_escola"], name="prof_idx_ue_tipo_escola"),
        ]

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_ue} - {self.nome}"


# ===========================================================================
# REFERÊNCIAS CURRICULARES (embarcadas de dominios_auxiliar / EolConnection)
# ===========================================================================


class ComponenteCurricular(models.Model):
    """Componente curricular (disciplina) do EolConnection.

    Fonte EOL: tabela `componente_curricular`.
    Usado para retornar DescricaoComponenteCurricular e no filtro
    cd_componente_curricular das atribuições.
    Registros com dt_cancelamento NOT NULL indicam componentes cancelados.
    """

    codigo = models.IntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)
    dt_cancelamento = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "componente_curricular"
        verbose_name = "componente curricular"
        verbose_name_plural = "componentes curriculares"
        indexes = [
            models.Index(
                fields=["dt_cancelamento"],
                name="idx_cc_cancelamento",
            ),
        ]

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo} - {self.descricao}"


class SerieEnsino(models.Model):
    """Série de ensino — sg_resumida_serie retornada como AnoTurma.

    Fonte EOL: tabela `serie_ensino`.
    Necessária para retornar AnoTurma em
    ObterComponentesCurricularesTerritorioAtribuidos.
    """

    codigo_serie = models.IntegerField(primary_key=True)
    sigla_resumida = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="sg_resumida_serie — exibida como AnoTurma nas queries.",
    )

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "serie_ensino"
        verbose_name = "série de ensino"
        verbose_name_plural = "séries de ensino"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_serie} - {self.sigla_resumida}"


# ===========================================================================
# REFERÊNCIAS PEDAGÓGICAS (embarcadas de pedagogico / EolConnection)
# ===========================================================================


class TerritorioSaber(models.Model):
    """Território do Saber — agrupamento temático do currículo TdS.

    Fonte EOL: tabela `território_saber`.
    Retornado como CodigoTerritorioSaber / DescricaoTerritorioSaber
    nas queries.
    """

    codigo_territorio = models.IntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "territorio_saber"
        verbose_name = "território do saber"
        verbose_name_plural = "territórios do saber"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_territorio} - {self.descricao}"


class TipoExperienciaPedagogica(models.Model):
    """Tipo de experiência pedagógica vinculada ao Território do Saber.

    Fonte EOL: tabela `tipo_experiencia_pedagogica`.
    Retornado como CodigoExperienciaPedagogica /
    DescricaoExperienciaPedagogica.
    """

    codigo_experiencia = models.IntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "tipo_experiencia_pedagogica"
        verbose_name = "tipo de experiência pedagógica"
        verbose_name_plural = "tipos de experiências pedagógicas"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_experiencia} - {self.descricao}"


class Grade(models.Model):
    """Grade curricular — organiza séries, componentes e turnos.

    Fonte EOL: tabela `grade`.
    Usada como elo entre EscolaGrade, SerieTurmaGrade e AtribuicaoAula.
    """

    codigo_grade = models.IntegerField(primary_key=True)
    codigo_serie_ensino = models.IntegerField(
        help_text="Ref. SerieEnsino.codigo_serie neste DB.",
    )
    codigo_tipo_turno = models.IntegerField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "grade"
        verbose_name = "grade curricular"
        verbose_name_plural = "grades curriculares"


class EscolaGrade(models.Model):
    """Associação entre escola e grade curricular.

    Fonte EOL: tabela `escola_grade`.
    Elo entre UnidadeEducacional e Grade; referenciada por SerieTurmaGrade
    e TurmaEscolaGradePrograma.
    """

    codigo_escola_grade = models.IntegerField(primary_key=True)
    codigo_escola = models.CharField(
        max_length=20,
        help_text="Ref. UnidadeEducacional.codigo_ue neste DB.",
    )
    grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name="escola_grades",
        db_column="codigo_grade",
    )

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "escola_grade"
        verbose_name = "grade da escola"
        verbose_name_plural = "grades das escolas"
        indexes = [
            models.Index(fields=["codigo_escola"], name="prof_idx_eg_escola"),
        ]


class TurmaEscola(models.Model):
    """Turma escolar — unidade fundamental de organização pedagógica.

    Fonte EOL: tabela `turma_escola`.
    Status: 'O'=Aberta, 'A'=Ativa, 'E'=Extinta, 'C'=Cancelada.
    Tipo: 1=Regular, 3=Programa.

    Filtro principal: st_turma_escola IN ('O','A') AND an_letivo = @AnoLetivo.
    """

    codigo_turma = models.BigIntegerField(primary_key=True)
    codigo_escola = models.CharField(
        max_length=20,
        help_text="Ref. UnidadeEducacional.codigo_ue neste DB.",
    )
    ano_letivo = models.IntegerField()
    nome_turma = models.CharField(max_length=200)
    codigo_tipo_turma = models.IntegerField(
        help_text="1=Regular, 3=Programa.",
    )
    codigo_duracao = models.IntegerField(null=True, blank=True)
    codigo_tipo_turno = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=1,
        help_text="'O'=Aberta, 'A'=Ativa, 'E'=Extinta, 'C'=Cancelada.",
    )
    dt_inicio_turma = models.DateField(null=True, blank=True)
    dt_fim_turma = models.DateField(null=True, blank=True)
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "turma_escola"
        verbose_name = "turma escolar"
        verbose_name_plural = "turmas escolares"
        indexes = [
            models.Index(fields=["codigo_escola"], name="prof_idx_te_escola"),
            models.Index(fields=["ano_letivo"], name="prof_idx_te_ano"),
            models.Index(fields=["status"], name="prof_idx_te_status"),
            models.Index(
                fields=["codigo_escola", "ano_letivo"],
                name="prof_idx_te_escola_ano",
            ),
        ]

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_turma} - {self.nome_turma} ({self.ano_letivo})"


class SerieTurmaGrade(models.Model):
    """Série-grade associada a uma turma — chave de atribuição de aulas.

    Fonte EOL: tabela `serie_turma_grade`.
    Entidade central de ligação entre TurmaEscola, EscolaGrade
    e AtribuicaoAula.
    Registros com dt_fim IS NULL estão ativos.
    """

    codigo_serie_grade = models.IntegerField(primary_key=True)
    turma = models.ForeignKey(
        TurmaEscola,
        on_delete=models.CASCADE,
        related_name="serie_grades",
        db_column="codigo_turma",
    )
    codigo_escola = models.CharField(
        max_length=20,
        help_text="Ref. UnidadeEducacional.codigo_ue neste DB.",
    )
    escola_grade = models.ForeignKey(
        EscolaGrade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="serie_turma_grades",
        db_column="codigo_escola_grade",
    )
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "serie_turma_grade"
        verbose_name = "série-grade da turma"
        verbose_name_plural = "séries-grade das turmas"
        indexes = [
            models.Index(fields=["dt_fim"], name="prof_idx_stg_dt_fim"),
            models.Index(fields=["codigo_escola"], name="prof_idx_stg_escola"),
        ]


class TurmaEscolaGradePrograma(models.Model):
    """Grade/programa associado a turmas do tipo Programa (cd_tipo_turma=3).

    Fonte EOL: tabela `turma_escola_grade_programa`.
    Referenciada por AtribuicaoAula.codigo_turma_escola_grade_programa
    e AtribuicaoExterno.codigo_turma_escola_grade_programa.
    """

    codigo = models.BigIntegerField(primary_key=True)
    turma = models.ForeignKey(
        TurmaEscola,
        on_delete=models.CASCADE,
        related_name="grade_programas",
        db_column="codigo_turma",
    )
    escola_grade = models.ForeignKey(
        EscolaGrade,
        on_delete=models.CASCADE,
        related_name="turma_programas",
        db_column="codigo_escola_grade",
    )
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "turma_escola_grade_programa"
        verbose_name = "grade/programa da turma"
        verbose_name_plural = "grades/programas das turmas"


class TurmaGradeTerritorioExperiencia(models.Model):
    """Vínculo entre série-grade, componente, território e experiência.

    Fonte EOL: tabela `turma_grade_territorio_experiencia`.
    Define quais componentes de uma grade pertencem ao currículo
    Território do Saber e a qual experiência pedagógica estão associados.
    Necessária para ObterComponentesCurricularesTerritorioAtribuidos.
    """

    id = models.BigAutoField(primary_key=True)
    serie_grade = models.ForeignKey(
        SerieTurmaGrade,
        on_delete=models.CASCADE,
        related_name="territorios_experiencias",
        db_column="codigo_serie_grade",
    )
    codigo_componente_curricular = models.IntegerField(
        help_text="Ref. ComponenteCurricular.codigo neste DB.",
    )
    territorio_saber = models.ForeignKey(
        TerritorioSaber,
        on_delete=models.CASCADE,
        related_name="grade_territorios",
        db_column="codigo_territorio",
    )
    experiencia_pedagogica = models.ForeignKey(
        TipoExperienciaPedagogica,
        on_delete=models.CASCADE,
        related_name="grade_experiencias",
        db_column="codigo_experiencia",
    )
    dt_inicio = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "turma_grade_territorio_experiencia"
        verbose_name = "território/experiência da grade de turma"
        verbose_name_plural = "territórios/experiências das grades de turmas"
        indexes = [
            models.Index(
                fields=["codigo_componente_curricular"],
                name="prof_idx_tgte_componente",
            ),
        ]


# ===========================================================================
# REFERÊNCIAS DE PROGRAMAS (embarcadas de programas / ApiEolConnection)
# ===========================================================================


class AgrupamentoAtribuicaoTerritorioSaber(models.Model):
    """Agrupamento de atribuição do programa Território do Saber.

    Fonte: tabela `agrupamentoatribuicaoterritoriosaber` (ApiEolConnection).
    Necessária para as queries:
      - VerificaSeTemAtribuicaoTurmaTerritorioSaberQuery
      - ObterUsuariosComAtribuicaoTerritorioSaberQuery
      - ObterAtribuicoesDoProfessorPorAnoLetivoTerritorioDoSaberQuery
    rf_professor referencia Professor.codigo_rf neste DB.
    codigo_turma referencia TurmaEscola.codigo_turma neste DB.
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
        null=True,
        blank=True,
        help_text="Ref. Professor.codigo_rf neste DB.",
    )
    codigo_turma = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Ref. TurmaEscola.codigo_turma neste DB.",
    )
    codigos_componentes_curriculares = models.TextField(
        null=True,
        blank=True,
        help_text="Lista de códigos separados por vírgula.",
    )
    ano_letivo = models.IntegerField(null=True, blank=True)
    codigo_motivo_disponibilizacao = models.IntegerField(null=True, blank=True)
    descricao_territorio_saber = models.CharField(max_length=200, null=True, blank=True)
    descricao_experiencia_pedagogica = models.CharField(
        max_length=200, null=True, blank=True
    )
    encerramento_atribuicao_agrupamento_atualizado = models.BooleanField(
        null=True, blank=True
    )
    criado_em = models.DateTimeField(null=True, blank=True)
    alterado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "agrupamento_atribuicao_territorio_saber"
        verbose_name = "agrupamento de atribuição TdS"
        verbose_name_plural = "agrupamentos de atribuições TdS"
        indexes = [
            models.Index(fields=["rf_professor"], name="prof_idx_aats_professor"),
            models.Index(fields=["codigo_turma"], name="prof_idx_aats_turma"),
            models.Index(fields=["ano_letivo"], name="prof_idx_aats_ano"),
        ]


# ===========================================================================
# DADOS DE PROFESSORES — SERVIDORES EFETIVOS
# ===========================================================================


class Cargo(models.Model):
    """Cargo funcional do servidor (ex: PEB I, PEB II).

    Fonte EOL: tabela `cargo`.
    Cargos de professor: 3239, 3247, 3255, 3263, 3271, 3280, 3298,
                         3301, 3336, 3344, 3840, 3859, 3867, 3874, 3883, 3884.
    Cargos sobrepostos que NÃO impedem atribuição: 3379, 3085, 3360.
    """

    codigo_cargo = models.IntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "cargo"
        verbose_name = "cargo"
        verbose_name_plural = "cargos"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_cargo} - {self.descricao}"


class Professor(models.Model):
    """Servidor público com perfil de professor na rede municipal.

    Fonte EOL: view `v_servidor_cotic`.
    Identificado pelo Registro Funcional (RF).
    """

    codigo_rf = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=200)
    nome_social = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "professor"
        verbose_name = "professor"
        verbose_name_plural = "professores"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.codigo_rf} - {self.nome}"


class CargoBaseServidor(models.Model):
    """Nomeação/cargo base do servidor no quadro funcional.

    Fonte EOL: view `v_cargo_base_cotic`.
    Representa o vínculo formal do servidor com seu cargo efetivo.
    dt_fim_nomeacao IS NULL = nomeação ativa.
    """

    id = models.BigAutoField(primary_key=True)
    professor = models.ForeignKey(
        Professor,
        on_delete=models.CASCADE,
        related_name="cargos_base",
        db_column="codigo_rf",
    )
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.CASCADE,
        related_name="servidores",
    )
    dt_posse = models.DateField(null=True, blank=True)
    dt_fim_nomeacao = models.DateField(null=True, blank=True)
    dt_cancelamento = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "cargo_base_servidor"
        verbose_name = "cargo base do servidor"
        verbose_name_plural = "cargos base dos servidores"
        indexes = [
            models.Index(fields=["professor"], name="idx_cbs_professor"),
            models.Index(
                fields=["dt_fim_nomeacao"],
                name="idx_cbs_fim_nomeacao",
            ),
        ]

    def __str__(self) -> str:
        """Representação string."""
        return f"CargoBase #{self.pk} RF={self.professor_id}"


class LotacaoServidor(models.Model):
    """Lotação do servidor em unidade educacional.

    Fonte EOL: tabela `lotacao_servidor`.
    dt_fim IS NULL = lotação atual ativa.
    Filtro nas queries: dt_fim IS NULL OR dt_fim < GETDATE().
    """

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="lotacoes",
    )
    codigo_unidade_educacao = models.CharField(
        max_length=20,
        help_text="Ref. UnidadeEducacional.codigo_ue neste DB.",
    )
    dt_inicio = models.DateField(null=True, blank=True)
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "lotacao_servidor"
        verbose_name = "lotação do servidor"
        verbose_name_plural = "lotações dos servidores"
        indexes = [
            models.Index(fields=["codigo_unidade_educacao"], name="idx_ls_ue"),
            models.Index(fields=["dt_fim"], name="idx_ls_dt_fim"),
        ]


class CargoSobrepostoServidor(models.Model):
    """Cargo sobreposto exercido sobre o cargo base (ex: diretor, coordenador).

    Fonte EOL: tabela `cargo_sobreposto_servidor`.
    dt_fim_cargo_sobreposto IS NULL = sobreposto ativo, impede atribuição
    (exceto cargos 3379, 3085, 3360).
    """

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="cargos_sobrepostos",
    )
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.CASCADE,
        related_name="sobreposicoes",
    )
    codigo_unidade_local_servico = models.CharField(
        max_length=20,
        help_text="UE onde o cargo sobreposto é exercido.",
    )
    dt_fim_cargo_sobreposto = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "cargo_sobreposto_servidor"
        verbose_name = "cargo sobreposto do servidor"
        verbose_name_plural = "cargos sobrepostos dos servidores"
        indexes = [
            models.Index(
                fields=["dt_fim_cargo_sobreposto"],
                name="idx_css_dt_fim",
            ),
        ]


class FuncaoAtividadeCargoServidor(models.Model):
    """Função de atividade exercida pelo servidor em determinada unidade.

    Fonte EOL: tabela `funcao_atividade_cargo_servidor`.
    dt_fim_funcao_atividade IS NULL = função ativa.
    """

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="funcoes_atividade",
    )
    codigo_unidade_local_servico = models.CharField(
        max_length=20,
        help_text="UE onde a função é exercida.",
    )
    dt_fim_funcao_atividade = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "funcao_atividade_cargo_servidor"
        verbose_name = "função de atividade do cargo do servidor"
        verbose_name_plural = "funções de atividade dos cargos dos servidores"


class LaudoMedico(models.Model):
    """Registro de laudo médico que impede atribuição de aulas ao servidor.

    Fonte EOL: tabela `laudo_medico`.
    Existência de registro = servidor está impedido de receber atribuição.
    """

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="laudos_medicos",
    )

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "laudo_medico"
        verbose_name = "laudo médico"
        verbose_name_plural = "laudos médicos"


# ===========================================================================
# DADOS DE PROFESSORES — CONTRATADOS EXTERNOS
# ===========================================================================


class FuncaoFuncionarioExterno(models.Model):
    """Tipo de função exercida pelo funcionário externo (contratado).

    Fonte EOL: tabela `funcao_funcionario_externo`.
    dt_cancelamento IS NULL = função ativa.
    """

    codigo_tipo_funcao = models.IntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)
    dt_cancelamento = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "funcao_funcionario_externo"
        verbose_name = "função de funcionário externo"
        verbose_name_plural = "funções de funcionários externos"

    def __str__(self) -> str:
        """Representação string."""
        return str(self.descricao)


class Pessoa(models.Model):
    """Pessoa física que atua como professor contratado (externo).

    Fonte EOL: tabela `pessoa`.
    Identificada por CPF (cd_cpf_pessoa) — equivalente ao RF para externos.
    Nas queries, nm_social prevalece sobre nm_pessoa quando preenchido.
    """

    codigo_pessoa = models.BigIntegerField(primary_key=True)
    cpf = models.CharField(max_length=14, unique=True)
    nome = models.CharField(max_length=200)
    nome_social = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "pessoa"
        verbose_name = "pessoa"
        verbose_name_plural = "pessoas"

    def __str__(self) -> str:
        """Representação string."""
        return f"{self.cpf} - {self.nome}"


class ContratoExterno(models.Model):
    """Contrato de professor externo/terceirizado com a rede municipal.

    Fonte EOL: tabela `contrato_externo`.
    Ativo quando: dt_cancelamento IS NULL
    AND cd_motivo_desligamento_externo IS NULL.
    """

    codigo_contrato = models.BigIntegerField(primary_key=True)
    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.CASCADE,
        related_name="contratos",
    )
    tipo_funcao = models.ForeignKey(
        FuncaoFuncionarioExterno,
        on_delete=models.CASCADE,
        related_name="contratos",
    )
    codigo_unidade_educacao = models.CharField(
        max_length=20,
        help_text="Ref. UnidadeEducacional.codigo_ue neste DB.",
    )
    dt_cancelamento = models.DateField(null=True, blank=True)
    codigo_motivo_desligamento = models.IntegerField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "contrato_externo"
        verbose_name = "contrato externo"
        verbose_name_plural = "contratos externos"
        indexes = [
            models.Index(fields=["codigo_unidade_educacao"], name="idx_ce_ue"),
            models.Index(
                fields=["dt_cancelamento"],
                name="idx_ce_cancelamento",
            ),
        ]


# ===========================================================================
# ATRIBUIÇÕES DE AULAS
# ===========================================================================


class AtribuicaoAula(models.Model):
    """Atribuição de aulas ao professor efetivo (servidor concursado).

    Fonte EOL: tabela `atribuicao_aula`.
    Ativa quando:
        dt_cancelamento IS NULL
        AND dt_atribuicao_aula <= GETDATE()
        AND COALESCE(dt_disponibilizacao_aulas, GETDATE()) >= data_referencia
    """

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="atribuicoes",
    )
    codigo_unidade_educacao = models.CharField(
        max_length=20,
        help_text="Ref. UnidadeEducacional.codigo_ue neste DB.",
    )
    codigo_turma_escola = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Ref. TurmaEscola.codigo_turma neste DB.",
    )
    codigo_turma_escola_grade_programa = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Ref. TurmaEscolaGradePrograma.codigo neste DB.",
    )
    codigo_grade = models.IntegerField(
        help_text="Ref. Grade.codigo_grade neste DB.",
    )
    codigo_componente_curricular = models.IntegerField(
        help_text="Ref. ComponenteCurricular.codigo neste DB.",
    )
    codigo_serie_grade = models.IntegerField(
        help_text="Ref. SerieTurmaGrade.codigo_serie_grade neste DB.",
    )
    ano_atribuicao = models.IntegerField()
    dt_atribuicao_aula = models.DateField()
    dt_disponibilizacao_aulas = models.DateField(null=True, blank=True)
    codigo_motivo_disponibilizacao = models.IntegerField(null=True, blank=True)
    dt_cancelamento = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "atribuicao_aula"
        verbose_name = "atribuição de aula"
        verbose_name_plural = "atribuições de aulas"
        indexes = [
            models.Index(fields=["codigo_unidade_educacao"], name="idx_aa_ue"),
            models.Index(fields=["codigo_turma_escola"], name="idx_aa_turma"),
            models.Index(
                fields=["codigo_componente_curricular"],
                name="idx_aa_componente",
            ),
            models.Index(fields=["ano_atribuicao"], name="idx_aa_ano"),
            models.Index(
                fields=["dt_cancelamento"],
                name="idx_aa_cancelamento",
            ),
        ]


class AtribuicaoExterno(models.Model):
    """Atribuição de aulas ao professor externo/contratado.

    Fonte EOL: tabela `atribuicao_externo`.
    Ativa quando:
        dt_cancelamento IS NULL
        AND (cd_motivo_disponibilizacao_externo = 3
             OR (dt_atribuicao <= GETDATE()
                 AND COALESCE(dt_disponibilizacao, dt_fim_turma) >= GETDATE())
             OR COALESCE(dt_disponibilizacao, dt_fim_turma) >= dt_fim_turma)
    """

    id = models.BigAutoField(primary_key=True)
    contrato_externo = models.ForeignKey(
        ContratoExterno,
        on_delete=models.CASCADE,
        related_name="atribuicoes",
    )
    codigo_unidade_educacao = models.CharField(
        max_length=20,
        help_text="Ref. UnidadeEducacional.codigo_ue neste DB.",
    )
    codigo_grade = models.IntegerField(
        help_text="Ref. Grade.codigo_grade neste DB.",
    )
    codigo_componente_curricular = models.IntegerField(
        help_text="Ref. ComponenteCurricular.codigo neste DB.",
    )
    codigo_serie_grade = models.IntegerField(
        help_text="Ref. SerieTurmaGrade.codigo_serie_grade neste DB.",
    )
    codigo_turma_escola_grade_programa = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Ref. TurmaEscolaGradePrograma.codigo neste DB.",
    )
    ano_atribuicao = models.IntegerField()
    dt_atribuicao = models.DateField()
    dt_disponibilizacao = models.DateField(null=True, blank=True)
    codigo_motivo_disponibilizacao_externo = models.IntegerField(null=True, blank=True)
    dt_cancelamento = models.DateField(null=True, blank=True)

    class Meta:
        """Metadados do modelo."""

        app_label = "professores"
        db_table = "atribuicao_externo"
        verbose_name = "atribuição de professor externo"
        verbose_name_plural = "atribuições de professores externos"
        indexes = [
            models.Index(fields=["codigo_unidade_educacao"], name="idx_ae_ue"),
            models.Index(
                fields=["codigo_componente_curricular"],
                name="idx_ae_componente",
            ),
            models.Index(fields=["ano_atribuicao"], name="idx_ae_ano"),
            models.Index(
                fields=["dt_cancelamento"],
                name="idx_ae_cancelamento",
            ),
        ]
