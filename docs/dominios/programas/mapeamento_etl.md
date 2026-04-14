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

**Filtro EOL:** `cd_tipo_programa IN (...)` — a lista é montada a partir de `TipoProgramaEOL.codigos()` em `services.py` (fonte única de verdade). Valores: 649, 650, 656, 657, 658.

---

## Fase 2 — ComponenteCurricularPrograma

SQL: `SQL_COMPONENTE_CURRICULAR_PROGRAMA` em `services.py`

| Campo EOL | Campo Destino | Descrição |
|-----------|--------------|-----------|
| `cc.cd_componente_curricular` | `codigo_componente_curricular` | Chave natural única |
| `LTRIM(RTRIM(cc.dc_componente_curricular))` | `nome_componente_curricular` | Nome do componente |
| *(derivado do id via `ComponenteCurricularEOL.categoria()`)* | `categoria` | `"PAP"` ou `"PAEE"` |
| *(derivado do id via `ComponenteCurricularEOL.vigente()`)* | `vigente` | `True` se não legado |

**Filtro EOL:** `cd_componente_curricular IN (...)` — a lista é montada a partir de `ComponenteCurricularEOL.codigos()` no próprio `services.py`, não é hardcoded na SQL.

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
| `te.st_turma_escola` | `situacao` | `O`, `A`, `C` ou `E` — valores do enum `SituacaoTurma` |
| `te.cd_tipo_programa` | `codigo_tipo_programa` | FK lógica para `tipo_programa` |
| *(derivado via `TipoProgramaEOL.categoria()` em `TurmaProgramaOut`)* | `categoria` | `"PAP"` ou `"PAEE"` |

**Filtros EOL:**
- `te.cd_tipo_turma = 3`
- `te.cd_tipo_programa IN (...)` — lista montada a partir de `TipoProgramaEOL.codigos()`

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

**Filtros EOL:** mesmos da Fase 3 + `gcc.cd_componente_curricular IN (...)` montado de `ComponenteCurricularEOL.codigos()`

---

## Fase 5 — MatriculaTurmaPrograma

SQL: `SQL_MATRICULA_TURMA_PROGRAMA` em `services.py`

| Campo EOL | Campo Destino | Descrição |
|-----------|--------------|-----------|
| `vm.cd_aluno` | `codigo_aluno` | FK lógica → `PEDAGOGICO_DB` (de `v_matricula_cotic`) |
| `m.cd_turma_escola` | `codigo_turma` | FK lógica → `turma_programa` (de `matricula_turma_escola`) |
| `gcc.cd_componente_curricular` | `codigo_componente_curricular` | FK lógica → `componente_curricular_programa` |
| `LTRIM(RTRIM(cc.dc_componente_curricular))` | `nome_componente_curricular` | Desnormalizado |
| `m.cd_situacao_aluno` | `codigo_situacao_matricula` | Situação **turma-específica** (de `matricula_turma_escola`) |
| *(derivado via `SituacaoMatricula.get_descricao()` em `MatriculaTurmaProgramaOut`)* | `descricao_situacao_matricula` | Texto resolvido em Python a partir do código |
| `m.dt_situacao_aluno` | `data_matricula` | Data da situação da matrícula |
| `m.dt_situacao_aluno` | `data_situacao` | Mesma data (alias `dt_situacao` na SQL) |
| `te.an_letivo` | `ano_letivo` | Desnormalizado da turma |
| `CAST(te.cd_escola AS VARCHAR(20))` | `codigo_ue` | Desnormalizado da turma |
| `CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20))` | `codigo_dre` | Desnormalizado da turma |
| *(derivado via `TipoProgramaEOL.categoria()` em `MatriculaTurmaProgramaOut`)* | `categoria` | `"PAP"` ou `"PAEE"` |

**JOINs:**
- `matricula_turma_escola m` ⟕ `v_matricula_cotic vm` — matrícula e aluno
- `turma_escola te` ⟕ `v_cadastro_unidade_educacao vcue` — dados da turma e DRE
- `turma_escola_grade_programa → escola_grade → grade_componente_curricular → componente_curricular` — componentes

> **Nota:** Após o refactor dos enums, o `CASE WHEN` que traduzia `cd_situacao_aluno` em texto foi **removido da SQL**. A tradução acontece em Python via `SituacaoMatricula.get_descricao()`. Não há JOIN com uma tabela `situacao_matricula`.

**Filtros EOL:** mesmos da Fase 4 — `te.cd_tipo_turma = 3`, `te.cd_tipo_programa IN (TipoProgramaEOL.codigos())`, `gcc.cd_componente_curricular IN (ComponenteCurricularEOL.codigos())`

> **Lacuna conhecida:** a SQL atual lê apenas de `matricula_turma_escola` + `v_matricula_cotic` (ano vigente). Matrículas arquivadas em `historico_matricula_turma_escola` + `v_historico_matricula_cotic` não entram — follow-up para cobrir anos passados. O domínio `alunos` já faz o `UNION ALL` correspondente em `SQL_MATRICULA` (`apps/alunos/services.py`).
