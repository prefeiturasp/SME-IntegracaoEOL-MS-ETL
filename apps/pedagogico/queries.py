# flake8: noqa: E501

"""Queries SQL do domínio pedagógico."""

_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO = 26
_MOTIVO_DISPONIBILIZACAO_FIM_ANO_LETIVO = 34
_TIPO_UNIDADE_ADMINISTRATIVA_DRE = 24

# Código sentinela que indica "território não utilizado" — não é um território real.
# O C# filtra explicitamente != 1 antes de agrupar (CargaDBAgrupamentosTerritorioSaberPorTurmaUseCase.cs:43
# e ComponenteCurricularService.cs:318). Registros com esse código devem ser ignorados.
_TERRITORIO_SABER_NAO_UTILIZADO = 1

# Tipos de escola que admitem professor externo:
# CEI_INDIR=11, CRP_CONV=12, EMEFPFOM=32, EMEIPFOM=33
_TIPOS_ESCOLA_EXTERNOS = "(11, 12, 32, 33)"

# Anos letivos disponíveis no EOL (EolConnection)
SQL_ANOS_LETIVOS = """
SELECT DISTINCT an_letivo
FROM turma_escola (NOLOCK)
WHERE st_turma_escola IN ('O', 'A', 'C', 'E')
ORDER BY an_letivo
"""

SQL_COMPONENTES_POR_TURMA = f"""
WITH
-- Base comum: turmas ativas do ano com turno e tipo de escola
cte_turmas AS (
    SELECT te.cd_turma_escola,
           te.cd_escola,
           te.an_letivo,
           te.dt_fim_turma,
           esc.tp_escola,
           dtt.qt_hora_duracao AS TurnoTurma
    FROM turma_escola (NOLOCK) te
        INNER JOIN escola (NOLOCK) esc ON te.cd_escola = esc.cd_escola
        INNER JOIN duracao_tipo_turno (NOLOCK) dtt
            ON te.cd_tipo_turno = dtt.cd_tipo_turno AND te.cd_duracao = dtt.cd_duracao
    WHERE te.st_turma_escola IN ('O', 'A', 'C', 'E')
      AND te.an_letivo = ?
),
-- Componentes via série (grade curricular normal)
cte_serie AS (
    SELECT t.cd_turma_escola,
           t.cd_escola,
           t.an_letivo,
           t.dt_fim_turma,
           t.tp_escola,
           t.TurnoTurma,
           serie_ensino.sg_resumida_serie   AS AnoTurma,
           stg.cd_serie_grade               AS CodigoSerieGrade,
           gcc.cd_grade                     AS CodigoGrade,
           iif(pcc.cd_componente_curricular IS NOT NULL,
               pcc.cd_componente_curricular,
               cc.cd_componente_curricular) AS Codigo,
           iif(pcc.dc_componente_curricular IS NOT NULL,
               pcc.dc_componente_curricular,
               cc.dc_componente_curricular) AS Descricao
    FROM cte_turmas t
        LEFT JOIN serie_turma_escola (NOLOCK) ste
            ON ste.cd_turma_escola = t.cd_turma_escola
        LEFT JOIN serie_turma_grade (NOLOCK) stg
            ON stg.cd_turma_escola = ste.cd_turma_escola AND stg.dt_fim IS NULL
        LEFT JOIN escola_grade (NOLOCK) eg
            ON stg.cd_escola_grade = eg.cd_escola_grade
        LEFT JOIN grade (NOLOCK) g ON eg.cd_grade = g.cd_grade
        LEFT JOIN grade_componente_curricular (NOLOCK) gcc ON gcc.cd_grade = g.cd_grade
        LEFT JOIN componente_curricular (NOLOCK) cc
            ON cc.cd_componente_curricular = gcc.cd_componente_curricular
            AND cc.dt_cancelamento IS NULL
        LEFT JOIN serie_ensino (NOLOCK) ON g.cd_serie_ensino = serie_ensino.cd_serie_ensino
        -- Programa (IIF para priorizar componente do programa sobre o da série)
        LEFT JOIN turma_escola_grade_programa (NOLOCK) tegp
            ON tegp.cd_turma_escola = t.cd_turma_escola
        LEFT JOIN escola_grade (NOLOCK) teg ON teg.cd_escola_grade = tegp.cd_escola_grade
        LEFT JOIN grade_componente_curricular (NOLOCK) pgcc ON pgcc.cd_grade = teg.cd_grade
        LEFT JOIN componente_curricular (NOLOCK) pcc
            ON pgcc.cd_componente_curricular = pcc.cd_componente_curricular
            AND pcc.dt_cancelamento IS NULL
),
-- Componentes via programa (grade de programa — turmas sem série)
cte_programa AS (
    SELECT t.cd_turma_escola,
           t.cd_escola,
           t.an_letivo,
           t.dt_fim_turma,
           t.tp_escola,
           t.TurnoTurma,
           serie_ensino.sg_resumida_serie   AS AnoTurma,
           NULL                             AS CodigoSerieGrade,
           pgcc.cd_grade                    AS CodigoGrade,
           pcc.cd_componente_curricular     AS Codigo,
           pcc.dc_componente_curricular     AS Descricao
    FROM cte_turmas t
        INNER JOIN turma_escola_grade_programa (NOLOCK) tegp
            ON tegp.cd_turma_escola = t.cd_turma_escola
        INNER JOIN escola_grade (NOLOCK) teg ON teg.cd_escola_grade = tegp.cd_escola_grade
        INNER JOIN grade (NOLOCK) pg ON pg.cd_grade = teg.cd_grade
        INNER JOIN grade_componente_curricular (NOLOCK) pgcc ON pgcc.cd_grade = teg.cd_grade
        INNER JOIN componente_curricular (NOLOCK) pcc
            ON pgcc.cd_componente_curricular = pcc.cd_componente_curricular
            AND pcc.dt_cancelamento IS NULL
        LEFT JOIN serie_ensino (NOLOCK) ON pg.cd_serie_ensino = serie_ensino.cd_serie_ensino
        -- Exclui turmas que já têm série (evita duplicata com cte_serie)
        WHERE NOT EXISTS (
            SELECT 1 FROM serie_turma_escola (NOLOCK) ste2
            WHERE ste2.cd_turma_escola = t.cd_turma_escola
        )
)

-- Branch 1: Série × SME
SELECT s.Codigo, s.Descricao, s.tp_escola AS TipoEscola, s.TurnoTurma,
       s.AnoTurma, s.an_letivo AS anoletivo, s.cd_turma_escola AS TurmaCodigo,
       vsc.cd_registro_funcional AS Professor,
       0 AS AtribuicaoExterna
FROM cte_serie s
LEFT JOIN atribuicao_aula (NOLOCK) aa
    ON aa.cd_grade = s.CodigoGrade
    AND aa.cd_componente_curricular = s.Codigo
    AND aa.cd_serie_grade = s.CodigoSerieGrade
    AND aa.an_atribuicao = s.an_letivo
    AND aa.dt_cancelamento IS NULL
    AND (aa.cd_motivo_disponibilizacao <> {_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO}
         OR aa.cd_motivo_disponibilizacao IS NULL)
    AND (aa.dt_disponibilizacao_aulas IS NULL
         OR aa.cd_motivo_disponibilizacao = {_MOTIVO_DISPONIBILIZACAO_FIM_ANO_LETIVO})
LEFT JOIN v_cargo_base_cotic (NOLOCK) vcbc ON vcbc.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
LEFT JOIN v_servidor_cotic (NOLOCK) vsc ON vsc.cd_servidor = vcbc.cd_servidor

UNION ALL

-- Branch 2: Série × Externo
SELECT s.Codigo, s.Descricao, s.tp_escola AS TipoEscola, s.TurnoTurma,
       s.AnoTurma, s.an_letivo AS anoletivo, s.cd_turma_escola AS TurmaCodigo,
       pe.cd_cpf_pessoa AS Professor,
       1 AS AtribuicaoExterna
FROM cte_serie s
LEFT JOIN atribuicao_externo (NOLOCK) ae
    ON ae.cd_grade = s.CodigoGrade
    AND ae.cd_componente_curricular = s.Codigo
    AND ae.an_atribuicao = s.an_letivo
    AND ae.dt_cancelamento IS NULL
    AND (ae.cd_motivo_disponibilizacao_externo <> 1
         OR ae.cd_motivo_disponibilizacao_externo IS NULL)
LEFT JOIN contrato_externo (NOLOCK) ce ON ce.cd_contrato_externo = ae.cd_contrato_externo
LEFT JOIN pessoa (NOLOCK) pe ON pe.cd_pessoa = ce.cd_pessoa
WHERE s.tp_escola IN {_TIPOS_ESCOLA_EXTERNOS}

UNION ALL

-- Branch 3: Programa × SME
SELECT p.Codigo, p.Descricao, p.tp_escola AS TipoEscola, p.TurnoTurma,
       p.AnoTurma, p.an_letivo AS anoletivo, p.cd_turma_escola AS TurmaCodigo,
       vsc.cd_registro_funcional AS Professor,
       0 AS AtribuicaoExterna
FROM cte_programa p
LEFT JOIN atribuicao_aula (NOLOCK) aa
    ON aa.cd_grade = p.CodigoGrade
    AND aa.cd_componente_curricular = p.Codigo
    AND aa.an_atribuicao = p.an_letivo
    AND aa.dt_cancelamento IS NULL
    AND (aa.cd_motivo_disponibilizacao <> {_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO}
         OR aa.cd_motivo_disponibilizacao IS NULL)
    AND (aa.dt_disponibilizacao_aulas IS NULL
         OR aa.cd_motivo_disponibilizacao = {_MOTIVO_DISPONIBILIZACAO_FIM_ANO_LETIVO})
LEFT JOIN v_cargo_base_cotic (NOLOCK) vcbc ON vcbc.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
LEFT JOIN v_servidor_cotic (NOLOCK) vsc ON vsc.cd_servidor = vcbc.cd_servidor

UNION ALL

-- Branch 4: Programa × Externo
SELECT p.Codigo, p.Descricao, p.tp_escola AS TipoEscola, p.TurnoTurma,
       p.AnoTurma, p.an_letivo AS anoletivo, p.cd_turma_escola AS TurmaCodigo,
       pe.cd_cpf_pessoa AS Professor,
       1 AS AtribuicaoExterna
FROM cte_programa p
LEFT JOIN atribuicao_externo (NOLOCK) ae
    ON ae.cd_grade = p.CodigoGrade
    AND ae.cd_componente_curricular = p.Codigo
    AND ae.an_atribuicao = p.an_letivo
    AND ae.dt_cancelamento IS NULL
    AND (ae.cd_motivo_disponibilizacao_externo <> 1
         OR ae.cd_motivo_disponibilizacao_externo IS NULL)
LEFT JOIN contrato_externo (NOLOCK) ce ON ce.cd_contrato_externo = ae.cd_contrato_externo
LEFT JOIN pessoa (NOLOCK) pe ON pe.cd_pessoa = ce.cd_pessoa
WHERE p.tp_escola IN {_TIPOS_ESCOLA_EXTERNOS}

UNION ALL

-- Branch 5: escola/grade × SME (tmpComponentes original)
SELECT DISTINCT cc.cd_componente_curricular AS Codigo,
                cc.dc_componente_curricular AS Descricao,
                t.tp_escola AS TipoEscola, t.TurnoTurma, t.AnoTurma,
                t.an_letivo AS anoletivo, t.cd_turma_escola AS TurmaCodigo,
                servidor.cd_registro_funcional AS Professor,
                0 AS AtribuicaoExterna
FROM (
    SELECT t2.cd_turma_escola, t2.cd_escola, t2.an_letivo, t2.dt_fim_turma,
           t2.tp_escola, t2.TurnoTurma,
           serie_ensino.sg_resumida_serie AS AnoTurma,
           stg.cd_serie_grade AS CodigoSerieGrade,
           g.cd_grade AS CodigoGrade
    FROM cte_turmas t2
        INNER JOIN serie_turma_escola (NOLOCK) ste ON ste.cd_turma_escola = t2.cd_turma_escola
        INNER JOIN serie_turma_grade (NOLOCK) stg
            ON stg.cd_turma_escola = ste.cd_turma_escola
        INNER JOIN escola_grade (NOLOCK) eg ON stg.cd_escola_grade = eg.cd_escola_grade
        INNER JOIN grade (NOLOCK) g ON eg.cd_grade = g.cd_grade
        INNER JOIN serie_ensino (NOLOCK) ON g.cd_serie_ensino = serie_ensino.cd_serie_ensino
) t
INNER JOIN atribuicao_aula (NOLOCK) aa
    ON aa.cd_grade = t.CodigoGrade
    AND aa.an_atribuicao = t.an_letivo
    AND aa.cd_unidade_educacao = t.cd_escola
    AND aa.dt_disponibilizacao_aulas IS NOT NULL
    AND aa.dt_cancelamento IS NULL
    AND aa.cd_motivo_disponibilizacao <> {_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO}
    AND (aa.cd_motivo_disponibilizacao = {_MOTIVO_DISPONIBILIZACAO_FIM_ANO_LETIVO}
         OR aa.cd_motivo_disponibilizacao IS NULL)
    AND COALESCE(aa.dt_disponibilizacao_aulas, t.dt_fim_turma) >= t.dt_fim_turma
INNER JOIN componente_curricular (NOLOCK) cc
    ON aa.cd_componente_curricular = cc.cd_componente_curricular
INNER JOIN v_cargo_base_cotic (NOLOCK) cargoServidor
    ON cargoServidor.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
INNER JOIN v_servidor_cotic (NOLOCK) servidor
    ON servidor.cd_servidor = cargoServidor.cd_servidor

UNION ALL

-- Branch 6: escola/grade × Externo (tmpComponentes original)
SELECT DISTINCT cc.cd_componente_curricular AS Codigo,
                cc.dc_componente_curricular AS Descricao,
                t.tp_escola AS TipoEscola, t.TurnoTurma, t.AnoTurma,
                t.an_letivo AS anoletivo, t.cd_turma_escola AS TurmaCodigo,
                pe.cd_cpf_pessoa AS Professor,
                1 AS AtribuicaoExterna
FROM (
    SELECT t2.cd_turma_escola, t2.cd_escola, t2.an_letivo, t2.dt_fim_turma,
           t2.tp_escola, t2.TurnoTurma,
           serie_ensino.sg_resumida_serie AS AnoTurma,
           stg.cd_serie_grade AS CodigoSerieGrade,
           g.cd_grade AS CodigoGrade
    FROM cte_turmas t2
        INNER JOIN serie_turma_escola (NOLOCK) ste ON ste.cd_turma_escola = t2.cd_turma_escola
        INNER JOIN serie_turma_grade (NOLOCK) stg
            ON stg.cd_turma_escola = ste.cd_turma_escola
        INNER JOIN escola_grade (NOLOCK) eg ON stg.cd_escola_grade = eg.cd_escola_grade
        INNER JOIN grade (NOLOCK) g ON eg.cd_grade = g.cd_grade
        INNER JOIN serie_ensino (NOLOCK) ON g.cd_serie_ensino = serie_ensino.cd_serie_ensino
) t
INNER JOIN atribuicao_externo (NOLOCK) ae
    ON ae.cd_grade = t.CodigoGrade
    AND ae.an_atribuicao = t.an_letivo
    AND ae.cd_unidade_educacao = t.cd_escola
    AND ae.dt_disponibilizacao IS NOT NULL
    AND ae.dt_cancelamento IS NULL
    AND ae.cd_motivo_disponibilizacao_externo <> 1
    AND (ae.cd_motivo_disponibilizacao_externo = 3
         OR ae.cd_motivo_disponibilizacao_externo IS NULL)
    AND COALESCE(ae.dt_disponibilizacao, t.dt_fim_turma) >= t.dt_fim_turma
INNER JOIN componente_curricular (NOLOCK) cc
    ON ae.cd_componente_curricular = cc.cd_componente_curricular
INNER JOIN contrato_externo (NOLOCK) ce ON ce.cd_contrato_externo = ae.cd_contrato_externo
INNER JOIN pessoa (NOLOCK) pe ON pe.cd_pessoa = ce.cd_pessoa
WHERE t.tp_escola IN {_TIPOS_ESCOLA_EXTERNOS}
"""

# Alimenta: componente_curricular_regencia
# Parâmetros (?):
#   1 — ano_letivo (SME)
#   2 — ano_letivo (Externo)
SQL_COMPONENTE_CURRICULAR_REGENCIA = f"""
-- SME — professor via RF
SELECT
    cc.cd_componente_curricular         AS CodigoComponenteCurricular,
    cc.dc_componente_curricular         AS DescricaoComponenteCurricular,
    serie_ensino.sg_resumida_serie      AS AnoTurma,
    te.an_letivo                        AS anoletivo,
    te.cd_turma_escola                  AS TurmaCodigo,
    esc.tp_escola                       AS TipoEscola,
    dtt.qt_hora_duracao                 AS TurnoTurma,
    vsc.cd_registro_funcional           AS rfProfessor,
    tgt.cd_experiencia_pedagogica       AS CodigoExperienciaPedagogica,
    tgt.cd_territorio_saber             AS CodigoTerritorioSaber,
    ter.dc_territorio_saber             AS DescricaoTerritorioSaber,
    exp.dc_experiencia_pedagogica       AS DescricaoExperienciaPedagogica,
    aa.dt_atribuicao_aula               AS dataAtribuicao,
    aa.an_atribuicao                    AS AnoAtribuicao,
    te.dt_fim_turma                     AS DataFimTurma,
    0                                   AS AtribuicaoExterna,
    MAX(aa.dt_disponibilizacao_aulas)   AS dataDisponibilizacao,
    MAX(aa.cd_motivo_disponibilizacao)  AS CodigoMotivoDisponibilizacao
FROM turma_escola te
    INNER JOIN escola esc ON te.cd_escola = esc.cd_escola
    INNER JOIN v_cadastro_unidade_educacao ue ON ue.cd_unidade_educacao = esc.cd_escola
    INNER JOIN unidade_administrativa dre
        ON dre.tp_unidade_administrativa = {_TIPO_UNIDADE_ADMINISTRATIVA_DRE}
        AND ue.cd_unidade_administrativa_referencia = dre.cd_unidade_administrativa
    -- Serie Ensino
    INNER JOIN serie_turma_escola ON serie_turma_escola.cd_turma_escola = te.cd_turma_escola
    INNER JOIN serie_turma_grade
        ON serie_turma_grade.cd_turma_escola = serie_turma_escola.cd_turma_escola
        AND serie_turma_grade.dt_fim IS NULL
    INNER JOIN escola_grade ON serie_turma_grade.cd_escola_grade = escola_grade.cd_escola_grade
    INNER JOIN grade ON escola_grade.cd_grade = grade.cd_grade
    INNER JOIN grade_componente_curricular gcc ON gcc.cd_grade = grade.cd_grade
    INNER JOIN componente_curricular cc
        ON cc.cd_componente_curricular = gcc.cd_componente_curricular
        AND cc.dt_cancelamento IS NULL
    INNER JOIN serie_ensino ON grade.cd_serie_ensino = serie_ensino.cd_serie_ensino
    INNER JOIN turma_grade_territorio_experiencia tgt
        ON tgt.cd_serie_grade = serie_turma_grade.cd_serie_grade
        AND tgt.cd_componente_curricular = cc.cd_componente_curricular
    INNER JOIN tipo_experiencia_pedagogica exp
        ON exp.cd_experiencia_pedagogica = tgt.cd_experiencia_pedagogica
    INNER JOIN território_saber ter ON ter.cd_territorio_saber = tgt.cd_territorio_saber
    INNER JOIN duracao_tipo_turno dtt
        ON te.cd_tipo_turno = dtt.cd_tipo_turno AND te.cd_duracao = dtt.cd_duracao
    -- Atribuição SME
    INNER JOIN atribuicao_aula (NOLOCK) aa
        ON gcc.cd_grade = aa.cd_grade
        AND gcc.cd_componente_curricular = aa.cd_componente_curricular
        AND aa.cd_serie_grade = serie_turma_grade.cd_serie_grade
        AND aa.dt_cancelamento IS NULL
        AND aa.an_atribuicao = te.an_letivo
        AND COALESCE(aa.dt_disponibilizacao_aulas, GETDATE()) >= '2020-02-05'
        AND (aa.cd_motivo_disponibilizacao <> {_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO}
             OR aa.cd_motivo_disponibilizacao IS NULL)
        AND aa.dt_atribuicao_aula <= GETDATE()
    INNER JOIN v_cargo_base_cotic (NOLOCK) vcbc ON aa.cd_cargo_base_servidor = vcbc.cd_cargo_base_servidor
    INNER JOIN v_servidor_cotic (NOLOCK) vsc ON vcbc.cd_servidor = vsc.cd_servidor
WHERE te.st_turma_escola IN ('O', 'A', 'C', 'E')
  AND te.an_letivo = ?  -- param 1: ano_letivo
  AND tgt.cd_territorio_saber <> {_TERRITORIO_SABER_NAO_UTILIZADO}
GROUP BY
    cc.cd_componente_curricular, cc.dc_componente_curricular,
    serie_ensino.sg_resumida_serie, te.an_letivo, te.cd_turma_escola,
    esc.tp_escola, dtt.qt_hora_duracao,
    vsc.cd_registro_funcional, tgt.cd_experiencia_pedagogica,
    tgt.cd_territorio_saber, ter.dc_territorio_saber,
    exp.dc_experiencia_pedagogica, aa.dt_atribuicao_aula,
    CAST(aa.dt_disponibilizacao_aulas AS DATE), te.dt_fim_turma, aa.an_atribuicao

UNION ALL

-- Externo — professor via CPF
SELECT
    cc.cd_componente_curricular              AS CodigoComponenteCurricular,
    cc.dc_componente_curricular              AS DescricaoComponenteCurricular,
    serie_ensino.sg_resumida_serie           AS AnoTurma,
    te.an_letivo                             AS anoletivo,
    te.cd_turma_escola                       AS TurmaCodigo,
    esc.tp_escola                            AS TipoEscola,
    dtt.qt_hora_duracao                      AS TurnoTurma,
    pe.cd_cpf_pessoa                         AS rfProfessor,
    tgt.cd_experiencia_pedagogica            AS CodigoExperienciaPedagogica,
    tgt.cd_territorio_saber                  AS CodigoTerritorioSaber,
    ter.dc_territorio_saber                  AS DescricaoTerritorioSaber,
    exp.dc_experiencia_pedagogica            AS DescricaoExperienciaPedagogica,
    aa_ext.dt_atribuicao                     AS dataAtribuicao,
    aa_ext.an_atribuicao                     AS AnoAtribuicao,
    te.dt_fim_turma                          AS DataFimTurma,
    1                                        AS AtribuicaoExterna,
    MAX(aa_ext.dt_disponibilizacao)          AS dataDisponibilizacao,
    MAX(aa_ext.cd_motivo_disponibilizacao_externo) AS CodigoMotivoDisponibilizacao
FROM turma_escola te
    INNER JOIN escola esc ON te.cd_escola = esc.cd_escola
    INNER JOIN v_cadastro_unidade_educacao ue ON ue.cd_unidade_educacao = esc.cd_escola
    INNER JOIN unidade_administrativa dre
        ON dre.tp_unidade_administrativa = 24
        AND ue.cd_unidade_administrativa_referencia = dre.cd_unidade_administrativa
    -- Serie Ensino
    INNER JOIN serie_turma_escola ON serie_turma_escola.cd_turma_escola = te.cd_turma_escola
    INNER JOIN serie_turma_grade
        ON serie_turma_grade.cd_turma_escola = serie_turma_escola.cd_turma_escola
        AND serie_turma_grade.dt_fim IS NULL
    INNER JOIN escola_grade ON serie_turma_grade.cd_escola_grade = escola_grade.cd_escola_grade
    INNER JOIN grade ON escola_grade.cd_grade = grade.cd_grade
    INNER JOIN grade_componente_curricular gcc ON gcc.cd_grade = grade.cd_grade
    INNER JOIN componente_curricular cc
        ON cc.cd_componente_curricular = gcc.cd_componente_curricular
        AND cc.dt_cancelamento IS NULL
    INNER JOIN serie_ensino ON grade.cd_serie_ensino = serie_ensino.cd_serie_ensino
    INNER JOIN turma_grade_territorio_experiencia tgt
        ON tgt.cd_serie_grade = serie_turma_grade.cd_serie_grade
        AND tgt.cd_componente_curricular = cc.cd_componente_curricular
    INNER JOIN tipo_experiencia_pedagogica exp
        ON exp.cd_experiencia_pedagogica = tgt.cd_experiencia_pedagogica
    INNER JOIN território_saber ter ON ter.cd_territorio_saber = tgt.cd_territorio_saber
    INNER JOIN duracao_tipo_turno dtt
        ON te.cd_tipo_turno = dtt.cd_tipo_turno AND te.cd_duracao = dtt.cd_duracao
    -- Atribuição Externo
    INNER JOIN atribuicao_externo (NOLOCK) aa_ext
        ON gcc.cd_grade = aa_ext.cd_grade
        AND gcc.cd_componente_curricular = aa_ext.cd_componente_curricular
        AND aa_ext.cd_serie_grade = serie_turma_grade.cd_serie_grade
        AND aa_ext.dt_cancelamento IS NULL
        AND aa_ext.an_atribuicao = te.an_letivo
        AND COALESCE(aa_ext.dt_disponibilizacao, GETDATE()) >= '2020-02-05'
        AND (aa_ext.cd_motivo_disponibilizacao_externo <> {_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO}
             OR aa_ext.cd_motivo_disponibilizacao_externo IS NULL)
        AND aa_ext.dt_atribuicao <= GETDATE()
    INNER JOIN contrato_externo ce (NOLOCK) ON ce.cd_contrato_externo = aa_ext.cd_contrato_externo
    INNER JOIN pessoa pe (NOLOCK) ON pe.cd_pessoa = ce.cd_pessoa
WHERE te.st_turma_escola IN ('O', 'A', 'C', 'E')
  AND te.an_letivo = ?  -- param 2: ano_letivo
  AND tgt.cd_territorio_saber <> {_TERRITORIO_SABER_NAO_UTILIZADO}
GROUP BY
    cc.cd_componente_curricular, cc.dc_componente_curricular,
    serie_ensino.sg_resumida_serie, te.an_letivo, te.cd_turma_escola,
    esc.tp_escola, dtt.qt_hora_duracao,
    pe.cd_cpf_pessoa, tgt.cd_experiencia_pedagogica,
    tgt.cd_territorio_saber, ter.dc_territorio_saber,
    exp.dc_experiencia_pedagogica, aa_ext.dt_atribuicao,
    CAST(aa_ext.dt_disponibilizacao AS DATE), te.dt_fim_turma, aa_ext.an_atribuicao
"""

SQL_COMPONENTES_NAO_CANCELADOS = """
SELECT
    cd_componente_curricular              AS Codigo,
    RTRIM(LTRIM(dc_componente_curricular)) AS Descricao
FROM componente_curricular
WHERE dt_cancelamento IS NULL
"""

# Alimenta: dados_aula_turma
# Parâmetros (?):
#   1 — ano_letivo
#
# Obs: ue_codigo e ano_letivo vêm no SELECT (não são filtros do ETL).
#      O microsserviço filtra por ue_codigo e componentes no PEDAGOGICO_DB.
SQL_DADOS_AULA_TURMA = """
SELECT DISTINCT
    cc.cd_componente_curricular AS ComponenteCurricularCodigo,
    cc.dc_componente_curricular AS ComponenteCurricularDescricao,
    te.cd_turma_escola          AS TurmaCodigo,
    te.dt_inicio_turma          AS DataInicioTurma,
    te.cd_escola                AS UeCodigo,
    te.an_letivo                AS AnoLetivo,
    te.cd_tipo_periodicidade    AS TipoPeriodicidade
FROM turma_escola (NOLOCK) te
    INNER JOIN escola (NOLOCK) esc ON te.cd_escola = esc.cd_escola
    -- Serie Ensino
    LEFT JOIN serie_turma_escola (NOLOCK)
        ON serie_turma_escola.cd_turma_escola = te.cd_turma_escola
    LEFT JOIN serie_turma_grade (NOLOCK)
        ON serie_turma_grade.cd_turma_escola = serie_turma_escola.cd_turma_escola
        AND serie_turma_grade.dt_fim IS NULL
    LEFT JOIN escola_grade (NOLOCK)
        ON serie_turma_grade.cd_escola_grade = escola_grade.cd_escola_grade
    LEFT JOIN grade (NOLOCK) ON escola_grade.cd_grade = grade.cd_grade
    LEFT JOIN grade_componente_curricular (NOLOCK) gcc ON gcc.cd_grade = grade.cd_grade
    LEFT JOIN componente_curricular (NOLOCK) cc
        ON cc.cd_componente_curricular = gcc.cd_componente_curricular
        AND cc.dt_cancelamento IS NULL
    LEFT JOIN serie_ensino (NOLOCK) ON grade.cd_serie_ensino = serie_ensino.cd_serie_ensino
    -- Atribuição
    INNER JOIN atribuicao_aula (NOLOCK) aa
        ON gcc.cd_grade = aa.cd_grade
        AND gcc.cd_componente_curricular = aa.cd_componente_curricular
        AND aa.cd_serie_grade = serie_turma_grade.cd_serie_grade
        AND aa.dt_cancelamento IS NULL
        AND aa.an_atribuicao = te.an_letivo
    INNER JOIN v_cargo_base_cotic (NOLOCK) vcbc ON aa.cd_cargo_base_servidor = vcbc.cd_cargo_base_servidor
    INNER JOIN v_servidor_cotic (NOLOCK) vsc ON vcbc.cd_servidor = vsc.cd_servidor
    INNER JOIN duracao_tipo_turno dtt
        ON te.cd_tipo_turno = dtt.cd_tipo_turno AND te.cd_duracao = dtt.cd_duracao
WHERE te.st_turma_escola IN ('O', 'A', 'C', 'E')
  AND te.an_letivo = ?  -- param 1: ano_letivo
"""

# Alimenta: componente_curricular_por_ano_letivo
# Parâmetros (?):
#   1 — ano_letivo
SQL_COMPONENTES_POR_ANO_LETIVO = """
;WITH componentesAnoTurmas AS (
    SELECT DISTINCT
        iif(pcc.cd_componente_curricular IS NOT NULL, pcc.cd_componente_curricular,
            cc.cd_componente_curricular)                                 AS CodigoComponenteCurricular,
        LTRIM(RTRIM(iif(pcc.dc_componente_curricular IS NOT NULL, pcc.dc_componente_curricular,
            cc.dc_componente_curricular)))                               AS DescricaoComponenteCurricular,
        serie_ensino.sg_resumida_serie                                   AS CodigoAnoTurma,
        LTRIM(RTRIM(serie_ensino.sg_serie_ensino))                       AS DescricaoSerieEnsino,
        serie_ensino.cd_serie_ensino                                     AS CodigoSerieEnsino,
        CASE
            WHEN eten.cd_etapa_ensino IN (1, 10)          THEN 1  -- EI
            WHEN eten.cd_etapa_ensino IN (2, 3, 7, 11)    THEN 3  -- EJA
            WHEN esc.tp_escola = 13                        THEN 4  -- CIEJA
            WHEN eten.cd_etapa_ensino IN (4, 5, 12, 13)   THEN 5  -- EF
            WHEN eten.cd_etapa_ensino IN (6, 7, 8, 9, 17, 14) THEN 6  -- EM
        END                                                              AS Modalidade,
        te.an_letivo                                                     AS AnoLetivo
    FROM turma_escola te
        INNER JOIN escola esc ON te.cd_escola = esc.cd_escola
        INNER JOIN v_cadastro_unidade_educacao ue ON ue.cd_unidade_educacao = esc.cd_escola
        INNER JOIN unidade_administrativa dre
            ON dre.tp_unidade_administrativa = 24
            AND ue.cd_unidade_administrativa_referencia = dre.cd_unidade_administrativa
        -- Serie Ensino
        LEFT JOIN serie_turma_escola ON serie_turma_escola.cd_turma_escola = te.cd_turma_escola
        LEFT JOIN serie_turma_grade
            ON serie_turma_grade.cd_turma_escola = serie_turma_escola.cd_turma_escola
            AND serie_turma_grade.dt_fim IS NULL
        LEFT JOIN escola_grade ON serie_turma_grade.cd_escola_grade = escola_grade.cd_escola_grade
        LEFT JOIN grade ON escola_grade.cd_grade = grade.cd_grade
        LEFT JOIN grade_componente_curricular gcc ON gcc.cd_grade = grade.cd_grade
        LEFT JOIN componente_curricular cc
            ON cc.cd_componente_curricular = gcc.cd_componente_curricular
            AND cc.dt_cancelamento IS NULL
        LEFT JOIN serie_ensino ON grade.cd_serie_ensino = serie_ensino.cd_serie_ensino
        -- Programa
        LEFT JOIN tipo_programa tp ON te.cd_tipo_programa = tp.cd_tipo_programa
        LEFT JOIN turma_escola_grade_programa tegp ON tegp.cd_turma_escola = te.cd_turma_escola
        LEFT JOIN escola_grade teg ON teg.cd_escola_grade = tegp.cd_escola_grade
        LEFT JOIN grade pg ON pg.cd_grade = teg.cd_grade
        LEFT JOIN grade_componente_curricular pgcc ON pgcc.cd_grade = teg.cd_grade
        LEFT JOIN componente_curricular pcc
            ON pgcc.cd_componente_curricular = pcc.cd_componente_curricular
            AND pcc.dt_cancelamento IS NULL
        -- Turno
        INNER JOIN duracao_tipo_turno dtt
            ON te.cd_tipo_turno = dtt.cd_tipo_turno AND te.cd_duracao = dtt.cd_duracao
        -- Etapa ensino
        LEFT JOIN etapa_ensino (NOLOCK) eten ON serie_ensino.cd_etapa_ensino = eten.cd_etapa_ensino
    WHERE te.st_turma_escola IN ('O', 'A', 'C')
      AND te.an_letivo = ?  -- param 1: ano_letivo
      AND serie_ensino.sg_resumida_serie IS NOT NULL
      AND serie_ensino.cd_serie_ensino IS NOT NULL
)
SELECT *
FROM componentesAnoTurmas
WHERE Modalidade > 0
  AND CodigoAnoTurma IS NOT NULL
  AND CodigoSerieEnsino IS NOT NULL
"""

# Alimenta: lookup para enriquecer componente_curricular_por_turma
# Parâmetros: nenhum (carga total)
# EhRegencia: lista hardcoded de IDs
# EhTerritorio: presença na tabela turma_grade_territorio_experiencia
# CodigoPai: resolvido via MAPA_COMPONENTE_PAI (constante hardcoded)
_IDS_REGENCIA = (
    508,
    511,
    1064,
    1065,
    1104,
    1105,
    1112,
    1113,
    1114,
    1115,
    1117,
    1121,
    1124,
    1125,
    1211,
    1212,
    1213,
    1290,
    1301,
)
_PLACEHOLDERS_REGENCIA = ",".join(str(i) for i in _IDS_REGENCIA)

SQL_LOOKUP_DISCIPLINAS = f"""
SELECT DISTINCT
    cc.cd_componente_curricular                          AS IdComponenteCurricular,
    RTRIM(LTRIM(cc.dc_componente_curricular))            AS Descricao,
    CASE
        WHEN cc.cd_componente_curricular IN ({_PLACEHOLDERS_REGENCIA}) THEN 1
        ELSE 0
    END                                                  AS EhRegencia,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM turma_grade_territorio_experiencia tgt
            WHERE tgt.cd_componente_curricular = cc.cd_componente_curricular
        ) THEN 1
        ELSE 0
    END                                                  AS EhTerritorio
FROM componente_curricular cc
WHERE cc.dt_cancelamento IS NULL
"""

# Alimenta: cruzamento para derivar planejamento_regencia
SQL_LOOKUP_PLANEJAMENTO_REGENCIA = f"""
SELECT DISTINCT
    gcc.cd_componente_curricular   AS IdComponenteCurricular,
    dtt.qt_hora_duracao            AS Turno,
    serie_ensino.sg_resumida_serie AS Ano
FROM grade_componente_curricular gcc
    INNER JOIN grade g
        ON g.cd_grade = gcc.cd_grade
    INNER JOIN serie_ensino
        ON serie_ensino.cd_serie_ensino = g.cd_serie_ensino
    INNER JOIN escola_grade eg
        ON eg.cd_grade = g.cd_grade
    INNER JOIN serie_turma_grade stg
        ON stg.cd_escola_grade = eg.cd_escola_grade
        AND stg.dt_fim IS NULL
    INNER JOIN serie_turma_escola ste
        ON ste.cd_turma_escola = stg.cd_turma_escola
    INNER JOIN turma_escola te
        ON te.cd_turma_escola = ste.cd_turma_escola
    INNER JOIN duracao_tipo_turno dtt
        ON te.cd_tipo_turno = dtt.cd_tipo_turno
        AND te.cd_duracao = dtt.cd_duracao
    INNER JOIN componente_curricular cc
        ON cc.cd_componente_curricular = gcc.cd_componente_curricular
WHERE gcc.cd_componente_curricular IN ({_PLACEHOLDERS_REGENCIA})
  AND cc.dt_cancelamento IS NULL
  AND te.st_turma_escola IN ('O', 'A', 'C')
"""

# Mapeamento componente → componente pai (constante hardcoded)
# Origem: tabela componentecurricularpai (ApiEolConnection) — dados estáticos
#
# Alimenta: campo codigo_componente_curricular_pai em ComponenteCurricularPorTurma (T2)
#   → lookup: MAPA_COMPONENTE_PAI.get(codigo)  → None se não tem pai
MAPA_COMPONENTE_PAI: dict[int, int] = {
    # idcomponentecurricular → idcomponentecurricularpai  (vigencia: 2021-12-31)
    512: 512,  # V40
    513: 512,
    534: 512,
    535: 512,
    515: 512,  # V56
    517: 512,
    518: 512,
}


# Alimenta: agrupamento_atribuicao_territorio_saber
# e componente_curricular_agrupamento
SQL_ATRIBUICOES_TERRITORIO_SABER = f"""
-- SME — professor via RF
SELECT
    cc.cd_componente_curricular       AS CodigoComponenteCurricular,
    te.cd_turma_escola                AS CodigoTurma,
    te.an_letivo                      AS AnoLetivo,
    vsc.cd_registro_funcional         AS RfProfessor,
    tgt.cd_territorio_saber           AS CodigoTerritorioSaber,
    tgt.cd_experiencia_pedagogica     AS CodigoExperienciaPedagogica,
    ter.dc_territorio_saber           AS DescricaoTerritorioSaber,
    exp.dc_experiencia_pedagogica     AS DescricaoExperienciaPedagogica,
    aa.dt_atribuicao_aula             AS DataAtribuicao,
    aa.dt_disponibilizacao_aulas      AS DataDisponibilizacao,
    aa.cd_motivo_disponibilizacao     AS CodigoMotivoDisponibilizacao,
    te.dt_fim_turma                   AS DataFimTurma,
    0                                 AS AtribuicaoExterna
FROM turma_escola te
    INNER JOIN escola esc ON te.cd_escola = esc.cd_escola
    INNER JOIN serie_turma_escola ste ON ste.cd_turma_escola = te.cd_turma_escola
    INNER JOIN serie_turma_grade stg
        ON stg.cd_turma_escola = ste.cd_turma_escola
        AND stg.dt_fim IS NULL
    INNER JOIN escola_grade eg ON eg.cd_escola_grade = stg.cd_escola_grade
    INNER JOIN grade g ON g.cd_grade = eg.cd_grade
    INNER JOIN grade_componente_curricular gcc ON gcc.cd_grade = g.cd_grade
    INNER JOIN componente_curricular cc
        ON cc.cd_componente_curricular = gcc.cd_componente_curricular
        AND cc.dt_cancelamento IS NULL
    INNER JOIN serie_ensino se ON se.cd_serie_ensino = g.cd_serie_ensino
    INNER JOIN turma_grade_territorio_experiencia tgt
        ON tgt.cd_serie_grade = stg.cd_serie_grade
        AND tgt.cd_componente_curricular = cc.cd_componente_curricular
    INNER JOIN tipo_experiencia_pedagogica exp
        ON exp.cd_experiencia_pedagogica = tgt.cd_experiencia_pedagogica
    INNER JOIN território_saber ter
        ON ter.cd_territorio_saber = tgt.cd_territorio_saber
    INNER JOIN atribuicao_aula aa
        ON gcc.cd_grade = aa.cd_grade
        AND gcc.cd_componente_curricular = aa.cd_componente_curricular
        AND aa.cd_serie_grade = stg.cd_serie_grade
        AND aa.dt_cancelamento IS NULL
        AND aa.an_atribuicao = te.an_letivo
        AND (aa.cd_motivo_disponibilizacao <> {_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO}
             OR aa.cd_motivo_disponibilizacao IS NULL)
    INNER JOIN v_cargo_base_cotic vcbc
        ON vcbc.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
    INNER JOIN v_servidor_cotic vsc ON vsc.cd_servidor = vcbc.cd_servidor
WHERE te.st_turma_escola IN ('O', 'A', 'C', 'E')

UNION ALL

-- Externos (CEI_INDIR=11, CRP_CONV=12, EMEFPFOM=32, EMEIPFOM=33)
SELECT
    cc.cd_componente_curricular       AS CodigoComponenteCurricular,
    te.cd_turma_escola                AS CodigoTurma,
    te.an_letivo                      AS AnoLetivo,
    pe.cd_cpf_pessoa                  AS RfProfessor,
    tgt.cd_territorio_saber           AS CodigoTerritorioSaber,
    tgt.cd_experiencia_pedagogica     AS CodigoExperienciaPedagogica,
    ter.dc_territorio_saber           AS DescricaoTerritorioSaber,
    exp.dc_experiencia_pedagogica     AS DescricaoExperienciaPedagogica,
    ae.dt_atribuicao                  AS DataAtribuicao,
    ae.dt_disponibilizacao            AS DataDisponibilizacao,
    ae.cd_motivo_disponibilizacao_externo AS CodigoMotivoDisponibilizacao,
    te.dt_fim_turma                   AS DataFimTurma,
    1                                 AS AtribuicaoExterna
FROM turma_escola te
    INNER JOIN escola esc ON te.cd_escola = esc.cd_escola
    INNER JOIN serie_turma_escola ste ON ste.cd_turma_escola = te.cd_turma_escola
    INNER JOIN serie_turma_grade stg
        ON stg.cd_turma_escola = ste.cd_turma_escola
        AND stg.dt_fim IS NULL
    INNER JOIN escola_grade eg ON eg.cd_escola_grade = stg.cd_escola_grade
    INNER JOIN grade g ON g.cd_grade = eg.cd_grade
    INNER JOIN grade_componente_curricular gcc ON gcc.cd_grade = g.cd_grade
    INNER JOIN componente_curricular cc
        ON cc.cd_componente_curricular = gcc.cd_componente_curricular
        AND cc.dt_cancelamento IS NULL
    INNER JOIN turma_grade_territorio_experiencia tgt
        ON tgt.cd_serie_grade = stg.cd_serie_grade
        AND tgt.cd_componente_curricular = cc.cd_componente_curricular
    INNER JOIN tipo_experiencia_pedagogica exp
        ON exp.cd_experiencia_pedagogica = tgt.cd_experiencia_pedagogica
    INNER JOIN território_saber ter
        ON ter.cd_territorio_saber = tgt.cd_territorio_saber
    INNER JOIN atribuicao_externo ae
        ON gcc.cd_grade = ae.cd_grade
        AND gcc.cd_componente_curricular = ae.cd_componente_curricular
        AND ae.dt_cancelamento IS NULL
        AND ae.an_atribuicao = te.an_letivo
        AND (ae.cd_motivo_disponibilizacao_externo <> 1
             OR ae.cd_motivo_disponibilizacao_externo IS NULL)
    INNER JOIN contrato_externo ce ON ce.cd_contrato_externo = ae.cd_contrato_externo
    INNER JOIN pessoa pe ON pe.cd_pessoa = ce.cd_pessoa
WHERE te.st_turma_escola IN ('O', 'A', 'C', 'E')
  AND esc.tp_escola IN {_TIPOS_ESCOLA_EXTERNOS}

ORDER BY CodigoTurma, CodigoTerritorioSaber, CodigoExperienciaPedagogica,
         RfProfessor, DataAtribuicao, DataDisponibilizacao
"""
