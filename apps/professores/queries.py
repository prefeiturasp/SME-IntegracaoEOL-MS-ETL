"""Constantes SQL do domínio Professores (EOL/SQL Server).

Todas as queries que leem dados do EOL para o domínio professores
residem neste módulo. Os JOINs estruturais com tabelas de suporte
(serie_turma_grade, turma_escola_grade_programa) ocorrem aqui, no
nível do SQL Server, evitando replicação dessas tabelas no PostgreSQL.

Cargos de professor reconhecidos pelo EOL:
    3239, 3247, 3255, 3263, 3271, 3280, 3298, 3301,
    3310, 3336, 3344, 3840, 3859, 3867, 3874, 3875,
    3883, 3884
"""

CARGOS_PROFESSOR = (
    3239,
    3247,
    3255,
    3263,
    3271,
    3280,
    3298,
    3301,
    3310,
    3336,
    3344,
    3840,
    3859,
    3867,
    3874,
    3875,
    3883,
    3884,
)

_PLACEHOLDERS_CARGO = ",".join(["%s"] * len(CARGOS_PROFESSOR))

SQL_PROFESSORES = f"""
    SELECT DISTINCT
        sc.cd_registro_funcional,
        sc.nm_pessoa,
        sc.nm_social,
        sc.cd_cpf_pessoa
    FROM v_servidor_cotic sc
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_servidor = sc.cd_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
      AND sc.cd_registro_funcional IS NOT NULL
"""

SQL_CARGOS_BASE = f"""
    SELECT
        cbs.cd_cargo_base_servidor,
        sc.cd_registro_funcional,
        cbs.cd_cargo,
        LTRIM(RTRIM(c.dc_cargo)) AS dc_cargo,
        cbs.cd_situacao_funcional,
        cbs.dt_posse,
        cbs.dt_fim_nomeacao,
        cbs.dt_cancelamento
    FROM v_cargo_base_cotic cbs
    INNER JOIN v_servidor_cotic sc
        ON sc.cd_servidor = cbs.cd_servidor
    INNER JOIN cargo c
        ON c.cd_cargo = cbs.cd_cargo
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_LOTACOES = """
    SELECT
        ls.cd_cargo_base_servidor,
        ls.cd_unidade_educacao,
        ls.dt_inicio,
        ls.dt_fim
    FROM lotacao_servidor ls
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = ls.cd_cargo_base_servidor
"""

SQL_CARGOS_SOBREPOSTOS = f"""
    SELECT
        css.cd_cargo_base_servidor,
        css.cd_cargo,
        css.cd_unidade_local_servico,
        css.dt_fim_cargo_sobreposto
    FROM cargo_sobreposto_servidor css
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = css.cd_cargo_base_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_FUNCOES_ATIVIDADE = f"""
    SELECT
        facs.cd_cargo_base_servidor,
        facs.cd_unidade_local_servico,
        facs.dt_fim_funcao_atividade
    FROM funcao_atividade_cargo_servidor facs
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = facs.cd_cargo_base_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_LAUDOS = f"""
    SELECT lm.cd_cargo_base_servidor
    FROM laudo_medico lm
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = lm.cd_cargo_base_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_PESSOAS = """
    SELECT
        cd_pessoa,
        cd_cpf_pessoa,
        nm_pessoa,
        nm_social
    FROM pessoa
    WHERE cd_pessoa IN (
        SELECT DISTINCT cd_pessoa
        FROM contrato_externo
        WHERE dt_cancelamento IS NULL
    )
"""

SQL_CONTRATOS_EXTERNOS = """
    SELECT
        cd_contrato_externo,
        cd_pessoa,
        cd_tipo_funcao_funcionario_externo,
        cd_unidade_educacao,
        dt_cancelamento,
        cd_motivo_desligamento_externo
    FROM contrato_externo
"""

SQL_ATRIBUICOES_AULA = f"""
    SELECT
        aa.cd_atribuicao_aula,
        aa.cd_cargo_base_servidor,
        aa.cd_unidade_educacao,
        COALESCE(stg.cd_turma_escola, tegp.cd_turma_escola) AS cd_turma_escola,
        aa.cd_turma_escola_grade_programa,
        aa.cd_grade,
        aa.cd_componente_curricular,
        aa.cd_serie_grade,
        aa.an_atribuicao,
        aa.dt_atribuicao_aula,
        COALESCE(aa.dt_disponibilizacao_aulas, te.dt_fim_turma) AS dt_disponibilizacao_aulas,
        aa.cd_motivo_disponibilizacao,
        aa.dt_cancelamento
    FROM atribuicao_aula aa
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
    LEFT JOIN serie_turma_grade stg
        ON stg.cd_serie_grade = aa.cd_serie_grade
    LEFT JOIN turma_escola_grade_programa tegp
        ON tegp.cd_turma_escola_grade_programa
            = aa.cd_turma_escola_grade_programa
    LEFT JOIN turma_escola te 
        ON te.cd_turma_escola = tegp.cd_turma_escola            
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_ATRIBUICOES_EXTERNO = """
    SELECT
        ae.cd_atribuicao_externo,
        ae.cd_contrato_externo,
        ae.cd_unidade_educacao,
        COALESCE(stg.cd_turma_escola, tegp.cd_turma_escola) AS cd_turma_escola,
        ae.cd_grade,
        ae.cd_componente_curricular,
        ae.cd_serie_grade,
        ae.cd_turma_escola_grade_programa,
        ae.an_atribuicao,
        ae.dt_atribuicao,
        COALESCE(ae.dt_disponibilizacao, te.dt_fim_turma) AS dt_disponibilizacao,
        ae.cd_motivo_disponibilizacao_externo,
        ae.dt_cancelamento
    FROM atribuicao_externo ae
    INNER JOIN contrato_externo ce
        ON ce.cd_contrato_externo = ae.cd_contrato_externo
    LEFT JOIN serie_turma_grade stg
        ON stg.cd_serie_grade = ae.cd_serie_grade
    LEFT JOIN turma_escola_grade_programa tegp
        ON tegp.cd_turma_escola_grade_programa
            = ae.cd_turma_escola_grade_programa
    LEFT JOIN turma_escola te 
        ON te.cd_turma_escola = tegp.cd_turma_escola            
    WHERE ce.dt_cancelamento IS NULL
"""
