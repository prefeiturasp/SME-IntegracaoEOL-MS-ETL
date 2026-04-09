"""Modelos do app professores — banco destino PROFESSORES_DB.

Domínio de professores: armazena apenas os dados próprios do domínio.
Referências a domínios externos (DRE, Escola, Turma, ComponenteCurricular,
SerieEnsino, TerritorioSaber, ExperienciaPedagogica, Cargo) são mantidas
somente como IDs (IntegerField / CharField). As descrições e dados completos
desses domínios são resolvidos em tempo de resposta pelo Transition Gateway.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TABELAS DE SUPORTE (estruturais — necessárias para filtros e junções)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  UnidadeEducacional   → cd_unidade_educacao + codigo_dre + codigo_tipo_escola
  TurmaEscola          → cd_turma_escola + status + an_letivo + dt_fim_turma
  SerieTurmaGrade      → cd_serie_grade + IDs de turma e escola_grade
  TurmaEscolaGradePrograma → IDs de turma e escola_grade
  TurmaGradeTerritorioExperiencia → IDs de serie_grade, componente,
                                    territorio e experiencia

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TABELAS DE DOMÍNIO (dados específicos de professores — EolConnection)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cargo                           → CargoBaseServidor.codigo_cargo (ID)
    v_servidor_cotic                → Professor
    v_cargo_base_cotic              → CargoBaseServidor
    lotacao_servidor                → LotacaoServidor
    cargo_sobreposto_servidor       → CargoSobrepostoServidor
    funcao_atividade_cargo_servidor → FuncaoAtividadeCargoServidor
    laudo_medico                    → LaudoMedico
    funcao_funcionario_externo      → ContratoExterno.codigo_tipo_funcao (ID)
    pessoa                          → Pessoa
    contrato_externo                → ContratoExterno
    atribuicao_aula                 → AtribuicaoAula
    atribuicao_externo              → AtribuicaoExterno

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORDEM DE CARGA ETL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Fase 1 — sem dependências:
     1. UnidadeEducacional
     2. TurmaEscola
     3. Professor
     4. Pessoa

  Fase 2 — dependem de fase 1:
     5. SerieTurmaGrade          (→ TurmaEscola via ID)
     6. TurmaEscolaGradePrograma (→ TurmaEscola via ID)
     7. CargoBaseServidor        (→ Professor)
     8. ContratoExterno          (→ Pessoa)

  Fase 3 — dependem de fase 2:
     9. TurmaGradeTerritorioExperiencia (IDs de serie_grade, componente,
                                         territorio, experiencia)
    10. LotacaoServidor                 (→ CargoBaseServidor)
    11. CargoSobrepostoServidor         (→ CargoBaseServidor)
    12. FuncaoAtividadeCargoServidor    (→ CargoBaseServidor)
    13. LaudoMedico                     (→ CargoBaseServidor)
    14. AtribuicaoAula                  (→ CargoBaseServidor)
    15. AtribuicaoExterno               (→ ContratoExterno)
    16. AgrupamentoAtribuicaoTerritorioSaber (ref: rf_professor, codigo_turma)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CARGOS QUE NÃO IMPEDEM ATRIBUIÇÃO (cargo_sobreposto):
    3379, 3085, 3360
"""

from django.db import models

# ---------------------------------------------------------------------------
# Constantes de Descrição (Acessibilidade e DRY)
# ---------------------------------------------------------------------------
_BASE_DESC = "ID da {} neste DB."
_HELP_UE = _BASE_DESC.format("UnidadeEducacional")
_HELP_TURMA = _BASE_DESC.format("TurmaEscola")
_HELP_STG = _BASE_DESC.format("SerieTurmaGrade")
_HELP_GRADE = "ID da escola_grade — ref. domínio pedagógico."
_HELP_COMP = "ID do componente curricular" + " — ref. domínio curricular."
_HELP_TERR = "ID do território do saber — ref. domínio pedagógico."
_HELP_EXP = "ID da experiência pedagógica — ref. domínio pedagógico."

# ===========================================================================
# TABELAS DE SUPORTE (estruturais — filtros e junções de professor)
# ===========================================================================


class UnidadeEducacional(models.Model):
    """Unidade educacional (escola) — somente IDs necessários para filtros.

    Fonte EOL: view `v_cadastro_unidade_educacao`.
    Armazena apenas os IDs que permitem filtrar professor por escola, DRE
    e tipo de escola. Nomes e siglas são resolvidos pelo Transition Gateway.
    """

    codigo_ue = models.CharField(max_length=20, primary_key=True)
    codigo_dre = models.CharField(
        max_length=20,
        null=True,  # NOSONAR - Manter compatibilidade com o legado
        blank=True,
        help_text="ID da DRE — ref. domínio institucional.",
    )
    codigo_tipo_escola = models.IntegerField(
        null=True,
        blank=True,
        help_text=(
            "ID do tipo de escola"
            " — usado em filtros tp_escola IN @tiposEscola."
        ),
    )

    class Meta:

        app_label = "professores"
        db_table = "unidade_educacional"
        verbose_name = "unidade educacional"
        verbose_name_plural = "unidades educacionais"
        indexes = [
            models.Index(fields=["codigo_dre"], name="prof_idx_ue_dre"),
            models.Index(
                fields=["codigo_tipo_escola"], name="prof_idx_ue_tipo_escola"
            ),
        ]

    def __str__(self) -> str:
        return str(self.codigo_ue)


class TurmaEscola(models.Model):
    """Turma escolar — campos necessários para filtros de atribuição.

    Fonte EOL: tabela `turma_escola`.
    Status: 'O'=Aberta, 'A'=Ativa, 'E'=Extinta, 'C'=Cancelada.

    Filtro principal: st_turma_escola IN ('O','A','C','E').
    """

    codigo_turma = models.BigIntegerField(primary_key=True)
    codigo_escola = models.CharField(
        max_length=20,
        help_text=_HELP_UE,
    )
    ano_letivo = models.IntegerField()
    status = models.CharField(
        max_length=1,
        help_text="'O'=Aberta, 'A'=Ativa, 'E'=Extinta, 'C'=Cancelada.",
    )
    dt_fim_turma = models.DateField(null=True, blank=True)
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:

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
        return f"{self.codigo_turma} ({self.ano_letivo})"


class SerieTurmaGrade(models.Model):
    """Série-grade associada a uma turma — chave de atribuição de aulas.

    Fonte EOL: tabela `serie_turma_grade`.
    Entidade central de ligação entre TurmaEscola, escola_grade
    e AtribuicaoAula.
    Registros com dt_fim IS NULL estão ativos.
    """

    codigo_serie_grade = models.IntegerField(primary_key=True)
    codigo_turma = models.BigIntegerField(
        help_text=_HELP_TURMA,
    )
    codigo_escola = models.CharField(
        max_length=20,
        help_text=_HELP_UE,
    )
    codigo_escola_grade = models.IntegerField(
        help_text=_HELP_GRADE,
    )
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:

        app_label = "professores"
        db_table = "serie_turma_grade"
        verbose_name = "série-grade da turma"
        verbose_name_plural = "séries-grade das turmas"
        indexes = [
            models.Index(fields=["codigo_turma"], name="prof_idx_stg_turma"),
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
    codigo_turma = models.BigIntegerField(
        help_text=_HELP_TURMA,
    )
    codigo_escola_grade = models.IntegerField(
        help_text=_HELP_GRADE,
    )
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:

        app_label = "professores"
        db_table = "turma_escola_grade_programa"
        verbose_name = "grade/programa da turma"
        verbose_name_plural = "grades/programas das turmas"
        indexes = [
            models.Index(fields=["codigo_turma"], name="prof_idx_tegp_turma"),
        ]


class TurmaGradeTerritorioExperiencia(models.Model):
    """Vínculo entre série-grade, componente, território e experiência.

    Fonte EOL: tabela `turma_grade_territorio_experiencia`.
    Define quais componentes de uma grade pertencem ao currículo
    Território do Saber e a qual experiência pedagógica estão associados.
    Todos os campos são IDs — descrições resolvidas pelo Transition Gateway.
    """

    id = models.BigAutoField(primary_key=True)
    codigo_serie_grade = models.IntegerField(
        help_text=_HELP_STG,
    )
    codigo_componente_curricular = models.IntegerField(
        help_text=_HELP_COMP,
    )
    codigo_territorio_saber = models.IntegerField(
        help_text=_HELP_TERR,
    )
    codigo_experiencia_pedagogica = models.IntegerField(
        help_text=_HELP_EXP,
    )
    dt_inicio = models.DateField(null=True, blank=True)

    class Meta:

        app_label = "professores"
        db_table = "turma_grade_territorio_experiencia"
        verbose_name = "território/experiência da grade de turma"
        verbose_name_plural = "territórios/experiências das grades de turmas"
        indexes = [
            models.Index(
                fields=["codigo_serie_grade"],
                name="prof_idx_tgte_serie_grade",
            ),
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
    Descrições de território e experiência são resolvidas pelo
    Transition Gateway.
    """

    codigo_agrupamento = models.BigIntegerField(primary_key=True)
    codigo_territorio_saber = models.IntegerField(
        null=True,
        blank=True,
        help_text=_HELP_TERR,
    )
    codigo_experiencia_pedagogica = models.IntegerField(
        null=True,
        blank=True,
        help_text=_HELP_EXP,
    )
    dt_inicio_atribuicao = models.DateField(null=True, blank=True)
    ano_atribuicao = models.IntegerField(null=True, blank=True)
    dt_fim_atribuicao = models.DateField(null=True, blank=True)
    dt_fim_turma = models.DateField(null=True, blank=True)
    rf_professor = models.CharField(
        max_length=20,
        null=True,  # NOSONAR - Manter compatibilidade com o legado
        blank=True,
        help_text="Ref. Professor.codigo_rf neste DB.",
    )
    codigo_turma = models.BigIntegerField(
        null=True,
        blank=True,
        help_text=_HELP_TURMA,
    )
    codigos_componentes_curriculares = models.TextField(
        null=True,  # NOSONAR - Manter compatibilidade com o legado
        blank=True,
        help_text="Lista de IDs de componentes separados por vírgula.",
    )
    ano_letivo = models.IntegerField(null=True, blank=True)
    codigo_motivo_disponibilizacao = models.IntegerField(null=True, blank=True)
    encerramento_atribuicao_agrupamento_atualizado = models.BooleanField(
        null=True, blank=True
    )
    criado_em = models.DateTimeField(null=True, blank=True)
    alterado_em = models.DateTimeField(null=True, blank=True)

    class Meta:

        app_label = "professores"
        db_table = "agrupamento_atribuicao_territorio_saber"
        verbose_name = "agrupamento de atribuição TdS"
        verbose_name_plural = "agrupamentos de atribuições TdS"
        indexes = [
            models.Index(
                fields=["rf_professor"], name="prof_idx_aats_professor"
            ),
            models.Index(fields=["codigo_turma"], name="prof_idx_aats_turma"),
            models.Index(fields=["ano_letivo"], name="prof_idx_aats_ano"),
        ]


# ===========================================================================
# DADOS DE PROFESSORES — SERVIDORES EFETIVOS
# ===========================================================================


class Professor(models.Model):
    """Servidor público com perfil de professor na rede municipal.

    Fonte EOL: view `v_servidor_cotic`.
    Identificado pelo Registro Funcional (RF).
    """

    codigo_rf = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=200)
    nome_social = models.CharField(
        max_length=200, null=True, blank=True  # NOSONAR
    )  # fmt: skip

    class Meta:

        app_label = "professores"
        db_table = "professor"
        verbose_name = "professor"
        verbose_name_plural = "professores"

    def __str__(self) -> str:
        return f"{self.codigo_rf} - {self.nome}"


class CargoBaseServidor(models.Model):
    """Nomeação/cargo base do servidor no quadro funcional.

    Fonte EOL: view `v_cargo_base_cotic`.
    Representa o vínculo formal do servidor com seu cargo efetivo.
    dt_fim_nomeacao IS NULL = nomeação ativa.
    codigo_cargo é ID do domínio RH — descrição resolvida pelo
    Transition Gateway.
    """

    id = models.BigAutoField(primary_key=True)
    professor = models.ForeignKey(
        Professor,
        on_delete=models.CASCADE,
        related_name="cargos_base",
        db_column="codigo_rf",
        db_constraint=False,
    )
    codigo_cargo = models.IntegerField(
        help_text="ID do cargo — ref. domínio RH/funcional.",
    )
    dt_posse = models.DateField(null=True, blank=True)
    dt_fim_nomeacao = models.DateField(null=True, blank=True)
    dt_cancelamento = models.DateField(null=True, blank=True)

    class Meta:

        app_label = "professores"
        db_table = "cargo_base_servidor"
        verbose_name = "cargo base do servidor"
        verbose_name_plural = "cargos base dos servidores"
        indexes = [
            models.Index(fields=["professor"], name="idx_cbs_professor"),
            models.Index(fields=["codigo_cargo"], name="idx_cbs_cargo"),
            models.Index(
                fields=["dt_fim_nomeacao"],
                name="idx_cbs_fim_nomeacao",
            ),
        ]

    def __str__(self) -> str:
        return f"CargoBase #{self.pk} RF={self.professor_id}"


class LotacaoServidor(models.Model):
    """Lotação do servidor em unidade educacional.

    Fonte EOL: tabela `lotacao_servidor`.
    dt_fim IS NULL = lotação atual ativa.
    """

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="lotacoes",
        db_constraint=False,
    )
    codigo_unidade_educacao = models.CharField(
        max_length=20,
        help_text=_HELP_UE,
    )
    dt_inicio = models.DateField(null=True, blank=True)
    dt_fim = models.DateField(null=True, blank=True)

    class Meta:

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
    codigo_cargo é ID do domínio RH — descrição resolvida pelo
    Transition Gateway.
    """

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="cargos_sobrepostos",
        db_constraint=False,
    )
    codigo_cargo = models.IntegerField(
        help_text="ID do cargo sobreposto — ref. domínio RH/funcional.",
    )
    codigo_unidade_local_servico = models.CharField(
        max_length=20,
        help_text="ID da UE onde o cargo sobreposto é exercido.",
    )
    dt_fim_cargo_sobreposto = models.DateField(null=True, blank=True)

    class Meta:

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
        db_constraint=False,
    )
    codigo_unidade_local_servico = models.CharField(
        max_length=20,
        help_text="ID da UE onde a função é exercida.",
    )
    dt_fim_funcao_atividade = models.DateField(null=True, blank=True)

    class Meta:

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
        db_constraint=False,
    )

    class Meta:

        app_label = "professores"
        db_table = "laudo_medico"
        verbose_name = "laudo médico"
        verbose_name_plural = "laudos médicos"


# ===========================================================================
# DADOS DE PROFESSORES — CONTRATADOS EXTERNOS
# ===========================================================================


class Pessoa(models.Model):
    """Pessoa física que atua como professor contratado (externo).

    Fonte EOL: tabela `pessoa`.
    Identificada por CPF (cd_cpf_pessoa) — equivalente ao RF para externos.
    Nas queries, nm_social prevalece sobre nm_pessoa quando preenchido.
    """

    codigo_pessoa = models.BigIntegerField(primary_key=True)
    cpf = models.CharField(max_length=14, unique=True)
    nome = models.CharField(max_length=200)
    nome_social = models.CharField(
        max_length=200, null=True, blank=True  # NOSONAR
    )  # fmt: skip

    class Meta:

        app_label = "professores"
        db_table = "pessoa"
        verbose_name = "pessoa"
        verbose_name_plural = "pessoas"

    def __str__(self) -> str:
        return f"{self.cpf} - {self.nome}"


class ContratoExterno(models.Model):
    """Contrato de professor externo/terceirizado com a rede municipal.

    Fonte EOL: tabela `contrato_externo`.
    Ativo quando: dt_cancelamento IS NULL
    AND cd_motivo_desligamento_externo IS NULL.
    codigo_tipo_funcao é ID do tipo de função — ref. domínio funcional.
    """

    codigo_contrato = models.BigIntegerField(primary_key=True)
    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.CASCADE,
        related_name="contratos",
        db_constraint=False,
    )
    codigo_tipo_funcao = models.IntegerField(
        help_text="ID do tipo de função do funcionário externo.",
    )
    codigo_unidade_educacao = models.CharField(
        max_length=20,
        help_text=_HELP_UE,
    )
    dt_cancelamento = models.DateField(null=True, blank=True)
    codigo_motivo_desligamento = models.IntegerField(null=True, blank=True)

    class Meta:

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
    Todos os IDs de componente, grade e série referenciam domínios externos.
    """

    id = models.BigAutoField(primary_key=True)
    cargo_base = models.ForeignKey(
        CargoBaseServidor,
        on_delete=models.CASCADE,
        related_name="atribuicoes",
        db_constraint=False,
    )
    codigo_unidade_educacao = models.CharField(
        max_length=20,
        help_text=_HELP_UE,
    )
    codigo_turma_escola = models.BigIntegerField(
        null=True,
        blank=True,
        help_text=_HELP_TURMA,
    )
    codigo_turma_escola_grade_programa = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="ID da TurmaEscolaGradePrograma neste DB.",
    )
    codigo_grade = models.IntegerField(
        help_text=_HELP_GRADE,
    )
    codigo_componente_curricular = models.IntegerField(
        help_text=_HELP_COMP,
    )
    codigo_serie_grade = models.IntegerField(
        help_text="ID da SerieTurmaGrade neste DB.",
    )
    ano_atribuicao = models.IntegerField()
    dt_atribuicao_aula = models.DateField()
    dt_disponibilizacao_aulas = models.DateField(null=True, blank=True)
    codigo_motivo_disponibilizacao = models.IntegerField(null=True, blank=True)
    dt_cancelamento = models.DateField(null=True, blank=True)

    class Meta:

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
        db_constraint=False,
    )
    codigo_unidade_educacao = models.CharField(
        max_length=20,
        help_text=_HELP_UE,
    )
    codigo_grade = models.IntegerField(
        help_text=_HELP_GRADE,
    )
    codigo_componente_curricular = models.IntegerField(
        help_text=_HELP_COMP,
    )
    codigo_serie_grade = models.IntegerField(
        help_text="ID da SerieTurmaGrade neste DB.",
    )
    codigo_turma_escola_grade_programa = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="ID da TurmaEscolaGradePrograma neste DB.",
    )
    ano_atribuicao = models.IntegerField()
    dt_atribuicao = models.DateField()
    dt_disponibilizacao = models.DateField(null=True, blank=True)
    codigo_motivo_disponibilizacao_externo = models.IntegerField(
        null=True, blank=True
    )
    dt_cancelamento = models.DateField(null=True, blank=True)

    class Meta:

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
