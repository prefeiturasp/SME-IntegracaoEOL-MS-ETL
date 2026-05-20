"""Queries SQL do domínio Alunos."""

SQL_TIPO_NEE = """
SELECT
    tp_necessidade_especial AS codigo_necessidade_especial
  , dc_necessidade_especial AS descricao
  , tp_necessidade_especial_estado AS codigo_estado
  , dt_cancelamento
FROM tipo_necessidade_especial
"""

SQL_ALUNO = """
SELECT
     a.cd_aluno AS codigo_aluno
   , v.nm_aluno AS nome
   , v.nm_social_aluno AS nome_social
   , v.dt_nascimento_aluno AS data_nascimento
   , v.cd_sexo_aluno AS sexo
   , a.cd_nacionalidade_aluno AS nacionalidade
   , a.cd_identificacao_social AS nis
   , a.cd_cpf_aluno AS cpf
   , a.nm_mae_aluno AS nome_mae
   , trc.dc_raca_cor AS raca_cor
   , a.dt_atualizacao_tabela  AS data_atualizacao_contato
   , CASE WHEN EXISTS (
    SELECT 1 FROM necessidade_especial_aluno
    WHERE cd_aluno = a.cd_aluno
) THEN 1 ELSE 0 END AS possui_deficiencia
FROM aluno a
LEFT JOIN v_aluno_cotic v ON a.cd_aluno = v.cd_aluno
LEFT JOIN tipo_raca_cor trc ON trc.tp_raca_cor = a.tp_raca_cor;
"""

SQL_RESPONSAVEL = """
SELECT
     ra.cd_identificador_responsavel AS codigo_responsavel
   , ra.cd_aluno AS codigo_aluno
   , ra.tp_pessoa_responsavel AS tipo_responsavel
   , ra.nm_responsavel AS nome
   , ra.cd_cpf_responsavel AS cpf
   , ra.email_responsavel AS email
   , ra.cd_ddd_celular_responsavel AS ddd_celular
   , ra.nr_celular_responsavel AS numero_celular
   , ra.in_autoriza_envio_sms AS autoriza_sms
   , e.nm_logradouro AS logradouro
   , e.cd_cep AS cep
   , ra.dt_fim AS data_fim_vinculo_aluno
FROM responsavel_aluno ra
LEFT JOIN endereco e ON e.ci_endereco = ra.ci_endereco
"""

SQL_NEE_ALUNO = """
SELECT
    cd_identificador_necessidade_especial_aluno
        AS codigo_necessidade_especial_aluno
  , cd_aluno AS codigo_aluno
  , tp_necessidade_especial AS codigo_necessidade_especial
  , dt_inicio
  , dt_fim
FROM necessidade_especial_aluno
"""

SQL_MATRICULA = """
SELECT
    cd_matricula, cd_aluno, codigo_ue, data_situacao_matricula, ano_letivo,
    codigo_situacao_matricula
FROM (
    SELECT
        cd_matricula
      , cd_aluno
      , cd_escola AS codigo_ue
      , dt_status_matricula AS data_situacao_matricula
      , an_letivo AS ano_letivo
      , st_matricula AS codigo_situacao_matricula
    FROM v_matricula_cotic
    UNION ALL
    SELECT
        cd_matricula
      , cd_aluno
      , cd_escola AS codigo_ue
      , dt_status_matricula AS data_situacao_matricula
      , an_letivo AS ano_letivo
      , st_matricula AS codigo_situacao_matricula
    FROM v_historico_matricula_cotic
) AS mt
"""

SQL_MATRICULA_TURMA = """
WITH CteMatriculaTurma AS (
    SELECT
        mt.cd_matricula
      , mt.cd_turma_escola AS codigo_turma
      , mt.nr_chamada_aluno AS numero_chamada
      , mt.dt_situacao_aluno AS data_situacao
    FROM matricula_turma_escola mt
    UNION ALL
    SELECT
        mt.cd_matricula
      , mt.cd_turma_escola AS codigo_turma
      , mt.nr_chamada_aluno AS numero_chamada
      , mt.dt_situacao_aluno AS data_situacao
    FROM historico_matricula_turma_escola mt
)
SELECT mt.cd_matricula, mt.codigo_turma, mt.numero_chamada, mt.data_situacao
FROM CteMatriculaTurma mt
"""

SQL_MATRICULA_ANO_LETIVO = """
SELECT tab.cd_unidade_educacao AS codigo_dre
     , tab.cd_escola AS codigo_ue
     , tab.tp_escola AS tipo_escola
     , tab.an_letivo AS ano_letivo
     , CASE
           WHEN tab.cd_etapa_ensino IN ( 1, 10 ) THEN 1
           WHEN tab.cd_etapa_ensino IN ( 3, 11 ) THEN 3
           WHEN tab.cd_etapa_ensino IN ( 5, 13 ) THEN 5
           WHEN tab.cd_etapa_ensino IN ( 6, 8, 9, 17 ) THEN 6
           END AS codigo_modalidade
     , CASE
           WHEN tab.cd_etapa_ensino IN ( 1, 10 ) THEN 'EI'
           WHEN tab.cd_etapa_ensino IN ( 3, 11 ) THEN 'EJA'
           WHEN tab.cd_etapa_ensino IN ( 5, 13 ) THEN 'EF'
           WHEN tab.cd_etapa_ensino IN ( 6, 8, 9, 17 ) THEN 'EM'
           END AS modalidade
     , CASE
           WHEN tab.cd_etapa_ensino IN ( 1, 10 ) THEN 1
           WHEN tab.cd_etapa_ensino IN ( 3, 11 ) THEN 4
           WHEN tab.cd_etapa_ensino IN ( 5, 13 ) THEN 2
           WHEN tab.cd_etapa_ensino IN ( 6, 8, 9, 17 ) THEN 3
           END AS ordem
, tab.sg_resumida_serie AS ano
, tab.dc_turma_escola AS turma
, COUNT(cd_matricula) AS quantidade
FROM (
SELECT
    dre.cd_unidade_educacao
  , e.cd_escola
  , e.tp_escola
  , ee.cd_etapa_ensino
  , se.sg_resumida_serie
  , te.dc_turma_escola
  , VMC.cd_matricula
  , VMC.an_letivo
FROM
    v_matricula_cotic VMC
INNER JOIN matricula_turma_escola mte ON VMC.cd_matricula = mte.cd_matricula
INNER JOIN turma_escola te
    ON te.cd_turma_escola = mte.cd_turma_escola
    AND te.cd_tipo_turma = 1
INNER JOIN escola e ON e.cd_escola = te.cd_escola
INNER JOIN serie_turma_escola ste ON te.cd_turma_escola = ste.cd_turma_escola
INNER JOIN serie_ensino se ON ste.cd_serie_ensino = se.cd_serie_ensino
INNER JOIN etapa_ensino ee ON se.cd_etapa_ensino = ee.cd_etapa_ensino
INNER JOIN v_cadastro_unidade_educacao vcue
    ON e.cd_escola = vcue.cd_unidade_educacao
INNER JOIN v_cadastro_unidade_educacao dre
    ON dre.cd_unidade_educacao = vcue.cd_unidade_administrativa_referencia
WHERE mte.cd_situacao_aluno in (1,5,6,10,13)
) AS tab
GROUP BY
    tab.cd_unidade_educacao,
    tab.tp_escola,
    tab.cd_escola,
    tab.cd_etapa_ensino,
    tab.sg_resumida_serie,
    tab.dc_turma_escola,
    tab.an_letivo
"""

SQL_MATRICULA_COMPONENTE_CURRICULAR_ANO_LETIVO = """
SELECT
       vcue.cd_unidade_educacao AS codigo_ue
     , vcue.cd_unidade_administrativa_referencia AS codigo_dre
     , vmc.an_letivo AS ano_letivo
     , CASE
            WHEN ee.cd_etapa_ensino IN (1, 10) THEN 'EI'
            WHEN ee.cd_etapa_ensino IN ( 2, 3, 7, 11 ) THEN 'EJA'
            WHEN ee.cd_etapa_ensino IN ( 4, 5, 12, 13 ) THEN 'EF'
            WHEN ee.cd_etapa_ensino IN ( 6, 7, 8, 9, 17, 14 ) THEN 'EM'
        END AS modalidade
     , CASE
            WHEN ee.cd_etapa_ensino IN(1, 10) THEN 1
            WHEN ee.cd_etapa_ensino IN( 2, 3, 7, 11 ) THEN 4
            WHEN ee.cd_etapa_ensino IN( 4, 5, 12, 13 ) THEN 2
            WHEN ee.cd_etapa_ensino IN( 6, 7, 8, 9, 17, 14 ) THEN 3
        END AS ordem
     , gcc.cd_componente_curricular AS componente_curricular_id
     , se.sg_resumida_serie AS ano
     , te.dc_turma_escola AS turma
     , COUNT(VMC.cd_matricula) AS quantidade
 from v_matricula_cotic VMC
inner join matricula_turma_escola mte
    on VMC.cd_matricula = mte.cd_matricula
inner join turma_escola_grade_programa tgte
    on tgte.cd_turma_escola = mte.cd_turma_escola
inner join escola_grade eg
    on eg.cd_escola_grade = tgte.cd_escola_grade
inner join grade_componente_curricular gcc
    on eg.cd_grade = gcc.cd_grade
inner join v_matricula_cotic vmc2
    on vmc2.cd_aluno = vmc.cd_aluno
    and vmc2.an_letivo = vmc.an_letivo
    and vmc.cd_matricula <> vmc2.cd_matricula
inner join matricula_turma_escola mtr
    on mtr.cd_matricula = vmc2.cd_matricula
inner join turma_escola te
    on te.cd_turma_escola = mtr.cd_turma_escola
    and te.cd_tipo_turma = 1
inner join escola e
    on e.cd_escola = te.cd_escola
inner join serie_turma_escola ste
    on te.cd_turma_escola = ste.cd_turma_escola
inner join serie_ensino se
    on ste.cd_serie_ensino = se.cd_serie_ensino
inner join etapa_ensino ee
    on se.cd_etapa_ensino = ee.cd_etapa_ensino
INNER JOIN v_cadastro_unidade_educacao vcue
    ON e.cd_escola = vcue.cd_unidade_educacao
INNER JOIN v_cadastro_unidade_educacao dre
    ON dre.cd_unidade_educacao = vcue.cd_unidade_administrativa_referencia
WHERE mte.cd_situacao_aluno in (1,6,10,13) AND se.cd_etapa_ensino <> 18
GROUP BY
  ee.cd_etapa_ensino
, gcc.cd_componente_curricular
, se.sg_resumida_serie
, te.dc_turma_escola
, vcue.cd_unidade_educacao
, vmc.an_letivo
, vcue.cd_unidade_administrativa_referencia
"""

SQL_DADOS_ALUNO_ACOMPANHAMENTO_ESCOLAR = """
SELECT aluno.cd_aluno                        codigo_aluno,
       aluno.nm_aluno                        nome,
       aluno.nm_social_aluno                 nome_social,
       responsavel.nm_responsavel            nome_responsavel,
       responsavel.cd_cpf_responsavel        cpf_responsavel,
       aluno.dt_nascimento_aluno             data_nascimento,
       Rtrim(Ltrim(tesc.sg_tp_escola))       descricao_tipo_escola,
       responsavel.tp_pessoa_responsavel     tipo_responsavel,
       dre.cd_unidade_educacao               codigo_dre,
       dre.nm_exibicao_unidade               sigla_dre,
       vue.cd_unidade_educacao               codigo_ue,
       Ltrim(Rtrim(vue.nm_unidade_educacao)) unidade_educacional,
       te.cd_turma_escola                    codigo_turma,
       te.dc_turma_escola                    turma,
       tesc.tp_escola                        codigo_tipo_escola,
       mte.situacaomatricula                 situacao_matricula,
       mte.dt_situacao_aluno                 data_situacao_matricula,
       etapa_ensino.cd_etapa_ensino AS codigo_etapa_ensino,
       ciclo_ensino.cd_ciclo_ensino AS codigo_ciclo_ensino,
       serie_ensino.sg_resumida_serie AS serie_resumida,
       etapa_ensino.cd_etapa_ensino as codigo_modalidade_turma
FROM   v_aluno_cotic aluno
       INNER JOIN responsavel_aluno responsavel
               ON aluno.cd_aluno = responsavel.cd_aluno
       INNER JOIN(SELECT cd_aluno,
                         cd_matricula,
                         vmc.cd_escola,
                         cd_serie_ensino
                  FROM   v_matricula_cotic vmc
                  inner join escola esc on esc.cd_escola = vmc.cd_escola
                  where st_matricula = 1
                    and (cd_serie_ensino is not null
                    or esc.tp_escola in (22, 23))
                    and an_letivo = year(getdate())) AS matricula
               ON matricula.cd_aluno = aluno.cd_aluno
       INNER JOIN(SELECT cd_matricula,
                         cd_turma_escola,
                         cd_situacao_aluno,
                         dt_situacao_aluno,
                         CASE
                           WHEN cd_situacao_aluno = 1 THEN 'Ativo'
                           WHEN cd_situacao_aluno = 6 THEN
                           'Pendente de Rematricula'
                           WHEN cd_situacao_aluno = 10 THEN 'Rematriculado'
                           WHEN cd_situacao_aluno = 13 THEN 'Sem continuidade'
                           ELSE 'Fora do dominio liberado pela PRODAM'
                         END SituacaoMatricula
                  FROM   matricula_turma_escola (nolock)) mte
               ON mte.cd_matricula = matricula.cd_matricula
                  AND mte.cd_situacao_aluno IN ( 1, 6, 10, 13 )
       INNER JOIN v_cadastro_unidade_educacao(nolock) vue
               ON vue.cd_unidade_educacao = matricula.cd_escola
       INNER JOIN escola esc
               ON esc.cd_escola = vue.cd_unidade_educacao
       INNER JOIN tipo_escola(nolock) tesc
               ON tesc.tp_escola = esc.tp_escola
                  AND tesc.tp_escola IN ( 1, 2, 3, 4,
                                          10, 11, 12, 13,
                                          14, 15, 16, 17,
                                          18, 19, 20, 22,
                                          23, 24, 25, 26,
                                          27, 28, 29, 30, 31 )
       INNER JOIN v_cadastro_unidade_educacao(nolock) dre
               ON dre.cd_unidade_educacao =
                  vue.cd_unidade_administrativa_referencia
       INNER JOIN turma_escola(nolock) te
               ON te.cd_turma_escola = mte.cd_turma_escola
       LEFT JOIN serie_ensino
               ON matricula.cd_serie_ensino = serie_ensino.cd_serie_ensino
       LEFT JOIN etapa_ensino
               ON serie_ensino.cd_etapa_ensino = etapa_ensino.cd_etapa_ensino
       LEFT JOIN ciclo_ensino
               ON serie_ensino.cd_ciclo_ensino = ciclo_ensino.cd_ciclo_ensino;
"""
