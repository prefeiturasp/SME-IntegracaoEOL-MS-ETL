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
_VALUES_CARGO = ",".join(["(%s)"] * len(CARGOS_PROFESSOR))

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
        COALESCE(
            aa.dt_disponibilizacao_aulas,
            te.dt_fim_turma
        ) AS dt_disponibilizacao_aulas,
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
        COALESCE(
            ae.dt_disponibilizacao,
            te.dt_fim_turma
        ) AS dt_disponibilizacao,
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

SQL_FUNCIONARIOS_UNIDADE_EDUCACIONAL = f"""
    ;WITH cargos_professor AS (
        SELECT v.codigo_cargo
        FROM (VALUES {_VALUES_CARGO}) AS v(codigo_cargo)
    )

    SELECT
        sc.nm_pessoa AS nome_servidor,
        sc.nm_social AS nome_social,
        sc.cd_cpf_pessoa AS cpf,
        sc.cd_registro_funcional AS codigo_rf,
        ls.cd_unidade_educacao AS codigo_ue,
        ls.dt_inicio AS data_inicio,
        ls.dt_fim AS data_fim,
        cbs.cd_cargo AS cd_cargo,
        LTRIM(RTRIM(c.dc_cargo)) AS cargo,
        0 AS cd_tipo_funcao_atividade,
        1 AS eh_professor,
        CASE
            WHEN lm.cd_cargo_base_servidor IS NULL THEN 0
            ELSE 1
        END AS esta_afastado,
        0 AS funcao_externo,
        0 AS tipo_funcao_externo

    FROM lotacao_servidor ls

    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = ls.cd_cargo_base_servidor

    INNER JOIN v_servidor_cotic sc
        ON sc.cd_servidor = cbs.cd_servidor

    INNER JOIN cargo c
        ON c.cd_cargo = cbs.cd_cargo

    LEFT JOIN laudo_medico lm
        ON lm.cd_cargo_base_servidor = cbs.cd_cargo_base_servidor
        AND lm.cd_tipo_laudo IN ('T', 'D')
        AND lm.dt_publicacao_doc_cessacao_laudo IS NULL

    WHERE cbs.cd_cargo IN (SELECT codigo_cargo FROM cargos_professor)
    AND sc.cd_registro_funcional IS NOT NULL

    UNION

    SELECT
        sc.nm_pessoa AS nome_servidor,
        sc.nm_social AS nome_social,
        sc.cd_cpf_pessoa AS cpf,
        sc.cd_registro_funcional AS codigo_rf,
        css.cd_unidade_local_servico AS codigo_ue,
        cbs.dt_posse AS data_inicio,
        css.dt_fim_cargo_sobreposto AS data_fim,
        css.cd_cargo AS cd_cargo,
        LTRIM(RTRIM(c.dc_cargo)) AS cargo,
        0 AS cd_tipo_funcao_atividade,
        CASE
            WHEN css.cd_cargo IN (SELECT codigo_cargo FROM cargos_professor)
            THEN 1
            ELSE 0
        END AS eh_professor,
        CASE
            WHEN lm.cd_cargo_base_servidor IS NULL THEN 0
            ELSE 1
        END AS esta_afastado,
        0 AS funcao_externo,
        0 AS tipo_funcao_externo

    FROM cargo_sobreposto_servidor css

    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = css.cd_cargo_base_servidor

    INNER JOIN v_servidor_cotic sc
        ON sc.cd_servidor = cbs.cd_servidor

    LEFT JOIN cargo c
        ON c.cd_cargo = css.cd_cargo

    LEFT JOIN laudo_medico lm
        ON lm.cd_cargo_base_servidor = cbs.cd_cargo_base_servidor
        AND lm.cd_tipo_laudo IN ('T', 'D')
        AND lm.dt_publicacao_doc_cessacao_laudo IS NULL

    WHERE cbs.cd_cargo IN (SELECT codigo_cargo FROM cargos_professor)

    UNION

    SELECT
        sc.nm_pessoa AS nome_servidor,
        sc.nm_social AS nome_social,
        sc.cd_cpf_pessoa AS cpf,
        sc.cd_registro_funcional AS codigo_rf,
        facs.cd_unidade_local_servico AS codigo_ue,
        cbs.dt_posse AS data_inicio,
        facs.dt_fim_funcao_atividade AS data_fim,
        cbs.cd_cargo AS cd_cargo,
        LTRIM(RTRIM(c.dc_cargo)) AS cargo,
        COALESCE(facs.cd_tipo_funcao, 0) AS cd_tipo_funcao_atividade,
        1 AS eh_professor,
        CASE
            WHEN lm.cd_cargo_base_servidor IS NULL THEN 0
            ELSE 1
        END AS esta_afastado,
        0 AS funcao_externo,
        0 AS tipo_funcao_externo

    FROM funcao_atividade_cargo_servidor facs

    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = facs.cd_cargo_base_servidor

    INNER JOIN v_servidor_cotic sc
        ON sc.cd_servidor = cbs.cd_servidor

    INNER JOIN cargo c
        ON c.cd_cargo = cbs.cd_cargo

    LEFT JOIN laudo_medico lm
        ON lm.cd_cargo_base_servidor = cbs.cd_cargo_base_servidor
        AND lm.cd_tipo_laudo IN ('T', 'D')
        AND lm.dt_publicacao_doc_cessacao_laudo IS NULL

    WHERE cbs.cd_cargo IN (SELECT codigo_cargo FROM cargos_professor)

    UNION

    SELECT
        p.nm_pessoa AS nome_servidor,
        p.nm_social AS nome_social,
        p.cd_cpf_pessoa AS cpf,
        p.cd_cpf_pessoa AS codigo_rf,
        ce.cd_unidade_educacao AS codigo_ue,
        ce.dt_inicio AS data_inicio,
        ce.dt_cancelamento AS data_fim,
        NULL AS cd_cargo,
        NULL AS cargo,
        0 AS cd_tipo_funcao_atividade,
        0 AS eh_professor,
        0 AS esta_afastado,
        COALESCE(ce.cd_tipo_funcao_funcionario_externo, 0) AS funcao_externo,
        COALESCE(ce.cd_tipo_funcao_funcionario_externo, 0) AS tipo_funcao_externo

    FROM contrato_externo ce

    INNER JOIN pessoa p
        ON p.cd_pessoa = ce.cd_pessoa

    WHERE ce.dt_cancelamento IS NULL
"""
