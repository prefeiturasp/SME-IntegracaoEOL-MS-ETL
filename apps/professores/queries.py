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

SQL_FUNCIONARIOS_CARGOS = """
    SELECT DISTINCT
        sc.nm_pessoa,
        sc.cd_registro_funcional,
        cbs.dt_posse,
        cbs.dt_fim_nomeacao,
        LTRIM(RTRIM(c.dc_cargo)) AS dc_cargo,
        cbs.cd_cargo
    FROM v_servidor_cotic sc
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_servidor = sc.cd_servidor
    INNER JOIN cargo c
        ON c.cd_cargo = cbs.cd_cargo
    WHERE sc.cd_registro_funcional IS NOT NULL
"""

SQL_LOTACOES = """
    SELECT
        ls.cd_cargo_base_servidor,
        ls.cd_unidade_educacao,
        ue.cd_unidade_administrativa_referencia AS codigo_dre,
        ls.dt_inicio,
        ls.dt_fim
    FROM lotacao_servidor ls
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = ls.cd_cargo_base_servidor
    LEFT JOIN v_cadastro_unidade_educacao ue
        ON ue.cd_unidade_educacao = ls.cd_unidade_educacao
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
        nm_social,
        nm_pai_pessoa,
        nm_mae_pessoa,
        dt_nascimento_pessoa,
        nr_rg_pessoa,
        nr_titulo_eleitor_pessoa,
        cd_pis_pasep
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

SQL_TURMAS_ATRIBUIDAS_UE = """
    SELECT
        CodEscola,
        CodTurma,
        AnoLetivo,
        Modalidade,
        Semestre,
        CodModalidade,
        CodDre,
        Dre,
        DreAbrev,
        UE,
        UEAbrev,
        NomeTurma,
        Ano,
        TipoUE,
        CodTipoUE,
        CodTipoEscola,
        TipoEscola,
        DuracaoTurno,
        TipoTurno,
        usuario_rf,
        cargo,
        cargo_sobreposto
    FROM turmas_atribuidas_ue WITH (NOLOCK)
    WHERE 1 = 1
      /*FILTRO_ANO_LETIVO_TURMAS_ATRIBUIDAS_UE*/
"""

SQL_DISCIPLINAS_TURMAS_ATRIBUIDAS_UE = """
    SELECT DISTINCT
        tau.CodEscola AS codigo_escola,
        tau.CodTurma AS codigo_turma,
        tau.AnoLetivo AS ano_letivo,
        tau.usuario_rf,
        componente_curricular.cd_componente_curricular
            AS codigo_componente_curricular,
        componente_curricular.dc_componente_curricular
            AS descricao_componente_curricular,
        CAST(NULL AS int) AS codigo_componente_curricular_pai,
        CAST(0 AS bit) AS regencia,
        CAST(NULL AS int) AS codigo_componente_territorio_saber,
        CAST(0 AS bit) AS territorio_saber,
        tau.CodDre AS codigo_dre,
        tau.CodTipoEscola AS codigo_tipo_escola,
        tau.TipoEscola AS tipo_escola,
        tau.cargo,
        tau.cargo_sobreposto
    FROM turmas_atribuidas_ue tau WITH (NOLOCK)
    INNER JOIN turma_escola
        ON turma_escola.cd_turma_escola = tau.CodTurma
    INNER JOIN escola esc
        ON turma_escola.cd_escola = esc.cd_escola
    INNER JOIN serie_turma_escola
        ON serie_turma_escola.cd_turma_escola =
            turma_escola.cd_turma_escola
    INNER JOIN serie_turma_grade
        ON serie_turma_grade.cd_turma_escola =
            serie_turma_escola.cd_turma_escola
    INNER JOIN escola_grade
        ON serie_turma_grade.cd_escola_grade =
            escola_grade.cd_escola_grade
    INNER JOIN grade
        ON escola_grade.cd_grade = grade.cd_grade
    INNER JOIN serie_ensino
        ON grade.cd_serie_ensino = serie_ensino.cd_serie_ensino
    INNER JOIN etapa_ensino
        ON serie_ensino.cd_etapa_ensino =
            etapa_ensino.cd_etapa_ensino
    INNER JOIN atribuicao_aula
        ON grade.cd_grade = atribuicao_aula.cd_grade
        AND atribuicao_aula.an_atribuicao = turma_escola.an_letivo
        AND atribuicao_aula.cd_serie_grade =
            serie_turma_grade.cd_serie_grade
        AND atribuicao_aula.cd_grade = grade.cd_grade
    INNER JOIN componente_curricular
        ON atribuicao_aula.cd_componente_curricular =
            componente_curricular.cd_componente_curricular
    WHERE atribuicao_aula.dt_cancelamento IS NULL
      AND componente_curricular.dt_cancelamento IS NULL
      AND esc.tp_escola IN (1, 3, 4, 16)
      AND etapa_ensino.cd_etapa_ensino IN (
          2, 3, 7, 11, 4, 5, 12, 13, 6, 7, 8, 9, 17, 14
      )
      AND turma_escola.st_turma_escola IN ('A', 'O', 'C')
      /*FILTRO_ANO_LETIVO_DISCIPLINAS_TURMAS_ATRIBUIDAS_UE*/

    UNION

    SELECT DISTINCT
        tau.CodEscola AS codigo_escola,
        tau.CodTurma AS codigo_turma,
        tau.AnoLetivo AS ano_letivo,
        tau.usuario_rf,
        componente_curricular.cd_componente_curricular
            AS codigo_componente_curricular,
        componente_curricular.dc_componente_curricular
            AS descricao_componente_curricular,
        CAST(NULL AS int) AS codigo_componente_curricular_pai,
        CAST(0 AS bit) AS regencia,
        CAST(NULL AS int) AS codigo_componente_territorio_saber,
        CAST(0 AS bit) AS territorio_saber,
        tau.CodDre AS codigo_dre,
        tau.CodTipoEscola AS codigo_tipo_escola,
        tau.TipoEscola AS tipo_escola,
        tau.cargo,
        tau.cargo_sobreposto
    FROM turmas_atribuidas_ue tau WITH (NOLOCK)
    INNER JOIN turma_escola
        ON turma_escola.cd_turma_escola = tau.CodTurma
    INNER JOIN turma_escola_grade_programa
        ON turma_escola_grade_programa.cd_turma_escola =
            turma_escola.cd_turma_escola
    INNER JOIN escola esc
        ON turma_escola.cd_escola = esc.cd_escola
    INNER JOIN escola_grade
        ON escola_grade.cd_escola = esc.cd_escola
        AND turma_escola_grade_programa.cd_escola_grade =
            escola_grade.cd_escola_grade
    INNER JOIN grade
        ON grade.cd_grade = escola_grade.cd_grade
    INNER JOIN grade_componente_curricular
        ON grade.cd_grade = grade_componente_curricular.cd_grade
    INNER JOIN componente_curricular
        ON grade_componente_curricular.cd_componente_curricular =
            componente_curricular.cd_componente_curricular
    WHERE esc.tp_escola IN (1, 3, 4, 16)
      AND turma_escola.st_turma_escola IN ('O', 'A', 'C')
      AND turma_escola.cd_tipo_turma IN (2, 3, 5)
      /*FILTRO_ANO_LETIVO_DISCIPLINAS_TURMAS_ATRIBUIDAS_UE*/
"""

SQL_ATRIBUICOES_AULA = f"""
    SELECT
        aa.cd_atribuicao_aula,
        aa.cd_cargo_base_servidor,
        aa.cd_unidade_educacao,
        COALESCE(stg.cd_turma_escola, tegp.cd_turma_escola) AS cd_turma_escola,
        te.dc_turma_escola,
        aa.cd_turma_escola_grade_programa,
        aa.cd_grade,
        aa.cd_componente_curricular,
        cc.dc_componente_curricular,
        aa.cd_serie_grade,
        se.sg_resumida_serie as ano_escolar,
        aa.an_atribuicao,
        se.cd_etapa_ensino,
        aa.dt_atribuicao_aula,
        te.dt_inicio_turma,
        te.dt_fim_turma,
        COALESCE(
            aa.dt_disponibilizacao_aulas,
            te.dt_fim_turma
        ) AS dt_disponibilizacao_aulas,
        aa.cd_motivo_disponibilizacao,
        aa.dt_cancelamento,
        dre.cd_unidade_educacao AS codigo_dre,
        dre.nm_unidade_educacao AS nome_dre,
        dre.nm_exibicao_unidade AS abreviacao_dre,
        ue.nm_unidade_educacao AS nome_unidade_educacional,
        esc.tp_escola AS codigo_tipo_escola,
        te.cd_tipo_turma AS codigo_tipo_turma,
        CASE
            WHEN te.cd_tipo_turma IN (2, 3, 4, 5) THEN 'Fundamental'
            WHEN etapa.cd_etapa_ensino IN (2, 3, 7, 11) THEN 'EJA'
            WHEN etapa.cd_etapa_ensino IN (4, 5, 12, 13)
                THEN 'Fundamental'
            WHEN etapa.cd_etapa_ensino IN (6, 7, 8, 9, 14, 17)
                THEN 'Médio'
        END AS modalidade,
        CASE
            WHEN te.cd_tipo_turma IN (2, 3, 4, 5) THEN 5
            WHEN etapa.cd_etapa_ensino IN (2, 3, 7, 11) THEN 3
            WHEN etapa.cd_etapa_ensino IN (4, 5, 12, 13) THEN 5
            WHEN etapa.cd_etapa_ensino IN (6, 7, 8, 9, 14, 17) THEN 6
        END AS codigo_modalidade,
        CASE
            WHEN etapa.cd_etapa_ensino IN (2, 3, 7, 11)
            THEN CASE
                WHEN DATEPART(MONTH, te.dt_inicio_turma) > 6 THEN 2
                ELSE 1
            END
            ELSE 0
        END AS semestre,
        dtt.qt_hora_duracao AS duracao_turno,
        tt.cd_tipo_turno AS tipo_turno
    FROM atribuicao_aula aa
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
    LEFT JOIN serie_turma_grade stg
        ON stg.cd_serie_grade = aa.cd_serie_grade
    LEFT JOIN turma_escola_grade_programa tegp
        ON tegp.cd_turma_escola_grade_programa
            = aa.cd_turma_escola_grade_programa
    LEFT JOIN turma_escola te
        ON te.cd_turma_escola = COALESCE(stg.cd_turma_escola,
        tegp.cd_turma_escola)
    LEFT JOIN componente_curricular cc
        ON cc.cd_componente_curricular = aa.cd_componente_curricular
    LEFT JOIN serie_ensino se
        ON se.cd_serie_ensino = stg.cd_serie_ensino
    LEFT JOIN etapa_ensino etapa
        ON etapa.cd_etapa_ensino = se.cd_etapa_ensino
    LEFT JOIN v_cadastro_unidade_educacao ue
        ON ue.cd_unidade_educacao = te.cd_escola
    LEFT JOIN v_cadastro_unidade_educacao dre
        ON dre.cd_unidade_educacao = ue.cd_unidade_administrativa_referencia
    LEFT JOIN escola esc
        ON esc.cd_escola = te.cd_escola
    LEFT JOIN tipo_turno tt
        ON tt.cd_tipo_turno = te.cd_tipo_turno
    LEFT JOIN duracao_tipo_turno dtt
        ON dtt.cd_tipo_turno = tt.cd_tipo_turno
       AND dtt.cd_duracao = te.cd_duracao
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
      /*FILTRO_ANO_LETIVO_ATRIBUICAO_AULA*/
"""

SQL_ATRIBUICOES_EXTERNO = """
    SELECT
        ae.cd_atribuicao_externo,
        ae.cd_contrato_externo,
        ae.cd_unidade_educacao,
        COALESCE(stg.cd_turma_escola, tegp.cd_turma_escola) AS cd_turma_escola,
        te.dc_turma_escola,
        ae.cd_grade,
        ae.cd_componente_curricular,
        cc.dc_componente_curricular,
        ae.cd_serie_grade,
        ae.cd_turma_escola_grade_programa,
        se.sg_resumida_serie as ano_escolar,
        ae.an_atribuicao,
        se.cd_etapa_ensino,
        ae.dt_atribuicao,
        te.dt_inicio_turma,
        te.dt_fim_turma,
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
        ON te.cd_turma_escola = COALESCE(stg.cd_turma_escola,
        tegp.cd_turma_escola)
    LEFT JOIN componente_curricular cc
        ON cc.cd_componente_curricular = ae.cd_componente_curricular
	LEFT JOIN serie_ensino se
		ON se.cd_serie_ensino = stg.cd_serie_ensino
    WHERE ce.dt_cancelamento IS NULL
      /*FILTRO_ANO_LETIVO_ATRIBUICAO_EXTERNO*/
"""

SQL_FUNCIONARIOS_UNIDADE_EDUCACIONAL = f"""
    ;WITH cargos_professor AS (
        SELECT v.codigo_cargo
        FROM (VALUES {_VALUES_CARGO}) AS v(codigo_cargo)
    ),
    laudo_ativo AS (
        SELECT
            cd_cargo_base_servidor,
            cd_tipo_laudo,
            dt_publicacao_doc_cessacao_laudo,
            ROW_NUMBER() OVER (
                PARTITION BY cd_cargo_base_servidor
                ORDER BY cd_laudo_medico DESC
            ) AS ordem
        FROM laudo_medico WITH (NOLOCK)
        WHERE dt_publicacao_doc_cessacao_laudo IS NULL
    )
    SELECT
        funcionarios.nome,
        funcionarios.nome_social,
        funcionarios.cpf,
        funcionarios.codigo_rf,
        funcionarios.codigo_ue,
        funcionarios.codigo_dre,
        funcionarios.data_inicio,
        funcionarios.data_fim,
        funcionarios.dt_fim_nomeacao,
        funcionarios.dt_fim_funcao_atividade,
        funcionarios.origem_vinculo,
        funcionarios.cd_cargo,
        funcionarios.cargo,
        funcionarios.cd_tipo_funcao_atividade,
        CASE
            WHEN funcionarios.cd_cargo IN (
                SELECT codigo_cargo FROM cargos_professor
            )
            THEN 1
            ELSE 0
        END AS eh_professor,
        CASE
            WHEN laudo.cd_tipo_laudo IN ('T', 'D')
                AND (
                    laudo.dt_publicacao_doc_cessacao_laudo IS NULL
                    OR laudo.dt_publicacao_doc_cessacao_laudo < GETDATE()
                )
            THEN 1
            ELSE 0
        END AS esta_afastado,
        funcionarios.funcao_externo,
        funcionarios.tipo_funcao_externo,
        funcionarios.pessoa_id,
        funcionarios.nome_ue,
        funcionarios.tipo_funcionario_externo,
        funcionarios.dc_funcao_externo,
        funcionarios.supervisor_dre
    FROM (
        SELECT DISTINCT
            servidor.nm_pessoa AS nome,
            servidor.nm_social AS nome_social,
            servidor.cd_cpf_pessoa AS cpf,
            servidor.cd_registro_funcional AS codigo_rf,
            ue.cd_unidade_educacao AS codigo_ue,
            ue.cd_unidade_administrativa_referencia AS codigo_dre,
            cargoServidor.dt_posse AS data_inicio,
            cargoServidor.dt_fim_nomeacao AS data_fim,
            cargoServidor.dt_fim_nomeacao AS dt_fim_nomeacao,
            funcao.dt_fim_funcao_atividade AS dt_fim_funcao_atividade,
            'lotacao' AS origem_vinculo,
            CASE
                WHEN cargoSobreposto.dc_cargo IS NOT NULL
                THEN cargoSobreposto.dc_cargo
                ELSE cargo.dc_cargo
            END AS cargo,
            CASE
                WHEN cargoSobreposto.cd_cargo IS NOT NULL
                THEN cargoSobreposto.cd_cargo
                ELSE cargo.cd_cargo
            END AS cd_cargo,
            funcao.cd_tipo_funcao AS cd_tipo_funcao_atividade,
            cargoServidor.cd_cargo_base_servidor,
            0 AS funcao_externo,
            0 AS tipo_funcao_externo,
            p.cd_pessoa AS pessoa_id,
            ue.nm_unidade_educacao AS nome_ue,
            NULL AS tipo_funcionario_externo,
            NULL AS dc_funcao_externo,
            CASE
                WHEN cargo.cd_cargo = 3352
                    AND cargoServidor.dt_fim_nomeacao IS NULL
                    AND lotacao_servidor.dt_fim IS NULL
                THEN 1
                ELSE 0
            END AS supervisor_dre
        FROM v_servidor_cotic servidor
        INNER JOIN v_cargo_base_cotic AS cargoServidor
            ON cargoServidor.cd_servidor = servidor.cd_servidor
        INNER JOIN cargo AS cargo
            ON cargoServidor.cd_cargo = cargo.cd_cargo
        LEFT JOIN lotacao_servidor AS lotacao_servidor
            ON cargoServidor.cd_cargo_base_servidor
                = lotacao_servidor.cd_cargo_base_servidor
        LEFT JOIN funcao_atividade_cargo_servidor funcao
            ON cargoServidor.cd_cargo_base_servidor
                = funcao.cd_cargo_base_servidor
            AND funcao.dt_fim_funcao_atividade IS NULL
        INNER JOIN v_cadastro_unidade_educacao ue
            ON lotacao_servidor.cd_unidade_educacao
                = ue.cd_unidade_educacao
        LEFT JOIN (
            SELECT
                cargoSobreposto.cd_cargo,
                cargoSobreposto.dc_cargo,
                cargo_sobreposto_servidor.cd_cargo_base_servidor,
                cargo_sobreposto_servidor.cd_unidade_local_servico
            FROM cargo_sobreposto_servidor AS cargo_sobreposto_servidor
            INNER JOIN cargo AS cargoSobreposto
                ON cargo_sobreposto_servidor.cd_cargo
                    = cargoSobreposto.cd_cargo
            INNER JOIN lotacao_servidor AS lotacao_servidor_sobreposto
                ON cargo_sobreposto_servidor.cd_cargo_base_servidor
                    = lotacao_servidor_sobreposto.cd_cargo_base_servidor
            WHERE cargo_sobreposto_servidor.dt_fim_cargo_sobreposto IS NULL
                OR cargo_sobreposto_servidor.dt_fim_cargo_sobreposto
                    > GETDATE()
        ) cargoSobreposto
            ON cargoSobreposto.cd_cargo_base_servidor
                = cargoServidor.cd_cargo_base_servidor
            AND cargoSobreposto.cd_unidade_local_servico
                = ue.cd_unidade_educacao
        LEFT JOIN pessoa p
            ON servidor.cd_cpf_pessoa = p.cd_cpf_pessoa
        WHERE lotacao_servidor.dt_fim IS NULL

        UNION

        SELECT DISTINCT
            servidor.nm_pessoa AS nome,
            servidor.nm_social AS nome_social,
            servidor.cd_cpf_pessoa AS cpf,
            servidor.cd_registro_funcional AS codigo_rf,
            ue.cd_unidade_educacao AS codigo_ue,
            ue.cd_unidade_administrativa_referencia AS codigo_dre,
            cargoServidor.dt_posse AS data_inicio,
            cargoServidor.dt_fim_nomeacao AS data_fim,
            cargoServidor.dt_fim_nomeacao AS dt_fim_nomeacao,
            funcao.dt_fim_funcao_atividade AS dt_fim_funcao_atividade,
            'cargo_sobreposto' AS origem_vinculo,
            RTRIM(LTRIM(cargo.dc_cargo)) AS cargo,
            cargo.cd_cargo,
            funcao.cd_tipo_funcao AS cd_tipo_funcao_atividade,
            cargoServidor.cd_cargo_base_servidor,
            0 AS funcao_externo,
            0 AS tipo_funcao_externo,
            p.cd_pessoa AS pessoa_id,
            ue.nm_unidade_educacao AS nome_ue,
            NULL AS tipo_funcionario_externo,
            NULL AS dc_funcao_externo,
            CASE
                WHEN cargo_sobreposto_servidor.cd_cargo = 3352
                    AND cargoServidor.dt_fim_nomeacao IS NULL
                    AND lotacao_servidor.dt_fim IS NULL
                THEN 1
                ELSE 0
            END AS supervisor_dre
        FROM v_servidor_cotic servidor
        INNER JOIN v_cargo_base_cotic AS cargoServidor
            ON cargoServidor.cd_servidor = servidor.cd_servidor
        LEFT JOIN lotacao_servidor AS lotacao_servidor
            ON cargoServidor.cd_cargo_base_servidor
                = lotacao_servidor.cd_cargo_base_servidor
        LEFT JOIN funcao_atividade_cargo_servidor funcao
            ON cargoServidor.cd_cargo_base_servidor
                = funcao.cd_cargo_base_servidor
            AND funcao.dt_fim_funcao_atividade IS NULL
        INNER JOIN cargo_sobreposto_servidor AS cargo_sobreposto_servidor
            ON cargo_sobreposto_servidor.cd_cargo_base_servidor
                = cargoServidor.cd_cargo_base_servidor
            AND (
                cargo_sobreposto_servidor.dt_fim_cargo_sobreposto IS NULL
                OR cargo_sobreposto_servidor.dt_fim_cargo_sobreposto
                    > GETDATE()
            )
        INNER JOIN cargo AS cargo
            ON cargo_sobreposto_servidor.cd_cargo = cargo.cd_cargo
        INNER JOIN v_cadastro_unidade_educacao ue
            ON cargo_sobreposto_servidor.cd_unidade_local_servico
                = ue.cd_unidade_educacao
        LEFT JOIN pessoa p
            ON servidor.cd_cpf_pessoa = p.cd_cpf_pessoa
        WHERE lotacao_servidor.dt_fim IS NULL

        UNION

        SELECT DISTINCT
            servidor.nm_pessoa AS nome,
            servidor.nm_social AS nome_social,
            servidor.cd_cpf_pessoa AS cpf,
            servidor.cd_registro_funcional AS codigo_rf,
            ue.cd_unidade_educacao AS codigo_ue,
            ue.cd_unidade_administrativa_referencia AS codigo_dre,
            cargoServidor.dt_posse AS data_inicio,
            cargoServidor.dt_fim_nomeacao AS data_fim,
            cargoServidor.dt_fim_nomeacao AS dt_fim_nomeacao,
            funcao.dt_fim_funcao_atividade AS dt_fim_funcao_atividade,
            'atribuicao_aula' AS origem_vinculo,
            RTRIM(LTRIM(cargo.dc_cargo)) AS cargo,
            cargo.cd_cargo,
            funcao.cd_tipo_funcao AS cd_tipo_funcao_atividade,
            cargoServidor.cd_cargo_base_servidor,
            0 AS funcao_externo,
            0 AS tipo_funcao_externo,
            p.cd_pessoa AS pessoa_id,
            ue.nm_unidade_educacao AS nome_ue,
            NULL AS tipo_funcionario_externo,
            NULL AS dc_funcao_externo,
            0 AS supervisor_dre
        FROM v_servidor_cotic servidor
        INNER JOIN v_cargo_base_cotic AS cargoServidor
            ON cargoServidor.cd_servidor = servidor.cd_servidor
        INNER JOIN cargo AS cargo
            ON cargoServidor.cd_cargo = cargo.cd_cargo
        LEFT JOIN funcao_atividade_cargo_servidor funcao
            ON cargoServidor.cd_cargo_base_servidor
                = funcao.cd_cargo_base_servidor
            AND funcao.dt_fim_funcao_atividade IS NULL
        INNER JOIN atribuicao_aula atribuicao
            ON atribuicao.cd_cargo_base_servidor
                = cargoServidor.cd_cargo_base_servidor
        INNER JOIN v_cadastro_unidade_educacao ue
            ON atribuicao.cd_unidade_educacao = ue.cd_unidade_educacao
        LEFT JOIN pessoa p
            ON servidor.cd_cpf_pessoa = p.cd_cpf_pessoa
        WHERE atribuicao.dt_cancelamento IS NULL
            AND cargoServidor.dt_fim_nomeacao IS NULL
            AND atribuicao.dt_disponibilizacao_aulas IS NULL
            AND YEAR(dt_atribuicao_aula) = YEAR(GETDATE())

        UNION

        SELECT DISTINCT
            servidor.nm_pessoa AS nome,
            servidor.nm_social AS nome_social,
            servidor.cd_cpf_pessoa AS cpf,
            servidor.cd_registro_funcional AS codigo_rf,
            ue.cd_unidade_educacao AS codigo_ue,
            ue.cd_unidade_administrativa_referencia AS codigo_dre,
            cargoServidor.dt_posse AS data_inicio,
            cargoServidor.dt_fim_nomeacao AS data_fim,
            cargoServidor.dt_fim_nomeacao AS dt_fim_nomeacao,
            atividade.dt_fim_funcao_atividade AS dt_fim_funcao_atividade,
            'funcao_atividade' AS origem_vinculo,
            RTRIM(LTRIM(cargo.dc_cargo)) AS cargo,
            cargo.cd_cargo,
            atividade.cd_tipo_funcao AS cd_tipo_funcao_atividade,
            cargoServidor.cd_cargo_base_servidor,
            0 AS funcao_externo,
            0 AS tipo_funcao_externo,
            p.cd_pessoa AS pessoa_id,
            ue.nm_unidade_educacao AS nome_ue,
            NULL AS tipo_funcionario_externo,
            NULL AS dc_funcao_externo,
            0 AS supervisor_dre
        FROM v_servidor_cotic servidor
        INNER JOIN v_cargo_base_cotic AS cargoServidor
            ON cargoServidor.cd_servidor = servidor.cd_servidor
        INNER JOIN cargo AS cargo
            ON cargoServidor.cd_cargo = cargo.cd_cargo
        INNER JOIN funcao_atividade_cargo_servidor atividade
            ON atividade.cd_cargo_base_servidor
                = cargoServidor.cd_cargo_base_servidor
            AND (
                atividade.dt_fim_funcao_atividade IS NULL
                OR atividade.dt_fim_funcao_atividade > GETDATE()
            )
        INNER JOIN v_cadastro_unidade_educacao ue
            ON ue.cd_unidade_educacao =
                CASE ue.tp_unidade_educacao
                    WHEN 3
                    THEN CONCAT(
                        SUBSTRING(atividade.cd_unidade_local_servico, 1, 5),
                        '0'
                    )
                    ELSE atividade.cd_unidade_local_servico
                END
        LEFT JOIN pessoa p
            ON servidor.cd_cpf_pessoa = p.cd_cpf_pessoa
        WHERE cargoServidor.dt_fim_nomeacao IS NULL
            OR cargoServidor.dt_fim_nomeacao > GETDATE()

        UNION

        SELECT DISTINCT
            p.nm_pessoa AS nome,
            p.nm_social AS nome_social,
            p.cd_cpf_pessoa AS cpf,
            p.cd_cpf_pessoa AS codigo_rf,
            ue.cd_unidade_educacao AS codigo_ue,
            ue.cd_unidade_administrativa_referencia AS codigo_dre,
            ce.dt_inicio AS data_inicio,
            ce.dt_cancelamento AS data_fim,
            CAST(NULL AS DATETIME) AS dt_fim_nomeacao,
            CAST(NULL AS DATETIME) AS dt_fim_funcao_atividade,
            'externo' AS origem_vinculo,
            '' AS cargo,
            CAST(NULL AS INT) AS cd_cargo,
            0 AS cd_tipo_funcao_atividade,
            0 AS cd_cargo_base_servidor,
            ffe.cd_funcao_externo AS funcao_externo,
            ffe.cd_tipo_funcao_funcionario_externo AS tipo_funcao_externo,
            p.cd_pessoa AS pessoa_id,
            ue.nm_unidade_educacao AS nome_ue,
            tfe.dc_tipo_funcionario_externo AS tipo_funcionario_externo,
            fe.dc_funcao_externo AS dc_funcao_externo,
            0 AS supervisor_dre
        FROM contrato_externo ce
        INNER JOIN pessoa p
            ON ce.cd_pessoa = p.cd_pessoa
        INNER JOIN funcao_funcionario_externo ffe
            ON ce.cd_tipo_funcao_funcionario_externo
                = ffe.cd_tipo_funcao_funcionario_externo
        INNER JOIN v_cadastro_unidade_educacao ue
            ON ce.cd_unidade_educacao = ue.cd_unidade_educacao
        LEFT JOIN tipo_funcionario_externo tfe
            ON ffe.cd_tipo_funcionario_externo
                = tfe.cd_tipo_funcionario_externo
        LEFT JOIN funcao_externo fe
            ON ffe.cd_funcao_externo = fe.cd_funcao_externo
        WHERE ce.dt_cancelamento IS NULL
    ) funcionarios
    LEFT JOIN laudo_ativo laudo
        ON laudo.cd_cargo_base_servidor
            = funcionarios.cd_cargo_base_servidor
        AND laudo.ordem = 1
"""


SQL_ADMINISTRADORES_SGP = """
    SELECT
        U.uad_codigo AS codigo_ue,
        US.usu_login AS rf_login
    FROM SYS_UsuarioGrupoUA UGA
        INNER JOIN SYS_UnidadeAdministrativa U
            ON UGA.uad_id = U.uad_id
        INNER JOIN SYS_Usuario US
            ON UGA.usu_id = US.usu_id
        INNER JOIN SYS_Grupo G
            ON UGA.gru_id = G.gru_id
    WHERE US.usu_situacao = 1
        AND G.gru_id IN (
            '48E1E074-37D6-E911-ABD6-F81654FE895D',  -- ADM UE
            '42E1E074-37D6-E911-ABD6-F81654FE895D'   -- ADM DRE
        )
        AND G.sis_id = 1000  -- Sistema SGP
    ORDER BY U.uad_codigo, US.usu_login
"""

SQL_FUNCIONARIO_SISTEMA_PERFIL = """
    SELECT
        login,
        MAX(nome_servidor) AS nome_servidor,
        MAX(cpf) AS cpf,
        MAX(email) AS email,
        perfil,
        MAX(uad_codigo) AS uad_codigo,
        sis_id
    FROM (
        SELECT
            US.usu_login AS login,
            PP.pes_nome AS nome_servidor,
            PPD.psd_numero AS cpf,
            US.usu_email AS email,
            G.gru_id AS perfil,
            U.uad_codigo AS uad_codigo,
            G.sis_id AS sis_id
        FROM SYS_UsuarioGrupoUA UGA
        INNER JOIN SYS_UnidadeAdministrativa U
            ON UGA.uad_id = U.uad_id
        INNER JOIN SYS_Usuario US
            ON UGA.usu_id = US.usu_id
        INNER JOIN SYS_Grupo G
            ON UGA.gru_id = G.gru_id
        INNER JOIN PES_Pessoa PP
            ON PP.pes_id = US.pes_id
        INNER JOIN PES_PessoaDocumento PPD
            ON PPD.pes_id = PP.pes_id
        INNER JOIN SYS_UsuarioGrupo UG
            ON US.usu_id = UG.usu_id
            AND G.gru_id = UG.gru_id
        WHERE US.usu_situacao = 1
          AND UG.usg_situacao = 1
        UNION
        SELECT
            US.usu_login AS login,
            PP.pes_nome AS nome_servidor,
            PPD.psd_numero AS cpf,
            US.usu_email AS email,
            G.gru_id AS perfil,
            NULL AS uad_codigo,
            G.sis_id AS sis_id
        FROM SYS_Usuario US
        INNER JOIN SYS_UsuarioGrupo UG
            ON UG.usu_id = US.usu_id
        INNER JOIN SYS_Grupo G
            ON UG.gru_id = G.gru_id
        LEFT JOIN PES_Pessoa PP
            ON PP.pes_id = US.pes_id
        LEFT JOIN PES_PessoaDocumento PPD
            ON PPD.pes_id = PP.pes_id
        WHERE US.usu_situacao = 1
          AND G.sis_id = 1000
    ) AS Funcionarios
    GROUP BY login, perfil, sis_id;
"""
