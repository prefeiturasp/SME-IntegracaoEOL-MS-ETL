"""Regras de domínio para execução parametrizada do ETL."""

COMANDOS_POR_DOMINIO: dict[str, str] = {
    "institucional": "etl_institucional",
    "professores": "etl_professores",
    "alunos": "etl_alunos",
    "pedagogico": "etl_pedagogico",
    "programas": "etl_programas",
}

DOMINIOS_VALIDOS = [*COMANDOS_POR_DOMINIO.keys()]
DOMINIOS_COM_ANOS_LETIVOS = frozenset(
    {"alunos", "pedagogico", "professores", "programas"}
)
DOMINIOS_COM_FASES = frozenset({"alunos", "pedagogico"})

FASES_POR_DOMINIO: dict[str, tuple[str, ...]] = {
    "institucional": (
        "dre",
        "tipo_escola",
        "sub_prefeitura",
        "unidade_educacional",
        "dre_abrangencia",
    ),
    "pedagogico": (
        "componente_curricular",
        "componente_turma",
        "atribuicao_componente",
        "atribuicao_territorio_saber",
        "componente_curricular_api_eol",
        "componentecurricularhierarquia",
        "componentecurricularpap",
        "componentecurricularplanejamentoregencia",
        "turmaitinerarioensinomedio",
        "agrupamento_atribuicao_territorio_saber",
        "grade_componente_curricular",
        "turma",
        "turma_atribuida_dre_ue",
        "etapa_ensino",
        "ciclo_ensino",
    ),
    "professores": (
        "professor",
        "pessoa",
        "administrador_escola",
        "cargo_base_servidor",
        "contrato_externo",
        "lotacao_servidor",
        "cargo_sobreposto_servidor",
        "funcao_atividade",
        "laudo_medico",
        "atribuicao_aula",
        "atribuicao_externo",
        "funcionario_unidade_educacional",
        "funcionario_cargo",
        "funcionario_vinculo_funcional",
        "funcionario_conecta_modalidade_escola",
        "funcionario_conecta_formacao",
        "funcionario_sistema_perfil",
        "turma_atribuida_ue",
        "disciplina_turma_atribuida_ue",
        "professor_escola_ano",
    ),
    "programas": (
        "tipo_programa",
        "componente_curricular_programa",
        "turma_programa",
        "turma_programa_componente_curricular",
        "matricula_turma_programa",
        "matricula_turma_programa_historico",
        "aluno_pap_ano_letivo",
        "aluno_pap_ano_letivo_historico",
    ),
    "alunos": (
        "tipo_necessidade_especial",
        "aluno",
        "responsavel_aluno",
        "nee_aluno",
        "matricula",
        "matricula_turma",
        "matricula_ano_letivo",
        "matricula_componente_curricular_ano_letivo",
        "dados_aluno_acompanhamento_escolar",
        "responsavel_aluno_turma",
        "matricula_ano_anterior",
    ),
}

FASES_COM_ANOS_LETIVOS: dict[str, tuple[str, ...]] = {
    "alunos": (
        "aluno",
        "responsavel_aluno",
        "nee_aluno",
        "matricula",
        "matricula_turma",
        "matricula_ano_letivo",
        "matricula_componente_curricular_ano_letivo",
        "dados_aluno_acompanhamento_escolar",
        "responsavel_aluno_turma",
        "matricula_ano_anterior",
    ),
    "pedagogico": (
        "componente_turma",
        "atribuicao_componente",
        "atribuicao_territorio_saber",
        "grade_componente_curricular",
        "turma",
        "turma_atribuida_dre_ue",
    ),
    "professores": (
        "atribuicao_aula",
        "atribuicao_externo",
        "turma_atribuida_ue",
        "disciplina_turma_atribuida_ue",
        "professor_escola_ano",
    ),
    "programas": (
        "turma_programa",
        "matricula_turma_programa",
        "matricula_turma_programa_historico",
        "aluno_pap_ano_letivo",
        "aluno_pap_ano_letivo_historico",
    ),
}


def validar_parametros_dominio(
    dominio: str,
    ano_letivo: int | None = None,
    fases: list[str] | None = None,
    anos_letivos: list[int] | None = None,
) -> str | None:
    """Valida os parâmetros de execução para o domínio informado.

    Args:
        dominio: Nome do domínio ETL a executar.
        ano_letivo: Parâmetro legado, não aceito pelo contrato atual.
        fases: Fases a executar; aceito pelos domínios alunos e pedagógico.
        anos_letivos: Lista de anos letivos; aceita pelos domínios compatíveis.

    Returns:
        Mensagem de erro se algum parâmetro for inválido, ``None`` se tudo ok.
    """
    if dominio not in DOMINIOS_VALIDOS:
        return f"Domínio inválido. Use: {', '.join(DOMINIOS_VALIDOS)}"

    if ano_letivo is not None:
        return "Use o parâmetro 'anos_letivos' em vez de 'ano_letivo'."

    if anos_letivos and dominio not in DOMINIOS_COM_ANOS_LETIVOS:
        return f"O domínio '{dominio}' não aceita o parâmetro anos_letivos."

    if fases and dominio not in DOMINIOS_COM_FASES:
        return f"O domínio '{dominio}' não aceita o parâmetro fases."

    return None
