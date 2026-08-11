# flake8: noqa: E501

_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO = 26
_MOTIVO_DISPONIBILIZACAO_FIM_ANO_LETIVO = 34
_TIPO_UNIDADE_ADMINISTRATIVA_DRE = 24

# Tipos de escola que admitem professor externo:
# CEI_INDIR=11, CRP_CONV=12, EMEFPFOM=32, EMEIPFOM=33
_TIPOS_ESCOLA_EXTERNOS = "(11, 12, 32, 33)"

# Componentes de Território do Saber por código fixo (espelha o legado:
# COMPONENTES_TERRITORIO em QueriesComponenteCurricular). O legado decide
# território por esta lista + atribuicao_aula, usando a grade/território
# (turma_grade_territorio_experiencia) apenas como dado opcional de descrição.
_COMPONENTES_TERRITORIO = (
    "1214, 1215, 1216, 1217, 1218, 1219, 1220, 1221, 1222, 1223, "
    "1519, 1520, 1521, 1522"
)

# Mapeamento componente regência (constante hardcoded)
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
_IDS_REGENCIA_ATRIBUICAO = (*_IDS_REGENCIA, 512, 513)
_PLACEHOLDERS_REGENCIA_ATRIBUICAO = ",".join(
    str(i) for i in _IDS_REGENCIA_ATRIBUICAO
)

# Catálogo de etapas de ensino (EolConnection).
SQL_ETAPA_ENSINO = """
SELECT
    cd_etapa_ensino AS Codigo,
    LTRIM(RTRIM(dc_etapa_ensino)) AS Descricao
FROM etapa_ensino
"""

# Anos letivos disponíveis no EOL (EolConnection)
SQL_ANOS_LETIVOS = """
SELECT DISTINCT an_letivo
FROM turma_escola (NOLOCK)
WHERE st_turma_escola IN ('O', 'A', 'C', 'E')
ORDER BY an_letivo
"""

# Fonte Postgres API EOL → destino pedagogico_db.
# Estas consultas alimentam tabelas estáticas/legadas via full refresh.
SQL_API_EOL_COMPONENTE_CURRICULAR = """
SELECT
    ccp.id,
    cc.idcomponentecurricular,
    cc.ehregencia,
    cc.ehterritorio,
    cc.descricao,
    ccp.idcomponentecurricularpai,
    ccp.vigencia
FROM componentecurricular cc
LEFT JOIN componentecurricularpai ccp
    ON cc.idcomponentecurricular = ccp.idcomponentecurricular
ORDER BY cc.idcomponentecurricular, ccp.id
"""

SQL_API_EOL_COMPONENTE_CURRICULAR_HIERARQUIA = """
SELECT
    id,
    idcomponentecurricularpai,
    idcomponentecurricular,
    vigencia
FROM componentecurricularpai
ORDER BY id
"""

SQL_API_EOL_COMPONENTE_CURRICULAR_PAP = """
SELECT
    id,
    id AS idcomponentecurricular
FROM componentecurricularpap
ORDER BY id
"""

SQL_API_EOL_COMPONENTE_CURRICULAR_PLANEJAMENTO_REGENCIA = """
SELECT
    idcomponentecurricular,
    turno,
    ano
FROM regenciacomponentecurricular
ORDER BY idcomponentecurricular, turno, ano
"""

SQL_API_EOL_TURMA_ITINERARIO_ENSINO_MEDIO = """
SELECT
    id,
    nome,
    serie
FROM turma_tipo_itinerario
ORDER BY id
"""

SQL_API_EOL_AGRUPAMENTO_ATRIBUICAO_TERRITORIO_SABER = """
SELECT
    ROW_NUMBER() OVER (
        ORDER BY
            codagrupamento,
            codturma,
            rfprofessor,
            codterritoriosaber,
            codexperienciapedagogica,
            dtinicioatribuicao,
            codcomponentescurriculares
    ) AS id_linha_api_eol,
    codagrupamento,
    codterritoriosaber,
    codexperienciapedagogica,
    dtinicioatribuicao::timestamp AS dtinicioatribuicao,
    anoatribuicao,
    dtfimatribuicao::timestamp AS dtfimatribuicao,
    dtfimturma::timestamp AS dtfimturma,
    rfprofessor,
    codturma,
    codcomponentescurriculares,
    anoletivo,
    codmotivodisponibilizacao,
    descterritoriosaber,
    descexperienciapedagogica,
    encerramento_atribuicao_agrupamento_atualizado
FROM agrupamentoatribuicaoterritoriosaber
ORDER BY codagrupamento
"""

API_EOL_PEDAGOGICO_TABLE_MAPPINGS = {
    "componente_curricular_api_eol": {
        "source_table": "componentecurricular, componentecurricularpai",
        "target_table": "componente_curricular_api_eol",
        "sql": SQL_API_EOL_COMPONENTE_CURRICULAR,
    },
    "componentecurricularhierarquia": {
        "source_table": "componentecurricularpai",
        "target_table": "componente_curricular_hierarquia",
        "sql": SQL_API_EOL_COMPONENTE_CURRICULAR_HIERARQUIA,
    },
    "componentecurricularpap": {
        "source_table": "componentecurricularpap",
        "target_table": "componente_curricular_pap",
        "sql": SQL_API_EOL_COMPONENTE_CURRICULAR_PAP,
    },
    "componentecurricularplanejamentoregencia": {
        "source_table": "regenciacomponentecurricular",
        "target_table": "componente_curricular_planejamento_regencia",
        "sql": SQL_API_EOL_COMPONENTE_CURRICULAR_PLANEJAMENTO_REGENCIA,
    },
    "turmaitinerarioensinomedio": {
        "source_table": "turma_tipo_itinerario",
        "target_table": "turma_itinerario_ensino_medio",
        "sql": SQL_API_EOL_TURMA_ITINERARIO_ENSINO_MEDIO,
    },
    "agrupamento_atribuicao_territorio_saber": {
        "source_table": "agrupamentoatribuicaoterritoriosaber",
        "target_table": "agrupamento_atribuicao_territorio_saber",
        "sql": SQL_API_EOL_AGRUPAMENTO_ATRIBUICAO_TERRITORIO_SABER,
    },
}

# Fase 2 — Estrutura turma × componente (sem professor).
# Uma linha por (turma_codigo, componente_codigo).
# Mantém apenas o vínculo e o código de território do saber, quando existir.
# Dois branches (UNION ALL — mutuamente exclusivos):
#   Branch 1: turmas com série (via serie_turma_escola)
#   Branch 2: turmas de programa (via turma_escola_grade_programa)
#
# codigo_componente_territorio_saber e descrições resolvidos pela grade de
# Território do Saber.
SQL_COMPONENTE_TURMA = """
WITH cte_territorio AS (
    SELECT
        tgt.cd_componente_curricular,
        ter.dc_territorio_saber,
        exp.dc_experiencia_pedagogica,
        ROW_NUMBER() OVER (
            PARTITION BY tgt.cd_componente_curricular
            ORDER BY tgt.cd_territorio_saber, tgt.cd_experiencia_pedagogica
        ) AS rn
    FROM turma_grade_territorio_experiencia (NOLOCK) tgt
    INNER JOIN território_saber (NOLOCK) ter
        ON ter.cd_territorio_saber = tgt.cd_territorio_saber
    INNER JOIN tipo_experiencia_pedagogica (NOLOCK) exp
        ON exp.cd_experiencia_pedagogica = tgt.cd_experiencia_pedagogica
    WHERE tgt.cd_territorio_saber <> 1
)
SELECT DISTINCT
    te.cd_turma_escola                                                                  AS turma_codigo,
    cc.cd_componente_curricular                                                         AS componente_codigo,
    CASE
        WHEN ter_existe.cd_territorio_saber IS NULL THEN NULL
        WHEN cc.cd_componente_curricular IN (1214, 1215, 1216, 1217, 1218, 1219, 1220, 1221, 1222, 1223, 1519, 1520, 1521, 1522) THEN cc.cd_componente_curricular
        ELSE tgt.cd_componente_curricular
    END AS codigo_componente_territorio_saber,
    ter.dc_territorio_saber                                                             AS desc_territorio_saber,
    exp.dc_experiencia_pedagogica                                                       AS desc_experiencia_pedagogica,
    esc.tp_escola                                                                        AS tipo_escola
FROM turma_escola (NOLOCK) te
INNER JOIN escola (NOLOCK) esc ON esc.cd_escola = te.cd_escola
INNER JOIN serie_turma_escola (NOLOCK) ste ON ste.cd_turma_escola = te.cd_turma_escola
INNER JOIN serie_turma_grade (NOLOCK) stg
    ON stg.cd_turma_escola = ste.cd_turma_escola AND stg.dt_fim IS NULL
INNER JOIN escola_grade (NOLOCK) eg     ON eg.cd_escola_grade = stg.cd_escola_grade
INNER JOIN grade (NOLOCK) g             ON g.cd_grade = eg.cd_grade
INNER JOIN grade_componente_curricular (NOLOCK) gcc ON gcc.cd_grade = g.cd_grade
INNER JOIN componente_curricular (NOLOCK) cc
    ON cc.cd_componente_curricular = gcc.cd_componente_curricular AND cc.dt_cancelamento IS NULL
LEFT JOIN turma_grade_territorio_experiencia (NOLOCK) tgt
    ON tgt.cd_serie_grade = stg.cd_serie_grade
   AND tgt.cd_componente_curricular = cc.cd_componente_curricular
LEFT JOIN território_saber (NOLOCK) ter_existe
    ON ter_existe.cd_territorio_saber = tgt.cd_territorio_saber
LEFT JOIN território_saber (NOLOCK) ter
    ON ter.cd_territorio_saber = tgt.cd_territorio_saber
   AND tgt.cd_territorio_saber <> 1
LEFT JOIN tipo_experiencia_pedagogica (NOLOCK) exp
    ON exp.cd_experiencia_pedagogica = tgt.cd_experiencia_pedagogica
   AND tgt.cd_territorio_saber <> 1
WHERE te.an_letivo = ?
  AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
UNION ALL
-- Turmas de programa
SELECT DISTINCT
    te.cd_turma_escola,
    cc.cd_componente_curricular,
    CASE
        WHEN tgt.cd_componente_curricular IS NULL THEN NULL
        WHEN cc.cd_componente_curricular IN (1214, 1215, 1216, 1217, 1218, 1219, 1220, 1221, 1222, 1223, 1519, 1520, 1521, 1522) THEN cc.cd_componente_curricular
        ELSE tgt.cd_componente_curricular
    END,
    tgt.dc_territorio_saber,
    tgt.dc_experiencia_pedagogica,
    esc.tp_escola                                                                        AS tipo_escola
FROM turma_escola (NOLOCK) te
INNER JOIN escola (NOLOCK) esc ON esc.cd_escola = te.cd_escola
INNER JOIN turma_escola_grade_programa (NOLOCK) tegp
    ON tegp.cd_turma_escola = te.cd_turma_escola AND tegp.dt_fim IS NULL
INNER JOIN escola_grade (NOLOCK) teg    ON teg.cd_escola_grade = tegp.cd_escola_grade
INNER JOIN grade (NOLOCK) pg            ON pg.cd_grade = teg.cd_grade
INNER JOIN grade_componente_curricular (NOLOCK) pgcc ON pgcc.cd_grade = teg.cd_grade
INNER JOIN componente_curricular (NOLOCK) cc
    ON pgcc.cd_componente_curricular = cc.cd_componente_curricular AND cc.dt_cancelamento IS NULL
LEFT JOIN cte_territorio tgt
    ON tgt.cd_componente_curricular = cc.cd_componente_curricular
   AND tgt.rn = 1
WHERE te.an_letivo = ?
  AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
"""

# Fase 3 — Atribuições professor × turma × componente.
# UNION ALL de 7 branches: SME por série, SME por programa (explícito + por
# escola_grade), externo por série, externo por programa, SME liberado e
# externo liberado. Dedup final por ROW_NUMBER (1 linha por PK).
# Uma linha por (turma_codigo, componente_codigo, professor).
SQL_ATRIBUICAO_COMPONENTE = f"""
WITH atribuicoes AS (
-- Branch 1: SME ativo (grade + serie_grade → turma via série)
SELECT
    ste.cd_turma_escola                 AS turma_codigo,
    aa.cd_componente_curricular         AS componente_codigo,
    vsc.cd_registro_funcional           AS professor,
    0                                   AS atribuicao_externa,
    aa.an_atribuicao                    AS ano_letivo,
    aa.cd_atribuicao_aula               AS id_atribuicao_origem,
    aa.dt_atribuicao_aula               AS dt_atribuicao,
    aa.dt_cancelamento                  AS dt_cancelamento,
    aa.dt_disponibilizacao_aulas        AS dt_disponibilizacao,
    aa.cd_motivo_disponibilizacao       AS cd_motivo_disponibilizacao
FROM atribuicao_aula (NOLOCK) aa
INNER JOIN v_cargo_base_cotic (NOLOCK) vcbc ON vcbc.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
INNER JOIN v_servidor_cotic (NOLOCK) vsc    ON vsc.cd_servidor = vcbc.cd_servidor
INNER JOIN componente_curricular (NOLOCK) cc
    ON cc.cd_componente_curricular = aa.cd_componente_curricular AND cc.dt_cancelamento IS NULL
INNER JOIN escola_grade (NOLOCK) eg         ON eg.cd_grade = aa.cd_grade
INNER JOIN serie_turma_grade (NOLOCK) stg
    ON stg.cd_escola_grade = eg.cd_escola_grade AND stg.cd_serie_grade = aa.cd_serie_grade AND stg.dt_fim IS NULL
INNER JOIN serie_turma_escola (NOLOCK) ste  ON ste.cd_turma_escola = stg.cd_turma_escola
INNER JOIN turma_escola (NOLOCK) te
    ON te.cd_turma_escola = ste.cd_turma_escola
    AND te.an_letivo = aa.an_atribuicao
    AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
WHERE aa.an_atribuicao = ?
  AND aa.dt_cancelamento IS NULL
  AND (aa.cd_motivo_disponibilizacao <> {_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO}
       OR aa.cd_motivo_disponibilizacao IS NULL)
  AND (aa.dt_disponibilizacao_aulas >= DATEFROMPARTS(aa.an_atribuicao, 2, 5)
       OR aa.dt_disponibilizacao_aulas IS NULL
       OR aa.cd_motivo_disponibilizacao = {_MOTIVO_DISPONIBILIZACAO_FIM_ANO_LETIVO}
       OR aa.cd_componente_curricular IN ({_PLACEHOLDERS_REGENCIA_ATRIBUICAO}))
UNION ALL
-- Branch 1b: SME regência por série, espelha BuscarDisciplinasRegenciaProfessor
SELECT
    te.cd_turma_escola                  AS turma_codigo,
    aa.cd_componente_curricular         AS componente_codigo,
    vsc.cd_registro_funcional           AS professor,
    0                                   AS atribuicao_externa,
    aa.an_atribuicao                    AS ano_letivo,
    aa.cd_atribuicao_aula               AS id_atribuicao_origem,
    aa.dt_atribuicao_aula               AS dt_atribuicao,
    aa.dt_cancelamento                  AS dt_cancelamento,
    aa.dt_disponibilizacao_aulas        AS dt_disponibilizacao,
    aa.cd_motivo_disponibilizacao       AS cd_motivo_disponibilizacao
FROM turma_escola (NOLOCK) te
INNER JOIN escola (NOLOCK) esc
    ON te.cd_escola = esc.cd_escola
INNER JOIN serie_turma_escola (NOLOCK) ste
    ON ste.cd_turma_escola = te.cd_turma_escola
INNER JOIN serie_turma_grade (NOLOCK) stg
    ON stg.cd_turma_escola = ste.cd_turma_escola
INNER JOIN escola_grade (NOLOCK) eg
    ON stg.cd_escola_grade = eg.cd_escola_grade
INNER JOIN grade (NOLOCK) g
    ON eg.cd_grade = g.cd_grade
INNER JOIN serie_ensino (NOLOCK) se
    ON g.cd_serie_ensino = se.cd_serie_ensino
INNER JOIN atribuicao_aula (NOLOCK) aa
    ON g.cd_grade = aa.cd_grade
   AND aa.an_atribuicao = te.an_letivo
   AND aa.cd_unidade_educacao = te.cd_escola
   AND aa.cd_serie_grade = stg.cd_serie_grade
INNER JOIN componente_curricular (NOLOCK) cc
    ON cc.cd_componente_curricular = aa.cd_componente_curricular
INNER JOIN v_cargo_base_cotic (NOLOCK) vcbc
    ON vcbc.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
INNER JOIN v_servidor_cotic (NOLOCK) vsc
    ON vsc.cd_servidor = vcbc.cd_servidor
INNER JOIN cargo (NOLOCK) c
    ON vcbc.cd_cargo = c.cd_cargo
INNER JOIN v_cadastro_unidade_educacao (NOLOCK) escola
    ON escola.cd_unidade_educacao = te.cd_escola
INNER JOIN v_cadastro_unidade_educacao (NOLOCK) dre
    ON dre.cd_unidade_educacao =
       escola.cd_unidade_administrativa_referencia
INNER JOIN unidade_administrativa (NOLOCK) ua
    ON escola.cd_unidade_administrativa_referencia =
       ua.cd_unidade_administrativa
   AND ua.tp_unidade_administrativa = {_TIPO_UNIDADE_ADMINISTRATIVA_DRE}
INNER JOIN etapa_ensino (NOLOCK) ee
    ON se.cd_etapa_ensino = ee.cd_etapa_ensino
INNER JOIN tipo_unidade_educacao (NOLOCK) tue
    ON dre.tp_unidade_educacao = tue.tp_unidade_educacao
INNER JOIN tipo_escola (NOLOCK) tes
    ON esc.tp_escola = tes.tp_escola
LEFT JOIN funcao_atividade_cargo_servidor (NOLOCK) facs
    ON vcbc.cd_cargo_base_servidor = facs.cd_cargo_base_servidor
   AND facs.dt_fim_funcao_atividade IS NULL
WHERE aa.an_atribuicao = ?
  AND aa.dt_cancelamento IS NULL
  AND cc.dt_cancelamento IS NULL
  AND te.st_turma_escola IN ('A', 'O', 'C')
  AND aa.cd_componente_curricular IN ({_PLACEHOLDERS_REGENCIA_ATRIBUICAO})
UNION ALL
-- Branch 2a: SME ativo via programa EXPLÍCITO (cd_turma_escola_grade_programa preenchido)
SELECT
    te.cd_turma_escola, aa.cd_componente_curricular, vsc.cd_registro_funcional, 0, aa.an_atribuicao,
    aa.cd_atribuicao_aula, aa.dt_atribuicao_aula, aa.dt_cancelamento, aa.dt_disponibilizacao_aulas, aa.cd_motivo_disponibilizacao
FROM atribuicao_aula (NOLOCK) aa
INNER JOIN v_cargo_base_cotic (NOLOCK) vcbc ON vcbc.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
INNER JOIN v_servidor_cotic (NOLOCK) vsc    ON vsc.cd_servidor = vcbc.cd_servidor
INNER JOIN componente_curricular (NOLOCK) cc
    ON cc.cd_componente_curricular = aa.cd_componente_curricular AND cc.dt_cancelamento IS NULL
INNER JOIN escola_grade (NOLOCK) eg         ON eg.cd_grade = aa.cd_grade
INNER JOIN grade_componente_curricular (NOLOCK) gcc
    ON gcc.cd_grade = eg.cd_grade AND gcc.cd_componente_curricular = aa.cd_componente_curricular
INNER JOIN turma_escola_grade_programa (NOLOCK) tegp
    ON tegp.cd_turma_escola_grade_programa = aa.cd_turma_escola_grade_programa
INNER JOIN turma_escola (NOLOCK) te
    ON te.cd_turma_escola = tegp.cd_turma_escola
    AND te.cd_escola = aa.cd_unidade_educacao
    AND te.an_letivo = aa.an_atribuicao
    AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
WHERE aa.an_atribuicao = ?
  AND aa.cd_turma_escola_grade_programa IS NOT NULL
  AND aa.dt_cancelamento IS NULL
  AND (aa.cd_motivo_disponibilizacao <> {_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO}
       OR aa.cd_motivo_disponibilizacao IS NULL)
  AND (aa.dt_disponibilizacao_aulas >= DATEFROMPARTS(aa.an_atribuicao, 2, 5)
       OR aa.dt_disponibilizacao_aulas IS NULL
       OR aa.cd_motivo_disponibilizacao = {_MOTIVO_DISPONIBILIZACAO_FIM_ANO_LETIVO}
       OR aa.cd_componente_curricular IN ({_PLACEHOLDERS_REGENCIA_ATRIBUICAO}))
UNION ALL
-- Branch 2b: SME ativo via programa por ESCOLA_GRADE (cd_turma_escola_grade_programa nulo)
SELECT
    te.cd_turma_escola, aa.cd_componente_curricular, vsc.cd_registro_funcional, 0, aa.an_atribuicao,
    aa.cd_atribuicao_aula, aa.dt_atribuicao_aula, aa.dt_cancelamento, aa.dt_disponibilizacao_aulas, aa.cd_motivo_disponibilizacao
FROM atribuicao_aula (NOLOCK) aa
INNER JOIN v_cargo_base_cotic (NOLOCK) vcbc ON vcbc.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
INNER JOIN v_servidor_cotic (NOLOCK) vsc    ON vsc.cd_servidor = vcbc.cd_servidor
INNER JOIN componente_curricular (NOLOCK) cc
    ON cc.cd_componente_curricular = aa.cd_componente_curricular AND cc.dt_cancelamento IS NULL
INNER JOIN escola_grade (NOLOCK) eg         ON eg.cd_grade = aa.cd_grade
INNER JOIN grade_componente_curricular (NOLOCK) gcc
    ON gcc.cd_grade = eg.cd_grade AND gcc.cd_componente_curricular = aa.cd_componente_curricular
INNER JOIN turma_escola_grade_programa (NOLOCK) tegp
    ON tegp.cd_escola_grade = eg.cd_escola_grade
INNER JOIN turma_escola (NOLOCK) te
    ON te.cd_turma_escola = tegp.cd_turma_escola
    AND te.cd_escola = aa.cd_unidade_educacao
    AND te.an_letivo = aa.an_atribuicao
    AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
WHERE aa.an_atribuicao = ?
  AND aa.cd_turma_escola_grade_programa IS NULL
  AND aa.dt_cancelamento IS NULL
  AND (aa.cd_motivo_disponibilizacao <> {_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO}
       OR aa.cd_motivo_disponibilizacao IS NULL)
  AND (aa.dt_disponibilizacao_aulas >= DATEFROMPARTS(aa.an_atribuicao, 2, 5)
       OR aa.dt_disponibilizacao_aulas IS NULL
       OR aa.cd_motivo_disponibilizacao = {_MOTIVO_DISPONIBILIZACAO_FIM_ANO_LETIVO}
       OR aa.cd_componente_curricular IN ({_PLACEHOLDERS_REGENCIA_ATRIBUICAO}))
UNION ALL
-- Branch 3: EXT ativo (grade → turma via série)
SELECT
    ste.cd_turma_escola, ae.cd_componente_curricular, pe.cd_cpf_pessoa, 1, ae.an_atribuicao,
    ae.cd_atribuicao_externo, ae.dt_atribuicao, ae.dt_cancelamento, ae.dt_disponibilizacao, ae.cd_motivo_disponibilizacao_externo
FROM atribuicao_externo (NOLOCK) ae
INNER JOIN contrato_externo (NOLOCK) ce     ON ce.cd_contrato_externo = ae.cd_contrato_externo
INNER JOIN pessoa (NOLOCK) pe               ON pe.cd_pessoa = ce.cd_pessoa
INNER JOIN componente_curricular (NOLOCK) cc
    ON cc.cd_componente_curricular = ae.cd_componente_curricular AND cc.dt_cancelamento IS NULL
INNER JOIN escola (NOLOCK) esc
    ON esc.cd_escola = ae.cd_unidade_educacao AND esc.tp_escola IN {_TIPOS_ESCOLA_EXTERNOS}
INNER JOIN escola_grade (NOLOCK) eg         ON eg.cd_grade = ae.cd_grade
INNER JOIN serie_turma_grade (NOLOCK) stg
    ON stg.cd_escola_grade = eg.cd_escola_grade AND stg.dt_fim IS NULL
INNER JOIN serie_turma_escola (NOLOCK) ste  ON ste.cd_turma_escola = stg.cd_turma_escola
INNER JOIN turma_escola (NOLOCK) te
    ON te.cd_turma_escola = ste.cd_turma_escola
    AND te.cd_escola = ae.cd_unidade_educacao
    AND te.an_letivo = ae.an_atribuicao
    AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
WHERE ae.an_atribuicao = ?
  AND ae.dt_cancelamento IS NULL
  AND (ae.cd_motivo_disponibilizacao_externo <> 1
       OR ae.cd_motivo_disponibilizacao_externo IS NULL)
  AND (ae.dt_disponibilizacao >= DATEFROMPARTS(ae.an_atribuicao, 2, 5)
       OR ae.dt_disponibilizacao IS NULL
       OR ae.cd_motivo_disponibilizacao_externo = 3)
UNION ALL
-- Branch 4: EXT ativo (turma de programa)
SELECT
    te.cd_turma_escola, ae.cd_componente_curricular, pe.cd_cpf_pessoa, 1, ae.an_atribuicao,
    ae.cd_atribuicao_externo, ae.dt_atribuicao, ae.dt_cancelamento, ae.dt_disponibilizacao, ae.cd_motivo_disponibilizacao_externo
FROM atribuicao_externo (NOLOCK) ae
INNER JOIN contrato_externo (NOLOCK) ce     ON ce.cd_contrato_externo = ae.cd_contrato_externo
INNER JOIN pessoa (NOLOCK) pe               ON pe.cd_pessoa = ce.cd_pessoa
INNER JOIN componente_curricular (NOLOCK) cc
    ON cc.cd_componente_curricular = ae.cd_componente_curricular AND cc.dt_cancelamento IS NULL
INNER JOIN escola (NOLOCK) esc
    ON esc.cd_escola = ae.cd_unidade_educacao AND esc.tp_escola IN {_TIPOS_ESCOLA_EXTERNOS}
INNER JOIN turma_escola_grade_programa (NOLOCK) tegp
    ON tegp.cd_turma_escola_grade_programa = ae.cd_turma_escola_grade_programa
INNER JOIN turma_escola (NOLOCK) te
    ON te.cd_turma_escola = tegp.cd_turma_escola
    AND te.cd_escola = ae.cd_unidade_educacao
    AND te.an_letivo = ae.an_atribuicao
    AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
WHERE ae.an_atribuicao = ?
  AND ae.dt_cancelamento IS NULL
  AND (ae.cd_motivo_disponibilizacao_externo <> 1
       OR ae.cd_motivo_disponibilizacao_externo IS NULL)
  AND (ae.dt_disponibilizacao >= DATEFROMPARTS(ae.an_atribuicao, 2, 5)
       OR ae.dt_disponibilizacao IS NULL
       OR ae.cd_motivo_disponibilizacao_externo = 3)
UNION ALL
-- Branch 5: SME liberado (escola + grade → turmas)
SELECT
    te.cd_turma_escola, aa.cd_componente_curricular, vsc.cd_registro_funcional, 0, aa.an_atribuicao,
    aa.cd_atribuicao_aula, aa.dt_atribuicao_aula, aa.dt_cancelamento, aa.dt_disponibilizacao_aulas, aa.cd_motivo_disponibilizacao
FROM atribuicao_aula (NOLOCK) aa
INNER JOIN v_cargo_base_cotic (NOLOCK) vcbc ON vcbc.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
INNER JOIN v_servidor_cotic (NOLOCK) vsc    ON vsc.cd_servidor = vcbc.cd_servidor
INNER JOIN componente_curricular (NOLOCK) cc
    ON cc.cd_componente_curricular = aa.cd_componente_curricular AND cc.dt_cancelamento IS NULL
INNER JOIN turma_escola (NOLOCK) te
    ON te.cd_escola = aa.cd_unidade_educacao
    AND te.an_letivo = aa.an_atribuicao
    AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
INNER JOIN serie_turma_escola (NOLOCK) ste  ON ste.cd_turma_escola = te.cd_turma_escola
INNER JOIN serie_turma_grade (NOLOCK) stg
    ON stg.cd_turma_escola = ste.cd_turma_escola AND stg.dt_fim IS NULL
INNER JOIN escola_grade (NOLOCK) eg
    ON eg.cd_escola_grade = stg.cd_escola_grade AND eg.cd_grade = aa.cd_grade
WHERE aa.an_atribuicao = ?
  AND aa.dt_disponibilizacao_aulas IS NOT NULL
  AND aa.dt_cancelamento IS NULL
  AND aa.cd_motivo_disponibilizacao <> {_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO}
  AND (aa.cd_motivo_disponibilizacao = {_MOTIVO_DISPONIBILIZACAO_FIM_ANO_LETIVO}
       OR aa.cd_motivo_disponibilizacao IS NULL)
  AND (
       aa.dt_disponibilizacao_aulas >= DATEFROMPARTS(aa.an_atribuicao, 2, 5)
       OR aa.cd_componente_curricular IN ({_PLACEHOLDERS_REGENCIA_ATRIBUICAO})
      )
UNION ALL
-- Branch 6: externo liberado (escola + grade → turmas)
SELECT
    te.cd_turma_escola, ae.cd_componente_curricular, pe.cd_cpf_pessoa, 1, ae.an_atribuicao,
    ae.cd_atribuicao_externo, ae.dt_atribuicao, ae.dt_cancelamento, ae.dt_disponibilizacao, ae.cd_motivo_disponibilizacao_externo
FROM atribuicao_externo (NOLOCK) ae
INNER JOIN contrato_externo (NOLOCK) ce     ON ce.cd_contrato_externo = ae.cd_contrato_externo
INNER JOIN pessoa (NOLOCK) pe               ON pe.cd_pessoa = ce.cd_pessoa
INNER JOIN componente_curricular (NOLOCK) cc
    ON cc.cd_componente_curricular = ae.cd_componente_curricular AND cc.dt_cancelamento IS NULL
INNER JOIN escola (NOLOCK) esc
    ON esc.cd_escola = ae.cd_unidade_educacao AND esc.tp_escola IN {_TIPOS_ESCOLA_EXTERNOS}
INNER JOIN turma_escola (NOLOCK) te
    ON te.cd_escola = ae.cd_unidade_educacao
    AND te.an_letivo = ae.an_atribuicao
    AND te.st_turma_escola IN ('O', 'A', 'C', 'E')
INNER JOIN serie_turma_escola (NOLOCK) ste  ON ste.cd_turma_escola = te.cd_turma_escola
INNER JOIN serie_turma_grade (NOLOCK) stg
    ON stg.cd_turma_escola = ste.cd_turma_escola AND stg.dt_fim IS NULL
INNER JOIN escola_grade (NOLOCK) eg
    ON eg.cd_escola_grade = stg.cd_escola_grade AND eg.cd_grade = ae.cd_grade
WHERE ae.an_atribuicao = ?
  AND ae.dt_disponibilizacao IS NOT NULL
  AND ae.dt_cancelamento IS NULL
  AND ae.cd_motivo_disponibilizacao_externo <> 1
  AND (ae.cd_motivo_disponibilizacao_externo = 3
       OR ae.cd_motivo_disponibilizacao_externo IS NULL)
  AND ae.dt_disponibilizacao >= DATEFROMPARTS(ae.an_atribuicao, 2, 5)
),
atribuicoes_ordenadas AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY turma_codigo, componente_codigo, professor
            ORDER BY
                CASE WHEN dt_disponibilizacao IS NULL THEN 0 ELSE 1 END,
                dt_atribuicao DESC,
                id_atribuicao_origem DESC
        ) AS ordem_atribuicao
    FROM atribuicoes
)
SELECT
    turma_codigo, componente_codigo, professor, atribuicao_externa, ano_letivo,
    id_atribuicao_origem, dt_atribuicao, dt_cancelamento, dt_disponibilizacao, cd_motivo_disponibilizacao
FROM atribuicoes_ordenadas
WHERE ordem_atribuicao = 1
OPTION (HASH JOIN)
"""

# Alimenta: turma
# Parâmetros (?):
#   1 — an_letivo
#
# Campos computados na query (não em Python):
#   Ano            — primeiro char de dc_turma_escola se numérico, senão '0'
#   Extinta        — st_turma_escola = 'E'
#   Modalidade     — descrição textual via cd_etapa_ensino
#   CodigoModalidade — inteiro por etapa/tipo escola
#   Semestre       — EJA: 1 ou 2 conforme mês de dt_inicio_turma; demais: 0
#   EnsinoEspecial — cd_etapa_ensino=13 AND cd_modalidade_ensino=2
SQL_TURMAS = """
SELECT DISTINCT
    tur.cd_turma_escola                                                        AS Codigo,
    tur.an_letivo                                                              AS AnoLetivo,
    CASE
        WHEN SUBSTRING(tur.dc_turma_escola, 1, 1) LIKE '%[0-9]%'
            THEN SUBSTRING(tur.dc_turma_escola, 1, 1)
        ELSE '0'
    END                                                                        AS Ano,
    tur.cd_tipo_turma                                                          AS TipoTurma,
    tur.dc_turma_escola                                                        AS NomeTurma,
    dtt.qt_hora_duracao                                                        AS DuracaoTurno,
    tur.cd_tipo_turno                                                          AS TipoTurno,
    tur.dt_inicio_turma                                                        AS DataInicioTurma,
    tur.dt_fim                                                                 AS DataFim,
    CASE WHEN tur.st_turma_escola = 'E' THEN 1 ELSE 0 END                     AS Extinta,
    tur.st_turma_escola                                                        AS Situacao,
    tur.cd_escola                                                              AS UeCodigo,
    tur.dt_atualizacao_tabela                                                  AS DataAtualizacao,
    tur.dt_status_turma_escola                                                 AS DataStatusTurmaEscola,
    se.dc_serie_ensino                                                         AS SerieEnsino,
    se.cd_serie_ensino                                                         AS CodigoSerieEnsino,
    CASE
        WHEN ee.cd_etapa_ensino IN (2, 3, 7, 11)     THEN 'EJA'
        WHEN ee.cd_etapa_ensino IN (4, 5, 12, 13)    THEN 'Fundamental'
        WHEN ee.cd_etapa_ensino IN (6, 7, 8, 9, 14, 17) THEN 'Médio'
        WHEN ee.cd_etapa_ensino IN (1, 10)            THEN 'Infantil'
        ELSE NULL
    END                                                                        AS Modalidade,
    CASE
        WHEN ee.cd_etapa_ensino IN (1, 10)
            OR (tur.cd_tipo_turma <> 1 AND esc.tp_escola IN (10,11,12,14,15,18,26))
            OR (tur.cd_tipo_turma <> 1 AND esc.tp_escola IN (2,17,28,30,31))  THEN 1
        WHEN ee.cd_etapa_ensino IN (2, 3, 7, 11)                              THEN 3
        WHEN ee.cd_etapa_ensino IN (4, 5, 12, 13)                             THEN 5
        WHEN tur.cd_tipo_turma = 3 AND esc.tp_escola IN(1, 3, 4, 16) 		  THEN 5
        WHEN ee.cd_etapa_ensino IN (6, 7, 8, 9, 14, 17)                      THEN 6
        WHEN tur.cd_tipo_turma = 7                                            THEN 6
        WHEN esc.tp_escola = 13                                               THEN 4
        ELSE 0
    END                                                                        AS CodigoModalidade,
    tur.cd_tipo_programa                                                       AS CodigoTipoPrograma,
    CASE
        WHEN COALESCE(ee.cd_etapa_ensino, prog_etapa.cd_etapa_ensino_prog) IN (1, 10)           THEN 1
        WHEN COALESCE(ee.cd_etapa_ensino, prog_etapa.cd_etapa_ensino_prog) IN (2, 3, 7, 11)     THEN 3
        WHEN esc.tp_escola = 13                                                                  THEN 4
        WHEN COALESCE(ee.cd_etapa_ensino, prog_etapa.cd_etapa_ensino_prog) IN (4, 5, 12, 13)    THEN 5
        WHEN COALESCE(ee.cd_etapa_ensino, prog_etapa.cd_etapa_ensino_prog) IN (6, 7, 8, 9, 14, 17) THEN 6
        ELSE 0
    END                                                                        AS CodigoModalidadeEtapa,
    CASE
        WHEN ee.cd_etapa_ensino IN (2, 3, 7, 11)
            THEN IIF(DATEPART(MONTH, tur.dt_inicio_turma) > 6, 2, 1)
        ELSE 0
    END                                                                        AS Semestre,
    IIF((se.cd_etapa_ensino = 13) AND (se.cd_modalidade_ensino = 2), 1, 0)    AS EnsinoEspecial,
    ee.cd_etapa_ensino                                                         AS CodigoEtapaEnsino,
    se.cd_ciclo_ensino                                                         AS CodigoCicloEnsino,
    esc.tp_escola                                                              AS TipoEscola,
    tur_prog_grade.cd_grade                                                    AS CodigoGradePrograma,
    tur_prog_grade.dc_grade                                                    AS DescricaoGradePrograma,
    tur_prog_grade.cd_tipo_grade                                               AS TipoGradePrograma,
    tur.cd_tipo_periodicidade                                                  AS CodigoTipoPeriodicidade
FROM turma_escola (NOLOCK) tur
INNER JOIN escola (NOLOCK) esc
    ON esc.cd_escola = tur.cd_escola
LEFT JOIN serie_turma_escola (NOLOCK) ste
    ON ste.cd_turma_escola = tur.cd_turma_escola AND ste.dt_fim IS NULL
LEFT JOIN serie_ensino (NOLOCK) se
    ON se.cd_serie_ensino = ste.cd_serie_ensino
LEFT JOIN etapa_ensino (NOLOCK) ee
    ON ee.cd_etapa_ensino = se.cd_etapa_ensino
LEFT JOIN duracao_tipo_turno dtt
    ON tur.cd_tipo_turno = dtt.cd_tipo_turno
    AND tur.cd_duracao = dtt.cd_duracao
LEFT JOIN (
    SELECT tegp.cd_turma_escola,
           MIN(se_p.cd_etapa_ensino) AS cd_etapa_ensino_prog
    FROM turma_escola_grade_programa (NOLOCK) tegp
    INNER JOIN escola_grade (NOLOCK) eg_p ON eg_p.cd_escola_grade = tegp.cd_escola_grade
    INNER JOIN grade (NOLOCK) gr_p        ON gr_p.cd_grade = eg_p.cd_grade
    INNER JOIN serie_ensino (NOLOCK) se_p ON se_p.cd_serie_ensino = gr_p.cd_serie_ensino
    GROUP BY tegp.cd_turma_escola
) prog_etapa ON prog_etapa.cd_turma_escola = tur.cd_turma_escola
LEFT JOIN (
    SELECT tur.cd_turma_escola,
           g.dc_grade,
           g.cd_grade,
           g.cd_tipo_grade
    FROM turma_escola (NOLOCK) tur
    LEFT JOIN serie_turma_escola(nolock) ste
        ON ste.cd_turma_escola = tur.cd_turma_escola
    LEFT JOIN serie_turma_grade(nolock) stg
        ON stg.cd_turma_escola = ste.cd_turma_escola and stg.dt_fim is null
    LEFT JOIN turma_escola_grade_programa(nolock) tegp
        ON tegp.cd_turma_escola = tur.cd_turma_escola and tegp.dt_fim is null
    LEFT JOIN escola_grade (NOLOCK) eg_p
        ON eg_p.cd_escola_grade = COALESCE(stg.cd_escola_grade, tegp.cd_escola_grade)
    LEFT JOIN grade (NOLOCK) g ON g.cd_grade = eg_p.cd_grade
    GROUP BY tur.cd_turma_escola, g.dc_grade, g.cd_grade, g.cd_tipo_grade
) tur_prog_grade ON tur_prog_grade.cd_turma_escola = tur.cd_turma_escola
WHERE tur.an_letivo = ?
  AND tur.st_turma_escola IN ('O', 'A', 'E', 'C')
"""

# Alimenta: turma_atribuida_dre_ue
# Parâmetros (?):
#   1 — AnoLetivo
SQL_TURMAS_ATRIBUIDAS_DRE_UE = """
SELECT
    CodEscola       AS CodigoEscola,
    CodTurma        AS CodigoTurma,
    AnoLetivo       AS AnoLetivo,
    Modalidade      AS Modalidade,
    Semestre        AS Semestre,
    CodModalidade   AS CodigoModalidade,
    CodDre          AS CodigoDre,
    Dre             AS Dre,
    DreAbrev        AS DreAbreviacao,
    UE              AS Ue,
    UEAbrev         AS UeAbreviacao,
    NomeTurma       AS NomeTurma,
    Ano             AS Ano,
    TipoUE          AS TipoUe,
    CodTipoUE       AS CodigoTipoUe,
    CodTipoEscola   AS CodigoTipoEscola,
    TipoEscola      AS TipoEscola,
    DuracaoTurno    AS DuracaoTurno,
    TipoTurno       AS TipoTurno
FROM turmas_atribuidas_dre_ue WITH (NOLOCK)
WHERE AnoLetivo = ?
"""

SQL_COMPONENTES_NAO_CANCELADOS = f"""
SELECT
    cd_componente_curricular              AS Codigo,
    RTRIM(LTRIM(dc_componente_curricular)) AS Descricao,
    CASE WHEN cd_componente_curricular IN ({_PLACEHOLDERS_REGENCIA}) THEN 1 ELSE 0 END AS Regencia
FROM componente_curricular
WHERE dt_cancelamento IS NULL
"""


# Alimenta: grade_componente_curricular
# Parâmetros (?):
#   1 — ano_letivo
SQL_GRADE_COMPONENTE_CURRICULAR = f"""
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
            WHEN eten.cd_etapa_ensino IN (1, 10)              THEN 1  -- EI
            WHEN eten.cd_etapa_ensino IN (2, 3, 7, 11)        THEN 3  -- EJA
            WHEN esc.tp_escola = 13                            THEN 4  -- CIEJA
            WHEN eten.cd_etapa_ensino IN (4, 5, 12, 13)       THEN 5  -- EF
            WHEN eten.cd_etapa_ensino IN (6, 7, 8, 9, 14, 17) THEN 6  -- EM
        END                                                              AS Modalidade,
        te.an_letivo                                                     AS AnoLetivo
    FROM turma_escola te
        INNER JOIN escola esc ON te.cd_escola = esc.cd_escola
        INNER JOIN v_cadastro_unidade_educacao ue ON ue.cd_unidade_educacao = esc.cd_escola
        INNER JOIN unidade_administrativa dre
            ON dre.tp_unidade_administrativa = {_TIPO_UNIDADE_ADMINISTRATIVA_DRE}
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
        LEFT JOIN etapa_ensino eten ON serie_ensino.cd_etapa_ensino = eten.cd_etapa_ensino
        -- Programa
        LEFT JOIN turma_escola_grade_programa tegp ON tegp.cd_turma_escola = te.cd_turma_escola
        LEFT JOIN escola_grade teg ON teg.cd_escola_grade = tegp.cd_escola_grade
        LEFT JOIN grade_componente_curricular pgcc ON pgcc.cd_grade = teg.cd_grade
        LEFT JOIN componente_curricular pcc
            ON pgcc.cd_componente_curricular = pcc.cd_componente_curricular
            AND pcc.dt_cancelamento IS NULL
    WHERE te.st_turma_escola IN ('O', 'A', 'C')
      AND te.an_letivo = ?  -- param: ano_letivo
      AND serie_ensino.sg_resumida_serie IS NOT NULL
      AND serie_ensino.cd_serie_ensino IS NOT NULL
)
SELECT *
FROM componentesAnoTurmas
WHERE Modalidade > 0
"""

# Alimenta: agrupamento_atribuicao_territorio_saber
# e componente_curricular_agrupamento
SQL_ATRIBUICOES_TERRITORIO_SABER = f"""
-- SME — professor via RF
SELECT
    cc.cd_componente_curricular       AS CodigoComponenteCurricular,
    te.cd_turma_escola                AS CodigoTurma,
    te.an_letivo                      AS AnoLetivo,
    vsc.cd_registro_funcional         AS RfProfessor,
    COALESCE(tgt.cd_territorio_saber, 0) AS CodigoTerritorioSaber,
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
    INNER JOIN v_cadastro_unidade_educacao ue ON ue.cd_unidade_educacao = esc.cd_escola
    INNER JOIN unidade_administrativa dre
        ON dre.tp_unidade_administrativa = {_TIPO_UNIDADE_ADMINISTRATIVA_DRE}
        AND ue.cd_unidade_administrativa_referencia = dre.cd_unidade_administrativa
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
        AND cc.cd_componente_curricular IN ({_COMPONENTES_TERRITORIO})
    INNER JOIN serie_ensino se ON se.cd_serie_ensino = g.cd_serie_ensino
    LEFT JOIN turma_grade_territorio_experiencia tgt
        ON tgt.cd_serie_grade = stg.cd_serie_grade
        AND tgt.cd_componente_curricular = cc.cd_componente_curricular
    LEFT JOIN tipo_experiencia_pedagogica exp
        ON exp.cd_experiencia_pedagogica = tgt.cd_experiencia_pedagogica
    LEFT JOIN território_saber ter
        ON ter.cd_territorio_saber = tgt.cd_territorio_saber
    INNER JOIN atribuicao_aula aa
        ON gcc.cd_grade = aa.cd_grade
        AND gcc.cd_componente_curricular = aa.cd_componente_curricular
        AND aa.cd_serie_grade = stg.cd_serie_grade
        AND aa.dt_cancelamento IS NULL
        AND aa.an_atribuicao = te.an_letivo
        AND aa.dt_atribuicao_aula <= GETDATE()
        AND COALESCE(aa.dt_disponibilizacao_aulas, GETDATE()) >= '2020-02-05'
        AND (aa.cd_motivo_disponibilizacao <> {_MOTIVO_DISPONIBILIZACAO_ERRO_CADASTRO}
             OR aa.cd_motivo_disponibilizacao IS NULL)
    INNER JOIN v_cargo_base_cotic vcbc
        ON vcbc.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
    INNER JOIN v_servidor_cotic vsc ON vsc.cd_servidor = vcbc.cd_servidor
WHERE te.st_turma_escola IN ('O', 'A', 'C', 'E')
  AND te.an_letivo = ?

UNION ALL

-- Externos (CEI_INDIR=11, CRP_CONV=12, EMEFPFOM=32, EMEIPFOM=33)
SELECT
    cc.cd_componente_curricular       AS CodigoComponenteCurricular,
    te.cd_turma_escola                AS CodigoTurma,
    te.an_letivo                      AS AnoLetivo,
    pe.cd_cpf_pessoa                  AS RfProfessor,
    COALESCE(tgt.cd_territorio_saber, 0) AS CodigoTerritorioSaber,
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
    INNER JOIN v_cadastro_unidade_educacao ue ON ue.cd_unidade_educacao = esc.cd_escola
    INNER JOIN unidade_administrativa dre
        ON dre.tp_unidade_administrativa = {_TIPO_UNIDADE_ADMINISTRATIVA_DRE}
        AND ue.cd_unidade_administrativa_referencia = dre.cd_unidade_administrativa
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
        AND cc.cd_componente_curricular IN ({_COMPONENTES_TERRITORIO})
    LEFT JOIN turma_grade_territorio_experiencia tgt
        ON tgt.cd_serie_grade = stg.cd_serie_grade
        AND tgt.cd_componente_curricular = cc.cd_componente_curricular
    LEFT JOIN tipo_experiencia_pedagogica exp
        ON exp.cd_experiencia_pedagogica = tgt.cd_experiencia_pedagogica
    LEFT JOIN território_saber ter
        ON ter.cd_territorio_saber = tgt.cd_territorio_saber
    INNER JOIN atribuicao_externo ae
        ON gcc.cd_grade = ae.cd_grade
        AND gcc.cd_componente_curricular = ae.cd_componente_curricular
        AND ae.dt_cancelamento IS NULL
        AND ae.an_atribuicao = te.an_letivo
        AND ae.dt_atribuicao <= GETDATE()
        AND COALESCE(ae.dt_disponibilizacao, GETDATE()) >= '2020-02-05'
        AND (ae.cd_motivo_disponibilizacao_externo <> 1
             OR ae.cd_motivo_disponibilizacao_externo IS NULL)
    INNER JOIN contrato_externo ce ON ce.cd_contrato_externo = ae.cd_contrato_externo
    INNER JOIN pessoa pe ON pe.cd_pessoa = ce.cd_pessoa
WHERE te.st_turma_escola IN ('O', 'A', 'C', 'E')
  AND te.an_letivo = ?
  AND esc.tp_escola IN {_TIPOS_ESCOLA_EXTERNOS}

ORDER BY CodigoTurma, CodigoTerritorioSaber, CodigoExperienciaPedagogica,
         RfProfessor, DataAtribuicao, DataDisponibilizacao
"""
