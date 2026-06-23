# Glossário de Modelos do Domínio Pedagógico

Estes modelos residem em `apps/pedagogico/models.py` e são persistidos no banco `pedagogico_db` (PostgreSQL).

## 1. ComponenteCurricular

Catálogo de componentes curriculares ativos no EOL. Fonte de verdade para código e descrição.

- **Tabela:** `componente_curricular`
- **Fonte:** `SQL_COMPONENTES_NAO_CANCELADOS`, equivalente a `componente_curricular WHERE dt_cancelamento IS NULL`
- **Unique:** `codigo` (Integer)
- **Nota:** também armazena `regencia`, calculado no SQL pela lista `_IDS_REGENCIA`.
- **Alimenta:** `GET /api/v1/componentes-curriculares`

## 2. ComponenteTurma

Estrutura turma × componente, sem professor. Mantém apenas o vínculo curricular real da turma e o código do componente quando ele pertence a território do saber.

- **Tabela:** `componente_turma`
- **Fonte:** `SQL_COMPONENTE_TURMA`
- **Unique:** `(turma_codigo, componente_codigo)`
- **Índices:** `turma_codigo`, `componente_codigo`
- **Branches da query:** turmas com série via `serie_turma_escola → serie_turma_grade → grade`; turmas de programa via `turma_escola_grade_programa`
- **Filtro de situação:** `st_turma_escola IN ('O', 'A', 'C', 'E')`
- **Alimenta:** consultas de componentes por turma

## 3. AtribuicaoComponente

Atribuição real de professor a uma turma e componente. Separa a existência do componente na turma da existência de professor atribuído.

- **Tabela:** `atribuicao_componente`
- **Fonte:** `SQL_ATRIBUICAO_COMPONENTE`
- **Unique:** `(turma_codigo, componente_codigo, professor)` com `nulls_distinct=False`
- **Índices:** `turma_codigo`, `componente_codigo`, `(professor, ano_letivo)`
- **Branches da query:** SME ativo por série; SME ativo por programa explícito; SME ativo por programa via `escola_grade`; externo ativo por série; externo ativo por programa; SME liberado; externo liberado.
- **Filtro de situação:** `st_turma_escola IN ('O', 'A', 'C', 'E')`
- **Motivo de disponibilização:** exclui erro de cadastro (`26` no SME, `1` para externo) e mantém fim de ano letivo quando previsto na regra do legado.
- **Externos:** limitados a `tp_escola IN (11, 12, 32, 33)`.
- **Professor nulo:** não representa “componente sem professor”; ausência de linha indica que não há professor atribuído.
- **Alimenta:** consultas por professor/turma/componente

## 4. AgrupamentoAtribuicaoTerritorioSaber

Agrupamento de componentes de território atribuídos a um professor numa mesma turma. `cod_agrupamento` é o identificador público/legado do agrupamento retornado nos endpoints, mas não identifica sozinho uma linha física da tabela.

- **Tabela:** `agrupamento_atribuicao_territorio_saber`
- **Fonte:** `SQL_ATRIBUICOES_TERRITORIO_SABER`
- **Unique:** `(cod_turma, cod_territorio_saber, cod_experiencia_pedagogica, rf_professor, dt_inicio_atribuicao, cod_componentes_curriculares)` com `nulls_distinct=False`
- **Índices:** `cod_agrupamento`, `cod_turma`, `rf_professor`, `ano_letivo`
- **Branches da query:** SME (`atribuicao_aula + v_cargo_base_cotic + v_servidor_cotic`) e externo (`atribuicao_externo + contrato_externo + pessoa`).
- **Território:** resolvido por `turma_grade_territorio_experiencia`.
- **Filtro de situação:** `st_turma_escola IN ('O', 'A', 'C', 'E')`
- **Alimenta:** `territorio-saber/agrupamentos-correlacionados`, `territorio-saber/agrupamentos`
- **Nota:** `cod_componentes_curriculares` armazena os códigos como CSV; o ETL faz o split e popula `ComponenteCurricularAgrupamento`. O mesmo `cod_agrupamento` pode aparecer em mais de uma linha quando o legado reaproveita o identificador para outro professor ou outro recorte histórico.

## 5. ComponenteCurricularAgrupamento

Itens de um agrupamento de território do saber — uma linha por componente. Derivada do split do CSV de `AgrupamentoAtribuicaoTerritorioSaber`.

- **Tabela:** `componente_curricular_agrupamento`
- **Fonte:** derivada de `AgrupamentoAtribuicaoTerritorioSaber`; o ETL faz split do CSV `cod_componentes_curriculares`.
- **Unique:** `(componente_codigo, turma_codigo, codigo_agrupamento, rf_professor)` com `nulls_distinct=False`
- **Índices:** `turma_codigo`, `componente_codigo`, `codigo_agrupamento`
- **Alimenta:** `codigosTerritoriosAgrupamento` nos endpoints de perfil e planejamento

## 6. GradeComponenteCurricular

Catálogo de componentes previstos na grade por série e modalidade. Representa a oferta curricular possível — independente de haver atribuição real de professor ou turma.

- **Tabela:** `grade_componente_curricular`
- **Fonte:** `SQL_GRADE_COMPONENTE_CURRICULAR`
- **Caminho principal:** `turma_escola → escola → grade`, com join em `unidade_administrativa` para DRE.
- **Filtro de situação:** `st_turma_escola IN ('O', 'A', 'C')`; turmas extintas (`E`) não entram.
- **Série válida:** exige `sg_resumida_serie IS NOT NULL`.
- **Programas:** considera turmas de programa via `turma_escola_grade_programa`.
- **Unique:** `(codigo_componente_curricular, ano_letivo, modalidade, codigo_serie_ensino)` com `nulls_distinct=False`
- **Índices:** `(ano_letivo, modalidade)`, `codigo_ano_turma`
- **`modalidade`:** calculado via CASE na query — `1=EI | 3=EJA | 4=CIEJA | 5=EF | 6=EM`
- **`codigo_ano_turma`:** campo de exibição/classificação retornado ao consumidor. Não compõe a identidade porque pode variar para a mesma série de ensino no legado; a chave segura usa `codigo_serie_ensino`.
- **Alimenta:** `ues/{ueId}/modalidades/{mod}/anos/{ano}`, `ues/{ueId}/modalidades/{mod}/anos/{ano}/turmas-programa`

## 7. Turma

Dados cadastrais de turmas extraídos do EOL. Sincronizado por ano letivo a partir de `turma_escola`.

- **Tabela:** `turma`
- **Fonte:** `SQL_TURMAS`
- **Unique:** `codigo` (BigIntegerField)
- **Índices:** `(ue_codigo, ano_letivo)`, `tipo_turma`, `ano_letivo`
- **Filtro de situação:** `st_turma_escola IN ('O', 'A', 'E', 'C')`
- **Alimenta:** endpoints de turmas e planejamento pedagógico
- **Campos calculados:** `Ano` usa o primeiro caractere numérico de `dc_turma_escola`, senão `0`; `Extinta` deriva de `st_turma_escola = 'E'`; `Modalidade` e `CodigoModalidade` derivam da etapa e do tipo de escola; `Semestre` é calculado para EJA pelo mês de início; `EnsinoEspecial` deriva de `cd_etapa_ensino = 13 AND cd_modalidade_ensino = 2`.
- **Etapa e ciclo (códigos crus):** `codigo_etapa_ensino` ← `ee.cd_etapa_ensino` (1–17) e `codigo_ciclo_ensino` ← `se.cd_ciclo_ensino`, materializados para paridade com `EtapaEnsino`/`CicloEnsino` do legado (Pedagogico-API). Os joins `ee`/`se` já existiam na `SQL_TURMAS` (sem join novo). ⚠️ **Não confundir com `codigo_modalidade_etapa`**, que é *bucket* derivado por `CASE` (1/3/4/5/6, com `COALESCE` da etapa do programa) — equivalente a um segundo `codigo_modalidade`, e **não** o `cd_etapa_ensino` cru. Adicionados na migration `0011`.

## 8. TurmaItinerarioEnsinoMedio

Tabela local de apoio com os itinerários disponíveis para o Ensino Médio. Não requer query ao SQL Server — populada via fixture Django.

- **Tabela:** `turma_itinerario_ensino_medio`
- **Origem:** `apps/pedagogico/fixtures/turma_itinerario_ensino_medio.json`
- **Alimenta:** `GET /api/v1/itinerario/ensino-medio`

## 9. ComponenteCurricularPlanejamentoRegencia

Tabela local de apoio. Armazena triplas `(id_componente_curricular, turno, ano)` que representam quais componentes entram no planejamento de regência por combinação de turno e série.

- **Tabela:** `componente_curricular_planejamento_regencia`
- **Origem:** fixtures/migração local
- **Uso atual:** referência para o microsserviço de consumo. Não é fase do ETL e não enriquece `ComponenteTurma`.

## 10. ComponenteCurricularHierarquia

Tabela local de apoio para resolver componentes filhos e seus componentes curriculares pais.

- **Tabela:** `componente_curricular_hierarquia`
- **Campos principais:** `id_componente_curricular_pai`, `id_componente_curricular`, `vigencia`
- **Uso atual:** referência para o microsserviço de consumo. Não é fase do ETL e não é gravada em `ComponenteTurma`.

## 11. ComponenteCurricularPAP

Tabela local de apoio com os IDs de componentes PAP (Programa de Apoio e Acompanhamento à Aprendizagem).

- **Tabela:** `componente_curricular_pap`
- **Unique:** `id_componente_curricular`
- **Origem:** fixtures/migração local
- **Alimenta:** validações e regras ligadas a PAP
