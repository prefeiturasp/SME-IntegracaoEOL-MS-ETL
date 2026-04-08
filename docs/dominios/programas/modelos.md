# Glossário de Modelos do Domínio Programas

Estes modelos residem em `apps/programas/models.py` e são persistidos no banco `programas_db` (PostgreSQL).

---

## 1. TipoPrograma

Subtipos de programa do EOL (`cd_tipo_programa`), agrupados por categoria.
O `id` preserva o mesmo valor do EOL — nenhum mapeamento adicional no ETL.

- **Tabela**: `tipo_programa`
- **PK**: `id` (`IntegerField` — mesmo valor de `cd_tipo_programa` do EOL)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `codigo_tipo_programa` | `IntegerField` (PK) | `cd_tipo_programa` do EOL |
| `nome` | `CharField(100)` | Nome do tipo de programa |
| `categoria` | `CharField(10)` | `"PAP"` ou `"PAEE"` |
| `ativo` | `BooleanField` | Indica se o tipo está ativo |

**Dados esperados (seed):**

| id | Nome | Categoria |
|----|------|-----------|
| 649 | PAP Recuperação | PAP |
| 650 | PAP Colaborativo | PAP |
| 656 | PAEE SRM | PAEE |
| 657 | PAEE Colaborativo | PAEE |
| 658 | PAEE Itinerante | PAEE |

---

## 2. ComponenteCurricularPrograma

Camada de configuração que substitui as constantes hardcoded
`IDS_COMPONENTES_CURRICULARES_PAP_NOVO` e `COMPONENTE_CURRICULAR_ID_SRM` do Pedagogico-API.

- **Tabela**: `componente_curricular_programa`
- **PK**: `id` (auto — `BigAutoField`)
- **Unique**: `codigo_componente_curricular`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `codigo_componente_curricular` | `BigIntegerField` (unique) | `cd_componente_curricular` do EOL |
| `nome_componente_curricular` | `CharField(200)` | `dc_componente_curricular` do EOL |
| `categoria` | `CharField(10)` | `"PAP"` ou `"PAEE"` |
| `vigente` | `BooleanField` | `True` = ativo; `False` = legado |
| `data_inicio` | `DateField` | Início da vigência |
| `data_fim` | `DateField` (nullable) | Fim da vigência; `NULL` = sem prazo |

**Dados esperados (seed — PAP vigentes):**

| codigo | Nome |
|--------|------|
| 1322 | PAP Recuperação de Aprendizagens |
| 1770 | PAP Projeto Colaborativo |
| 1804 | PAP 2º Ano Alfabetização |
| 1805 | PAP 2º Ano Colaborativo Alfabetização |

**Dados esperados (seed — PAP legados):**

| codigo | Nome |
|--------|------|
| 1033 | Recuperação Paralela Matemática |
| 1051 | Recuperação Paralela Ciências |
| 1052 | Recuperação Paralela Geografia |
| 1053 | Recuperação Paralela História |
| 1054 | Recuperação Paralela Português |

**Dados esperados (seed — PAEE vigente):**

| codigo | Nome |
|--------|------|
| 1030 | Sala de Recursos Multifuncionais |

---

## 3. TurmaPrograma

Turmas de programa (`cd_tipo_turma=3`) extraídas do EOL. Tabela central do domínio —
referência lógica para `TurmaProgramaComponenteCurricular` e `MatriculaTurmaPrograma`.

- **Tabela**: `turma_programa`
- **PK**: `id` (auto — `BigAutoField`)
- **Unique**: `codigo_turma`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `codigo_turma` | `BigIntegerField` (unique) | `cd_turma_escola` do EOL |
| `nome_turma` | `CharField(200)` | `dc_turma_escola` do EOL |
| `codigo_ue` | `CharField(20)` | `escola.cd_escola` do EOL |
| `codigo_dre` | `CharField(20)` | `cd_unidade_administrativa_referencia` |
| `ano_letivo` | `SmallIntegerField` | `an_letivo` do EOL |
| `tipo_turno` | `SmallIntegerField` (nullable) | `cd_tipo_turno` do EOL |
| `descricao_turno` | `CharField(100)` (nullable) | `dc_exibicao_portal` — desnormalizado |
| `situacao` | `CharField(1)` | `O`=Organizada, `A`=Não Organizada, `C`=Concluída, `E`=Extinta |
| `codigo_tipo_programa` | `IntegerField` | FK lógica → `tipo_programa.id` |
| `categoria` | `CharField(10)` | `"PAP"` ou `"PAEE"` — desnormalizado para filtros diretos |
| `criado_em` | `DateTimeField` (auto) | Criação do registro |
| `atualizado_em` | `DateTimeField` (nullable) | Última atualização pelo ETL |

**Índices:**

| Nome | Campo(s) |
|------|----------|
| `idx_turma_prog_ano` | `ano_letivo` |
| `idx_turma_prog_ue` | `codigo_ue` |
| `idx_turma_prog_categoria` | `categoria` |

---

## 4. TurmaProgramaComponenteCurricular

Componentes curriculares que uma turma de programa efetivamente oferece.
Equivale à cadeia `turma_escola_grade_programa → grade → grade_componente_curricular` do EOL.

- **Tabela**: `turma_programa_componente_curricular`
- **PK**: `id` (auto — `BigAutoField`)
- **Unique constraint**: `(codigo_turma, codigo_componente_curricular)`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `codigo_turma` | `BigIntegerField` | FK lógica → `turma_programa.codigo_turma` |
| `codigo_componente_curricular` | `BigIntegerField` | FK lógica → `componente_curricular_programa` |
| `nome_componente_curricular` | `CharField(200)` | `dc_componente_curricular` — desnormalizado |
| `criado_em` | `DateTimeField` (auto) | Criação do registro |

**Índices:**

| Nome | Campo(s) |
|------|----------|
| `idx_turma_prog_comp_turma` | `codigo_turma` |

---

## 5. MatriculaTurmaPrograma

Matrículas de alunos em turmas de programa, por componente curricular. Tabela principal
para consultas dos endpoints PAP/PAEE do Pedagogico-API.

- **Tabela**: `matricula_turma_programa`
- **PK**: `id` (auto — `BigAutoField`)
- **Unique constraint**: `(codigo_turma, codigo_aluno, codigo_componente_curricular)`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `codigo_aluno` | `BigIntegerField` | `cd_aluno` do EOL — FK lógica para `PEDAGOGICO_DB` |
| `codigo_turma` | `BigIntegerField` | FK lógica → `turma_programa.codigo_turma` |
| `codigo_componente_curricular` | `BigIntegerField` | FK lógica → `componente_curricular_programa` |
| `nome_componente_curricular` | `CharField(200)` | `dc_componente_curricular` — desnormalizado |
| `codigo_situacao_matricula` | `SmallIntegerField` | `st_matricula` do EOL |
| `descricao_situacao_matricula` | `CharField(50)` | Ex: `"Ativo"`, `"Concluído"` — desnormalizado |
| `data_matricula` | `DateField` | `dt_status_matricula` do EOL |
| `data_situacao` | `DateField` (nullable) | `dt_situacao_aluno` do EOL |
| `ano_letivo` | `SmallIntegerField` | Desnormalizado da turma |
| `codigo_ue` | `CharField(20)` | Desnormalizado da turma |
| `codigo_dre` | `CharField(20)` | Desnormalizado da turma |
| `categoria` | `CharField(10)` | `"PAP"` ou `"PAEE"` — desnormalizado para filtros diretos |
| `criado_em` | `DateTimeField` (auto) | Criação do registro |
| `atualizado_em` | `DateTimeField` (nullable) | Última atualização pelo ETL |

**Valores de `codigo_situacao_matricula`:**

| Código | Descrição |
|--------|-----------|
| 1 | Ativo |
| 5 | Concluído |
| 6 | Pend. Rematrícula |
| 10 | Rematriculado |
| 13 | Sem continuidade |

**Índices:**

| Nome | Campo(s) |
|------|----------|
| `idx_matricula_aluno` | `codigo_aluno` |
| `idx_matricula_ano` | `ano_letivo` |
| `idx_matricula_ue` | `codigo_ue` |
| `idx_matricula_categoria` | `categoria` |
