# Glossário de Modelos do Domínio Pedagógico

Estes modelos residem em `apps/pedagogico/models.py` e são persistidos no banco `pedagogico_db` (PostgreSQL).

## 1. ComponenteCurricular

Catálogo de componentes curriculares ativos no EOL. Fonte de verdade para código e descrição.

- **Tabela:** `componente_curricular`
- **Unique:** `codigo` (Integer)
- **Alimenta:** `GET /api/v1/componentes-curriculares`

## 2. ComponenteCurricularPorTurma

Atribuição real de componente a uma turma e professor. Inclui flags que classificam o componente: regência, território do saber e planejamento de regência.

- **Tabela:** `componente_curricular_por_turma`
- **Unique:** `(codigo, turma_codigo, professor)` com `nulls_distinct=False`
- **Índices:** `turma_codigo`, `codigo`, `ano_letivo`, `(professor, ano_letivo)`
- **Alimenta:** turmas, atribuições, validações PAP/UE

## 3. AgrupamentoAtribuicaoTerritorioSaber

Agrupamento de componentes de território atribuídos a um professor numa mesma turma. `cod_agrupamento` é hash MD5 determinístico da chave natural.

- **Tabela:** `agrupamento_atribuicao_territorio_saber`
- **Unique:** `cod_agrupamento` (BigIntegerField)
- **Índices:** `cod_turma`, `rf_professor`, `ano_letivo`
- **Alimenta:** `territorio-saber/agrupamentos-correlacionados`, `territorio-saber/agrupamentos`
- **Nota:** `cod_componentes_curriculares` armazena os códigos como CSV; o ETL faz o split e popula `ComponenteCurricularAgrupamento`.

## 4. ComponenteCurricularAgrupamento

Itens de um agrupamento de território do saber — uma linha por componente. Derivada do split do CSV de `AgrupamentoAtribuicaoTerritorioSaber`.

- **Tabela:** `componente_curricular_agrupamento`
- **Unique:** `(componente_codigo, turma_codigo, codigo_agrupamento)`
- **Índices:** `turma_codigo`, `componente_codigo`
- **Alimenta:** `codigosTerritoriosAgrupamento` nos endpoints de perfil e planejamento

## 5. ComponenteInicioTurma

Data de início e periodicidade de cada componente por turma. Campos `ue_codigo`, `ano_letivo` e `tipo_periodicidade` são desnormalizados para evitar JOIN no endpoint.

- **Tabela:** `componente_inicio_turma`
- **Unique:** `(componente_codigo, turma_codigo)`
- **Índices:** `(ue_codigo, ano_letivo)`, `turma_codigo`
- **Alimenta:** `GET /api/v1/componentes-curriculares/turmas/vigencia`

## 6. GradeCurricularSerie

Catálogo de componentes previstos na grade por série e modalidade. Representa a oferta curricular possível — independente de haver atribuição real de professor ou turma.

- **Tabela:** `grade_curricular_serie`
- **Unique:** `(codigo_componente_curricular, ano_letivo, modalidade)` com `nulls_distinct=False`
- **Índices:** `(ano_letivo, modalidade)`, `codigo_ano_turma`
- **`modalidade`:** calculado via CASE na query — `1=EI | 3=EJA | 4=CIEJA | 5=EF | 6=EM`
- **Alimenta:** `ues/{ueId}/modalidades/{mod}/anos/{ano}`, `ues/{ueId}/modalidades/{mod}/anos/{ano}/turmas-programa`

## 7. RegenciaComponenteCurricular

Tabela local de apoio. Armazena triplas `(id_componente, turno, ano)` que representam a configuração histórica de planejamento de regência por combinação de turno e série.

- **Tabela:** `regencia_componente_curricular`
- **Origem:** fixtures/migração local
- **Uso atual:** referência histórica do domínio. O ETL principal calcula o lookup A3 diretamente do EOL via `SQL_LOOKUP_PLANEJAMENTO_REGENCIA`.

## 8. ComponenteCurricularPAP

Tabela local de apoio com os IDs de componentes PAP (Programa de Apoio e Acompanhamento à Aprendizagem).

- **Tabela:** `componentecurricularpap`
- **Unique:** `id_componente_curricular`
- **Origem:** fixtures/migração local
- **Alimenta:** validações e regras ligadas a PAP
