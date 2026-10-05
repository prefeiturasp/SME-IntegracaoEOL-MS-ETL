# Mapeamento do ETL — Domínio Programas

Detalhamento de origem (EOL / SQL Server) e destino (PostgreSQL `programas_db`) por tabela. As 8 fases estão registradas como `PhaseConfig` em `EtlProgramasService._init_fases()` (`apps/programas/services.py`); todas usam `modo_escrita="upsert"`.

---

## Fase 1 — TipoPrograma

SQL: `SQL_TIPO_PROGRAMA` em `services.py`. DTO: `TipoProgramaIn`.

| Campo EOL | Campo Destino | Descrição |
|-----------|--------------|-----------|
| `tp.cd_tipo_programa` | `codigo_tipo_programa` | PK preservada do EOL |
| `LTRIM(RTRIM(tp.sg_tipo_programa))` (alias `sigla`) | — | Usado apenas na derivação da categoria |
| `LTRIM(RTRIM(tp.dc_tipo_programa))` (alias `descricao`) | `nome` | `descricao` se não vazio; senão `sigla` |
| *(derivado via `TipoProgramaEOL.categoria_por_sigla(sigla, descricao)`)* | `categoria` | `"PAP"`, `"PAEE"` ou `"OUTROS"` |
| *(fixo: `True`)* | `ativo` | Sempre ativo |

**Filtro EOL:** `EXISTS` sobre `turma_escola` + `turma_escola_grade_programa` —
apenas tipos referenciados por turmas com `cd_tipo_turma = 3` e
`turma_escola_grade_programa.dt_fim IS NULL`.

> Não há filtro `cd_tipo_programa IN (...)` — qualquer tipo referenciado é carregado.

---

## Fase 2 — ComponenteCurricularPrograma

SQL: `SQL_COMPONENTE_CURRICULAR_PROGRAMA` em `services.py`. DTO: `ComponenteCurricularProgramaIn`.

| Campo EOL | Campo Destino | Descrição |
|-----------|--------------|-----------|
| `cc.cd_componente_curricular` | `codigo_componente_curricular` | Chave natural única |
| `LTRIM(RTRIM(cc.dc_componente_curricular))` | `nome_componente_curricular` | Nome do componente |
| *(derivado via `ComponenteCurricularEOL.categoria()`)* | `categoria` | `"PAP"`, `"PAEE"` ou `"OUTROS"` |
| *(derivado via `ComponenteCurricularEOL.vigente()`)* | `vigente` | `True` se não legado |

**Filtros EOL:** `te.cd_tipo_turma = 3`, `te.st_turma_escola IN ('O','A','C','E')`,
`tegp.dt_fim IS NULL`, `cc.dt_cancelamento IS NULL` — qualquer componente que apareça
no programa é carregado (categoria/vigente vêm do enum).

---

## Fase 3 — TurmaPrograma

SQL: `SQL_TURMA_PROGRAMA` em `services.py`. DTO: `TurmaProgramaIn`.

| Campo EOL | Campo Destino | Descrição |
|-----------|--------------|-----------|
| `te.cd_turma_escola` | `codigo_turma` | Chave natural única |
| `LTRIM(RTRIM(te.dc_turma_escola))` | `nome_turma` | Nome da turma |
| `CAST(te.cd_escola AS VARCHAR(20))` | `codigo_ue` | Código da unidade educacional |
| `CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20))` | `codigo_dre` | Código da DRE |
| `te.an_letivo` | `ano_letivo` | Ano letivo |
| `te.cd_tipo_turno` | `tipo_turno` | Código do turno (nullable) |
| `tt.dc_exibicao_portal` | `descricao_turno` | Descrição do turno — desnormalizado |
| `te.st_turma_escola` | `situacao` | `O`, `A`, `C` ou `E` |
| `te.cd_tipo_programa` | `codigo_tipo_programa` | FK lógica (nullable) |
| *(derivado na SQL via `CASE WHEN`)* | `categoria` | `"PAP"`, `"PAEE"` ou `"OUTROS"` |
| `g_one.descricao_grade` (TOP 1, `OUTER APPLY`) | `descricao_grade` | `grade.dc_grade` da grade vinculada — TOP 1, fiel ao legado |

**Derivação de `categoria` (no próprio SQL):**

1. `PAEE` — se existe `turma_escola_grade_programa` para a turma com
   `cd_componente_curricular = 1030` (`PAEE_SALA_RECURSOS_MULTIFUNCIONAIS`)
2. `PAP` — se existe `turma_escola_grade_programa` com `cd_componente_curricular`
   em `_COMPONENTES_PAP_CONHECIDOS` (vigentes + legados)
3. `OUTROS` — caso contrário

**Filtros EOL:**
- `te.cd_tipo_turma = 3`
- `te.st_turma_escola IN ('O','A','C','E')`
- `EXISTS` em `turma_escola_grade_programa` com `dt_fim IS NULL`

**JOINs:**
- `v_cadastro_unidade_educacao` — para `codigo_dre`
- `tipo_turno` (LEFT JOIN) — para `descricao_turno`
- `OUTER APPLY` em `turma_escola_grade_programa → escola_grade → grade` — TOP 1 para `descricao_grade`

---

## Fase 4 — TurmaProgramaComponenteCurricular

SQL: `SQL_TURMA_PROGRAMA_COMPONENTE_CURRICULAR` em `services.py`. DTO: `TurmaProgramaComponenteCurricularIn`.

| Campo EOL | Campo Destino | Descrição |
|-----------|--------------|-----------|
| `tegp.cd_turma_escola` | `codigo_turma` | FK lógica → `turma_programa` |
| `gcc.cd_componente_curricular` | `codigo_componente_curricular` | FK lógica → `componente_curricular_programa` |
| `LTRIM(RTRIM(cc.dc_componente_curricular))` | `nome_componente_curricular` | Desnormalizado para evitar JOIN |

**JOINs:** `turma_escola_grade_programa → escola_grade → grade_componente_curricular → componente_curricular`, mais `turma_escola` para os filtros de tipo e situação.

**Filtros EOL:** `te.cd_tipo_turma = 3`, `te.st_turma_escola IN ('O','A','C','E')`, `tegp.dt_fim IS NULL`, `cc.dt_cancelamento IS NULL` — **sem filtro `IN (...)` por componente**, traz todos os componentes vinculados.

---

## Fase 5 — MatriculaTurmaPrograma

SQL: `SQL_MATRICULA_TURMA_PROGRAMA` em `services.py`. DTO: `MatriculaTurmaProgramaIn`.

| Campo EOL | Campo Destino | Descrição |
|-----------|--------------|-----------|
| `vm.cd_aluno` | `codigo_aluno` | FK lógica → `PEDAGOGICO_DB` (de `v_matricula_cotic`) |
| `m.cd_turma_escola` | `codigo_turma` | FK lógica → `turma_programa` (de `matricula_turma_escola`) |
| `gcc.cd_componente_curricular` | `codigo_componente_curricular` | FK lógica → `componente_curricular_programa` |
| `LTRIM(RTRIM(cc.dc_componente_curricular))` | `nome_componente_curricular` | Desnormalizado |
| `m.cd_situacao_aluno` (alias `cd_situacao_aluno`) | `codigo_situacao_matricula` | Situação **turma-específica** |
| *(derivado via `SituacaoMatricula.get_descricao()` em `to_domain()`)* | `descricao_situacao_matricula` | Texto resolvido em Python |
| `vm.dt_status_matricula` (alias `dt_matricula`) | `data_matricula` | `DateTimeField` (preserva horário) |
| `m.dt_situacao_aluno` (alias `dt_situacao`) | `data_situacao` | Data da situação |
| `te.an_letivo` | `ano_letivo` | Desnormalizado da turma |
| `CAST(te.cd_escola AS VARCHAR(20))` | `codigo_ue` | Desnormalizado da turma |
| `CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20))` | `codigo_dre` | Desnormalizado da turma |
| *(derivado via `ComponenteCurricularEOL.categoria(codigo_componente_curricular)`)* | `categoria` | `"PAP"`, `"PAEE"` ou `"OUTROS"` |

**JOINs:**
- `matricula_turma_escola m` ⟕ `v_matricula_cotic vm`
- `turma_escola te` ⟕ `v_cadastro_unidade_educacao vcue`
- `turma_escola_grade_programa → escola_grade → grade_componente_curricular → componente_curricular`

**Filtros EOL:** `te.cd_tipo_turma = 3`, `te.st_turma_escola IN ('O','A','C','E')`, `tegp.dt_fim IS NULL`, `cc.dt_cancelamento IS NULL`, `m.cd_situacao_aluno IN (1, 5, 6, 10, 13)`.

---

## Fase 6 — MatriculaTurmaProgramaHistorico

SQL: `SQL_MATRICULA_TURMA_PROGRAMA_HISTORICO` em `services.py`. DTO: `MatriculaTurmaProgramaIn` (mesmo da Fase 5).

Equivalente à Fase 5, mas lendo do histórico:

- Tabela origem: `historico_matricula_turma_escola` + `v_historico_matricula_cotic` (com `WITH (NOLOCK)`)
- Coluna `dt_situacao` retornada como `NULL` (não há equivalente no histórico)
- `cd_situacao_aluno` derivado de `CAST(vm.st_matricula AS SMALLINT)`
- **Filtros EOL:** `te.cd_tipo_turma = 3`, `te.st_turma_escola IN ('O','A','C')` (sem `E`), `vm.st_matricula IN ('1','5')`, `tegp.dt_fim IS NULL`, `cc.dt_cancelamento IS NULL`
- `data_matricula` no destino é **nullable** (modelo `MatriculaTurmaProgramaHistorico`)

---

## Fase 7 — AlunoPapAnoLetivo

SQL: `SQL_ALUNO_PAP_ANO_LETIVO` em `services.py`. DTO: `AlunoPapAnoLetivoIn`.

Visão pré-agregada (live) para o endpoint `alunos-pap/{anoLetivo}`.

| Campo EOL | Campo Destino |
|-----------|---------------|
| `vm.cd_aluno` | `codigo_aluno` |
| `m.cd_turma_escola` | `codigo_turma` |
| `gcc.cd_componente_curricular` | `codigo_componente_curricular` |
| `te.an_letivo` | `ano_letivo` |
| `CAST(te.cd_escola AS VARCHAR(20))` | `codigo_ue` |
| `CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20))` | `codigo_dre` |

**Filtros EOL:** `te.cd_tipo_turma = 3`, `gcc.cd_componente_curricular IN (ComponenteCurricularEOL.codigos_pap_vigentes())` (apenas PAP vigentes, sem PAEE nem legados), `te.st_turma_escola IN ('O','A','C')`, `tegp.dt_fim IS NULL`, `cc.dt_cancelamento IS NULL`, `m.cd_situacao_aluno = 1` (apenas ativos).

---

## Fase 8 — AlunoPapAnoLetivoHistorico

SQL: `SQL_ALUNO_PAP_ANO_LETIVO_HISTORICO` em `services.py`. DTO: `AlunoPapAnoLetivoIn` (mesmo da Fase 7).

Equivalente à Fase 7 lendo do histórico (`v_historico_matricula_cotic`,
`historico_matricula_turma_escola` com `WITH (NOLOCK)`).

**Filtros EOL:** `te.cd_tipo_turma = 3`, `gcc.cd_componente_curricular IN (ComponenteCurricularEOL.codigos_pap_vigentes())`, `te.st_turma_escola IN ('O','A','C')`, `tegp.dt_fim IS NULL`, `cc.dt_cancelamento IS NULL`, `vm.st_matricula IN ('1','5')`.
