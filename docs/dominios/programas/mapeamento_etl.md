# Mapeamento do ETL — Domínio Programas

Detalhamento de origem (EOL / SQL Server) e destino (PostgreSQL `programas_db`) por tabela.

---

## Fase 1 — TipoPrograma

SQL: `SQL_TIPO_PROGRAMA` em `services.py`

| Campo EOL | Campo Destino | Descrição |
|-----------|--------------|-----------|
| `cd_tipo_programa` | `codigo_tipo_programa` | PK preservada do EOL |
| `LTRIM(RTRIM(sg_tipo_programa))` | — | Usado apenas na transformação (DTO) |
| `LTRIM(RTRIM(dc_tipo_programa))` | `nome` | Nome completo do tipo de programa |
| *(derivado do id em `TipoProgramaOut`)* | `categoria` | `"PAP"` ou `"PAEE"` |
| *(fixo: `True`)* | `ativo` | Sempre ativo no seed |

**Filtro EOL:** `cd_tipo_programa IN (649, 650, 656, 657, 658)`

---

## Fase 2 — ComponenteCurricularPrograma

SQL: `SQL_COMPONENTE_CURRICULAR_PROGRAMA` em `services.py`

| Campo EOL | Campo Destino | Descrição |
|-----------|--------------|-----------|
| `cc.cd_componente_curricular` | `codigo_componente_curricular` | Chave natural única |
| `LTRIM(RTRIM(cc.dc_componente_curricular))` | `nome_componente_curricular` | Nome do componente |
| `cc.dt_inicio` | `data_inicio` | Início da vigência |
| `cc.dt_fim` | `data_fim` | Fim da vigência (`NULL` se sem prazo) |
| *(derivado do id em `ComponenteCurricularProgramaOut`)* | `categoria` | `"PAP"` ou `"PAEE"` |
| *(derivado do id em `ComponenteCurricularProgramaOut`)* | `vigente` | `True` se não legado |

**Filtro EOL:** `cd_componente_curricular IN (1322, 1770, 1804, 1805, 1033, 1051, 1052, 1053, 1054, 1030)`

---

## Fase 3 — TurmaPrograma

SQL: `SQL_TURMA_PROGRAMA` em `services.py`

| Campo EOL | Campo Destino | Descrição |
|-----------|--------------|-----------|
| `te.cd_turma_escola` | `codigo_turma` | Chave natural única |
| `LTRIM(RTRIM(te.dc_turma_escola))` | `nome_turma` | Nome da turma |
| `CAST(te.cd_escola AS VARCHAR(20))` | `codigo_ue` | Código da unidade educacional |
| `CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20))` | `codigo_dre` | Código da DRE |
| `te.an_letivo` | `ano_letivo` | Ano letivo |
| `te.cd_tipo_turno` | `tipo_turno` | Código do turno (nullable) |
| `tt.dc_exibicao_portal` | `descricao_turno` | Descrição do turno — desnormalizado |
| `te.sg_tipo_situacao_turma` | `situacao` | `O`, `A`, `C` ou `E` |
| `te.cd_tipo_programa` | `codigo_tipo_programa` | FK lógica para `tipo_programa` |
| *(derivado via `TurmaProgramaOut`)* | `categoria` | `"PAP"` ou `"PAEE"` |

**Filtros EOL:**
- `te.cd_tipo_turma = 3`
- `te.cd_tipo_programa IN (649, 650, 656, 657, 658)`

**JOINs:**
- `v_cadastro_unidade_educacao` — para `codigo_dre`
- `tipo_turno` (LEFT JOIN) — para `descricao_turno`

---

## Fase 4 — TurmaProgramaComponenteCurricular

SQL: `SQL_TURMA_PROGRAMA_COMPONENTE_CURRICULAR` em `services.py`

| Campo EOL | Campo Destino | Descrição |
|-----------|--------------|-----------|
| `tegp.cd_turma_escola` | `codigo_turma` | FK lógica → `turma_programa` |
| `gcc.cd_componente_curricular` | `codigo_componente_curricular` | FK lógica → `componente_curricular_programa` |
| `LTRIM(RTRIM(cc.dc_componente_curricular))` | `nome_componente_curricular` | Desnormalizado para evitar JOIN |

**JOINs:**
- `turma_escola_grade_programa` → `escola_grade_programa` → `grade_componente_curricular` → `componente_curricular`
- `turma_escola` (filtro de tipo e programa)

**Filtros EOL:** mesmos da Fase 3 + `gcc.cd_componente_curricular` na lista de componentes do seed

---

## Fase 5 — MatriculaTurmaPrograma

SQL: `SQL_MATRICULA_TURMA_PROGRAMA` em `services.py`

| Campo EOL | Campo Destino | Descrição |
|-----------|--------------|-----------|
| `m.cd_aluno` | `codigo_aluno` | FK lógica → `PEDAGOGICO_DB` |
| `m.cd_turma_escola` | `codigo_turma` | FK lógica → `turma_programa` |
| `gcc.cd_componente_curricular` | `codigo_componente_curricular` | FK lógica → `componente_curricular_programa` |
| `LTRIM(RTRIM(cc.dc_componente_curricular))` | `nome_componente_curricular` | Desnormalizado |
| `m.st_matricula` | `codigo_situacao_matricula` | Código numérico da situação |
| `LTRIM(RTRIM(sm.dc_situacao_matricula))` | `descricao_situacao_matricula` | Texto da situação — desnormalizado |
| `m.dt_status_matricula` | `data_matricula` | Data da situação da matrícula |
| `m.dt_situacao_aluno` | `data_situacao` | Data da situação do aluno (nullable) |
| `te.an_letivo` | `ano_letivo` | Desnormalizado da turma |
| `CAST(te.cd_escola AS VARCHAR(20))` | `codigo_ue` | Desnormalizado da turma |
| `CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20))` | `codigo_dre` | Desnormalizado da turma |
| *(derivado via `MatriculaTurmaProgramaOut`)* | `categoria` | `"PAP"` ou `"PAEE"` |

**JOINs:**
- `turma_escola`, `v_cadastro_unidade_educacao` — dados da turma
- `turma_escola_grade_programa` → `escola_grade_programa` → `grade_componente_curricular` → `componente_curricular` — componentes
- `situacao_matricula` (LEFT JOIN) — descrição da situação

**Filtros EOL:** mesmos da Fase 4
