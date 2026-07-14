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

Estrutura turma × componente, sem professor. Mantém o vínculo curricular real
da turma e, quando o componente pertence a Território do Saber, materializa os
dados contextuais usados na resposta do MS Pedagógico.

- **Tabela:** `componente_turma`
- **Fonte:** `SQL_COMPONENTE_TURMA`
- **Unique:** `(turma_codigo, componente_codigo)`
- **Índices:** `turma_codigo`, `componente_codigo`
- **Branches da query:** turmas com série via `serie_turma_escola → serie_turma_grade → grade`; turmas de programa via `turma_escola_grade_programa`
- **Filtro de situação:** `st_turma_escola IN ('O', 'A', 'C', 'E')`
- **Território do Saber:** `codigo_componente_territorio_saber` recebe o
  próprio código do componente quando há vínculo em
  `turma_grade_territorio_experiencia`.
- **Descrição contextual:** para componentes de Território do Saber,
  `desc_territorio_saber` e `desc_experiencia_pedagogica` vêm de
  `território_saber` e `tipo_experiencia_pedagogica`. O consumidor monta a
  descrição como `desc_territorio_saber - desc_experiencia_pedagogica`, ou
  apenas `desc_territorio_saber` quando a experiência não existir.
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
- **Fonte principal:** `SQL_API_EOL_AGRUPAMENTO_ATRIBUICAO_TERRITORIO_SABER`, a partir de `agrupamentoatribuicaoterritoriosaber` no `API_EOL_DB`
- **Modo de carga:** `full_refresh`
- **Chave física:** não há unique funcional no destino; a carga usa `id_linha_api_eol`, uma chave técnica calculada na leitura, para copiar todas as linhas da origem.
- **Índices:** `cod_agrupamento`, `cod_turma`, `rf_professor`, `ano_letivo`
- **Território:** descrições e códigos vêm prontos da API EOL, com origem no processo de agrupamento do domínio legado.
- **Alimenta:** `territorio-saber/agrupamentos-correlacionados`, `territorio-saber/agrupamentos`
- **Nota:** `cod_componentes_curriculares` armazena os códigos como CSV. O mesmo `cod_agrupamento` pode aparecer em mais de uma linha quando a origem reaproveita o identificador para outro professor ou outro recorte histórico.

## 5. ComponenteCurricularAgrupamento

Itens de um agrupamento de território do saber — uma linha por componente. Mantida para compatibilidade e para a fase backup de geração local de agrupamentos.

- **Tabela:** `componente_curricular_agrupamento`
- **Fonte:** derivada de `AgrupamentoAtribuicaoTerritorioSaber` apenas quando a fase opcional `agrupamento_territorio_saber_gerado` é executada.
- **Unique:** `(componente_codigo, turma_codigo, codigo_agrupamento, rf_professor)` com `nulls_distinct=False`
- **Índices:** `turma_codigo`, `componente_codigo`, `codigo_agrupamento`
- **Uso atual:** apoio/compatibilidade; o fluxo principal lê o CSV diretamente da tabela de agrupamento.

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

Tabela de apoio com os itinerários disponíveis para o Ensino Médio.

- **Tabela:** `turma_itinerario_ensino_medio`
- **Origem:** `turma_tipo_itinerario` no `API_EOL_DB`, via `full_refresh`
- **Alimenta:** `GET /api/v1/itinerario/ensino-medio`

## 9. ComponenteCurricularPlanejamentoRegencia

Tabela de apoio. Armazena triplas `(id_componente_curricular, turno, ano)` que representam quais componentes entram no planejamento de regência por combinação de turno e série.

- **Tabela:** `componente_curricular_planejamento_regencia`
- **Origem:** `regenciacomponentecurricular` no `API_EOL_DB`, via `full_refresh`
- **Uso atual:** referência para o microsserviço de consumo. Não enriquece `ComponenteTurma`.

## 10. ComponenteCurricularHierarquia

Tabela de apoio para resolver componentes filhos e seus componentes curriculares pais.

- **Tabela:** `componente_curricular_hierarquia`
- **Campos principais:** `id_componente_curricular_pai`, `id_componente_curricular`, `vigencia`
- **Origem:** `componentecurricularpai` no `API_EOL_DB`, via `full_refresh`
- **Uso atual:** referência para o microsserviço de consumo. Não é gravada em `ComponenteTurma`.

## 11. ComponenteCurricularPAP

Tabela de apoio com os IDs de componentes PAP (Programa de Apoio e Acompanhamento à Aprendizagem).

- **Tabela:** `componente_curricular_pap`
- **Unique:** `id_componente_curricular`
- **Origem:** `componentecurricularpap` no `API_EOL_DB`, via `full_refresh`
- **Alimenta:** validações e regras ligadas a PAP

## 12. TurmaAtribuidaDreUe

Turma consolidada por DRE e UE, já entregue pronta pela origem. Existe para
responder à abrangência de turmas de um funcionário por unidade sem recompor a
hierarquia DRE → UE → turma no serviço de consumo.

- **Tabela:** `turma_atribuida_dre_ue`
- **Origem:** turmas atribuídas por DRE/UE no EOL, por ano letivo
- **Identidade:** turma dentro de escola e ano letivo. A origem repete a mesma
  turma legitimamente, então não há unicidade imposta no banco.
- **Estratégia:** recarga completa por ano letivo — a origem já entrega a linha
  final, sem detecção de mudança por linha.
- **Alimenta:** consulta de abrangência de turmas por DRE/UE do Transition Gateway.
