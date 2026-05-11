# Glossário de Modelos do Domínio Pedagógico

Estes modelos residem em `apps/pedagogico/models.py` e são persistidos no banco `pedagogico_db` (PostgreSQL).

## 1. ComponenteCurricular

Catálogo de componentes curriculares ativos no EOL. Fonte de verdade para código e descrição.

- **Tabela:** `componente_curricular`
- **Unique:** `codigo` (Integer)
- **Nota:** também armazena `regencia`, calculado no SQL pela lista `_IDS_REGENCIA`.
- **Alimenta:** `GET /api/v1/componentes-curriculares`

## 2. ComponenteTurma

Estrutura turma × componente, sem professor. Mantém apenas o vínculo curricular real da turma e o código do componente quando ele pertence a território do saber.

- **Tabela:** `componente_turma`
- **Unique:** `(turma_codigo, componente_codigo)`
- **Índices:** `turma_codigo`, `componente_codigo`
- **Alimenta:** consultas de componentes por turma

## 3. AtribuicaoComponente

Atribuição real de professor a uma turma e componente. Separa a existência do componente na turma da existência de professor atribuído.

- **Tabela:** `atribuicao_componente`
- **Unique:** `(turma_codigo, componente_codigo, professor)` com `nulls_distinct=False`
- **Índices:** `turma_codigo`, `componente_codigo`, `(professor, ano_letivo)`
- **Alimenta:** consultas por professor/turma/componente

## 4. AgrupamentoAtribuicaoTerritorioSaber

Agrupamento de componentes de território atribuídos a um professor numa mesma turma. `cod_agrupamento` é hash MD5 determinístico da chave natural.

- **Tabela:** `agrupamento_atribuicao_territorio_saber`
- **Unique:** `cod_agrupamento` (BigIntegerField)
- **Índices:** `cod_turma`, `rf_professor`, `ano_letivo`
- **Alimenta:** `territorio-saber/agrupamentos-correlacionados`, `territorio-saber/agrupamentos`
- **Nota:** `cod_componentes_curriculares` armazena os códigos como CSV; o ETL faz o split e popula `ComponenteCurricularAgrupamento`.

## 5. ComponenteCurricularAgrupamento

Itens de um agrupamento de território do saber — uma linha por componente. Derivada do split do CSV de `AgrupamentoAtribuicaoTerritorioSaber`.

- **Tabela:** `componente_curricular_agrupamento`
- **Unique:** `(componente_codigo, turma_codigo, codigo_agrupamento)`
- **Índices:** `turma_codigo`, `componente_codigo`
- **Alimenta:** `codigosTerritoriosAgrupamento` nos endpoints de perfil e planejamento

## 6. GradeComponenteCurricular

Catálogo de componentes previstos na grade por série e modalidade. Representa a oferta curricular possível — independente de haver atribuição real de professor ou turma.

- **Tabela:** `grade_componente_curricular`
- **Unique:** `(codigo_componente_curricular, ano_letivo, modalidade, codigo_ano_turma, codigo_serie_ensino)` com `nulls_distinct=False`
- **Índices:** `(ano_letivo, modalidade)`, `codigo_ano_turma`
- **`modalidade`:** calculado via CASE na query — `1=EI | 3=EJA | 4=CIEJA | 5=EF | 6=EM`
- **Alimenta:** `ues/{ueId}/modalidades/{mod}/anos/{ano}`, `ues/{ueId}/modalidades/{mod}/anos/{ano}/turmas-programa`

## 7. Turma

Dados cadastrais de turmas extraídos do EOL. Sincronizado por ano letivo a partir de `turma_escola`.

- **Tabela:** `turma`
- **Unique:** `codigo` (BigIntegerField)
- **Índices:** `(ue_codigo, ano_letivo)`, `tipo_turma`, `ano_letivo`
- **Alimenta:** endpoints de turmas e planejamento pedagógico
- **Nota:** `Extinta` é derivado via `CASE` na query (`st_turma_escola = 'E'`). `Modalidade` e `CodigoModalidade` são calculados via `CASE` sobre `cd_etapa_ensino`. `Semestre` é calculado para turmas EJA pelo mês de início.

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
