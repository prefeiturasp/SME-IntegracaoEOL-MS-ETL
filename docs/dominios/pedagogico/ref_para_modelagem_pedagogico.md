# Documentação Técnica — ETL PEDAGOGICO_DB
## Model_IN, Model_OUT e Mapeamento de Transformação

## SEÇÃO 1 — Resumo do Fluxo ETL (Confirmar)

### 1.1 Visão Geral

```
[Scheduler: CRON / AWX / Rundeck]
         |
         v
[ETLJobController]
   Ponto único de entrada. Inicia o ciclo de vida da execução.
   Gera execution_id. Registra início no SINC_REC_DB.
         |
         v
[LeitorEOLService]
   Lê incrementalmente do SE1426 via réplica Cimarron (read-only).
   Usa watermark (timestamp ou ID sequencial) para saber de onde continuar.
   Watermark lido do SINC_REC_DB antes de começar.
         |
         v
[ETLTaskPublisher]
   Divide os registros em batches.
   Publica cada batch como task no broker KeyDB.
         |
         v
[Celery Workers] (paralelos)
   Cada worker recebe um batch.
   Executa: transformação (Model_IN → Model_OUT) + persistência.
         |
         v
[UpsertTables]
   Persiste no PEDAGOGICO_DB via ON CONFLICT DO UPDATE.
   Nunca DELETE + INSERT. Operação idempotente.
         |
         v
[SyncRecordService]
   Atualiza watermark no SINC_REC_DB (SOMENTE após sucesso total).
   Registra: registros lidos, escritos, duração, status.
```

### 1.2 Bancos Envolvidos

| Banco | Tipo | Papel no ETL | 
|-------|------|--------------|
| SE1426 (réplica Cimarron) | SQL Server 2008 | Fonte — leitura apenas
| ApiEolConnection | PostgreSQL (legado) | Fonte auxiliar — dados normalizados legado
| PEDAGOGICO_DB | PostgreSQL (novo) | Destino — escrita via upsert
| SINC_REC_DB | PostgreSQL (auditoria) | Controle — watermark, logs de execução

### 1.3 Frequência e Janela

| Parâmetro | Valor |
|-----------|-------|
| Execução normal | 1x/dia, janela D-1 |
| Execução de troubleshooting | até 2ª execução, mediante autorização |
| Janela de dados | Registros do dia anterior (D-1) |
| Reprocessamento | Permitido — idempotência garante segurança |

### 1.4 Princípio de Modelagem (Confirmar)

> Cada tabela no PEDAGOGICO_DB materializa o resultset de um ou mais endpoints da API. O microsserviço faz SELECT simples. O ETL faz todo o trabalho pesado.

---

## SEÇÃO 2 — Correções em Relação à Documentação Anterior (HU-26)

> Estas correções são o motivo pelo qual o HU-26 **não deve ser usado como referência de modelagem**.

| Dimensão | HU-26 (INCORRETO) | Nova Modelagem (A CONFIRMAR) |
|----------|-------------------|--------------------------|
| Ponto de partida | Tabelas do SE1426 | Resultsets dos endpoints |
| Número de tabelas | 20 | **7** |
| Normalização | 3NF — entidades separadas | Desnormalização controlada |
| Descrições | Tabelas de catálogo separadas (`etapa_ensino`, `serie_ensino`...) | **Inline** nas tabelas principais |
| Lógica no microsserviço | JOINs via Django ORM | `SELECT * WHERE chave = ?` — zero JOIN |
| Lógica no ETL | Mínima | **Todo o trabalho pesado** |
| FK físicas | Presentes entre tabelas | **ZERO FK física — nem dentro do domínio** |
| FK cruzadas | Tentativa de FK física | FK lógica (valor em VARCHAR, sem constraint) |
| Django models | Gerados com ForeignKey() | **Sem ForeignKey() — sem related_name — sem on_delete** |
| Chave de upsert | Não definida | Definida por tabela (ver Seção 4) |

### 2.1 Por que não usar FK física ( A CONFIRMAR )

**Razão técnica:** PostgreSQL não suporta FK entre bancos diferentes. Como cada domínio tem seu próprio banco, `turma_codigo` (domínio Institucional) e `professor` (domínio Professor) **não podem ter FK física**.

**Razão arquitetural:** O PEDAGOGICO_DB é um read model — uma projeção materializada, não um banco relacional normalizado. A integridade referencial é responsabilidade do ETL (via SE1426 como fonte de verdade), não do banco.

---

## SEÇÃO 3 — Model_IN (Entrada — dados do SE1426 / ApiEolConnection)

> O **Model_IN** representa os dados exatamente como chegam das queries de origem, antes de qualquer transformação. Em Python, serão dicionários ou dataclasses correspondentes ao resultset de cada query.

### 3.1 Fontes de Dados

O ETL lê de duas fontes distintas que precisam de engines SQLAlchemy separados:

```
Engine 1: SE1426 (EolConnection) → SQL Server via pyodbc
Engine 2: ApiEolConnection       → PostgreSQL via psycopg2
```

---

### Pipeline A — Componentes por Turma (Shape A)

**Alimenta:** `componente_curricular_por_turma` + `componente_curricular_agrupamento`  
**Endpoints atendidos:** 1, 2, 3, 9, 10, e validações 5, 8, 17

Este pipeline requer **3 queries coordenadas**:

#### Query A1 — ObterComponentesPorTurmasAsync (EolConnection)

```sql
-- Campos retornados (aliases usados pelo C# e que virarão o Model_IN em Python)
Codigo          INTEGER     -- cd_componente_curricular (pode ser do pai COALESCE)
Descricao       VARCHAR     -- dc_componente_curricular (pode ser do pai COALESCE)
AnoTurma        VARCHAR     -- sg_resumida_serie (ex: "1", "2", "EI")
TurnoTurma      INTEGER     -- qt_hora_duracao (horas de duração)
AnoLetivo       INTEGER     -- an_letivo
TurmaCodigo     VARCHAR     -- cd_turma_escola
Professor       VARCHAR     -- cd_registro_funcional (SME) ou cd_cpf_pessoa (Externo)
```

> **Obs A1:** A query usa UNION ALL (professor SME + professor externo). O campo `Professor` pode ser RF (SME) ou CPF (externo). O ETL deve normalizar isso no transform.

> **Obs A2:** Os campos `regencia`, `planejamentoRegencia`, `territorioSaber`, `exibirComponenteEOL`, `codigoComponenteTerritorioSaber`, `codigoComponenteCurricularPai` **NÃO vêm desta query**. Vêm da Query A2 (join no transform).

#### Query A2 — ObterDisciplinasAsync (ApiEolConnection)

```sql
-- Fonte: ApiEolConnection (PostgreSQL legado)
SELECT ccp.Id,
    cc.IdComponenteCurricular,
    cc.EhRegencia,          -- boolean
    cc.EhTerritorio,        -- boolean → territorioSaber
    cc.Descricao,
    ccp.idcomponentecurricularpai,
    ccp.vigencia
FROM ComponenteCurricular cc
LEFT JOIN componentecurricularpai ccp ON cc.idcomponentecurricular = ccp.idcomponentecurricular
```

**Model_IN A2:**

```
IdComponenteCurricular    INTEGER   -- chave de join com Query A1
EhRegencia                BOOLEAN   -- → regencia no Model_OUT
EhTerritorio              BOOLEAN   -- → territorioSaber no Model_OUT
CodigoPai                 INTEGER   -- → codigoComponenteCurricularPai (pode ser NULL)
```

#### Query A3 — BuscarDisciplinasRegenciaAsync (ApiEolConnection)

```sql
SELECT IdComponenteCurricular, Turno, Ano
FROM RegenciaComponenteCurricular
```

**Model_IN A3:**

```
IdComponenteCurricular    INTEGER   -- chave de join
Turno                     INTEGER   -- turno da regência
Ano                       INTEGER   -- ano da regência (usado para filtrar planejamentoRegencia)
```

> **Obs A3:** `planejamentoRegencia` é calculado cruzando A1 + A3 — se o componente da turma aparece em RegenciaComponenteCurricular com o turno/ano correspondente.

#### Query A4 — BuscarComponentesCurricularesPAP (ApiEolConnection)

```sql
SELECT id AS Id FROM componentecurricularpap
```

**Model_IN A4:**

```
Id    INTEGER   -- lista de IDs de componentes PAP (usado para exibirComponenteEOL)
```

> **Obs A4:** `exibirComponenteEOL` é `True` quando o `Codigo` do componente **NÃO está** na lista PAP. Regra de negócio do domínio.

---

### Pipeline B — Regência por Ano de Turma (Shape B)

**Alimenta:** `componente_curricular_regencia`  
**Endpoint atendido:** 4

#### Query B1 — ObterComponentesCurricularesTerritorioAtribuidos (EolConnection)

```
CodigoComponenteCurricular    INTEGER   -- cd_componente_curricular → codigo
DescricaoComponenteCurricular VARCHAR   -- dc_componente_curricular → descricao
AnoTurma                      VARCHAR   -- sg_resumida_serie → ano_turma
anoletivo                     INTEGER   -- an_letivo → ano_letivo
TurmaCodigo                   VARCHAR   -- cd_turma_escola → turma_codigo
rfProfessor                   VARCHAR   -- cd_registro_funcional ou cd_cpf_pessoa → professor
CodigoTerritorioSaber         INTEGER   -- cd_territorio_saber → codigo_componente_territorio_saber
DescricaoTerritorioSaber      VARCHAR   -- dc_territorio_saber (interno, não vai no endpoint)
CodigoExperienciaPedagogica   INTEGER   -- cd_experiencia_pedagogica (interno)
DescricaoExperienciaPedagogica VARCHAR  -- dc_experiencia_pedagogica (interno)
dataAtribuicao                DATETIME  -- dt_atribuicao_aula → inicio_atribuicao
DataFimTurma                  DATETIME  -- dt_fim_turma → fim_atribuicao
AnoAtribuicao                 INTEGER   -- an_atribuicao (controle interno)
AtribuicaoExterna             INTEGER   -- 0=SME, 1=externo (controle interno)
dataDisponibilizacao          DATETIME  -- MAX(dt_disponibilizacao_aulas) (controle)
CodigoMotivoDisponibilizacao  INTEGER   -- MAX(cd_motivo_disponibilizacao) (controle)
TipoEscola                    VARCHAR   -- tp_escola → tipo_escola
TurnoTurma                    INTEGER   -- qt_hora_duracao → turno_turma
```

> **Obs B1:** Esta query usa UNION ALL (professor SME + professor externo). Mesma lógica do Pipeline A.

> **Obs B2:** `territorioSaber` no endpoint é derivado da presença de `CodigoTerritorioSaber` (valor não nulo = True).

> **Obs B3:** `componentePlanejamentoRegencia` precisa ser calculado cruzando com Query A3 (RegenciaComponenteCurricular).

---

### Pipeline C — Lista Simples de Componentes (Shape C)

**Alimenta:** `componente_curricular`  
**Endpoint atendido:** 11

#### Query C1 — ListarNaoCanceladasAsync (EolConnection)

```sql
SELECT cd_componente_curricular AS Codigo,
       RTRIM(LTRIM(dc_componente_curricular)) AS Descricao
FROM componente_curricular
WHERE dt_cancelamento IS NULL
```

**Model_IN C1:**

```
Codigo      INTEGER   -- cd_componente_curricular → codigo
Descricao   VARCHAR   -- dc_componente_curricular → descricao
```

> **Obs C1:** Esta é a query mais simples. 1:1 com Model_OUT. Zero transformação.

---

### Pipeline D — Dados Aula Turma (Shape D)

**Alimenta:** `dados_aula_turma`  
**Endpoint atendido:** 12

#### Query D1 — ObterDadosComponentesCurricularesRegenciaPorUeEAnoLetivoAsync (EolConnection)

```
ComponenteCurricularCodigo       VARCHAR   -- cd_componente_curricular → componente_codigo
ComponenteCurricularDescricao    VARCHAR   -- dc_componente_curricular → componente_descricao
TurmaCodigo                      VARCHAR   -- cd_turma_escola → turma_codigo
DataInicioTurma                  DATETIME  -- dt_inicio_turma → data_inicio_turma
```

> **Obs D1:** Parâmetros desta query: `ueCodigo`, `anoLetivo`, `componentesCurriculares`. O ETL precisa estrategizar a ingestão incremental (por UE ou por anoLetivo).

---

### Pipeline E — Componentes por Ano Letivo (Shape E)

**Alimenta:** `componente_curricular_por_ano_letivo`  
**Endpoints atendidos:** 16, e validações 6, 7

**Query E1 — `ObterComponentesCurricularesEAnosTurmaApiEolPorAnoLetivo` (EolConnection)**

Localizada em `ComponenteCurricularController.txt` linha 1097. Usa CTE `componentesAnoTurmas`.  
Parâmetro: `@AnoLetivo` (INTEGER).  
Filtros finais: `modalidade > 0 AND CodigoAnoTurma IS NOT NULL AND CodigoSerieEnsino IS NOT NULL`.

**Model_IN E:**

```
CodigoComponenteCurricular   INTEGER   -- IIF(pcc.cd_componente_curricular, cc.cd_componente_curricular)
DescricaoComponenteCurricular VARCHAR  -- IIF(pcc.dc_componente_curricular, cc.dc_componente_curricular)
CodigoAnoTurma               VARCHAR   -- serie_ensino.sg_resumida_serie
DescricaoSerieEnsino         VARCHAR   -- serie_ensino.sg_serie_ensino (LTRIM/RTRIM)
CodigoSerieEnsino            INTEGER   -- serie_ensino.cd_serie_ensino
Modalidade                   INTEGER   -- CASE cd_etapa_ensino: 1,10→1(EI) | 2,3,7,11→3(EJA) | tp_escola=13→4(CIEJA) | 4,5,12,13→5(EF) | 6,7,8,9,14,17→6(EM)
```

> **Obs:** `CodigoComponenteCurricular` prioriza o componente do programa (`pcc`) quando presente — mesma lógica do Pipeline A. A `Modalidade` é **calculada** no SE1426 via CASE, não vem de coluna direta.

---

### Pipeline F — Agrupamentos Território Saber

**Alimenta:** `agrupamento_atribuicao_territorio_saber` + `componente_curricular_agrupamento`  
**Endpoints atendidos:** 13, 14, 15

#### Query F1 — ObterAgrupamentosTerritorioSaber (ApiEolConnection)

```
codagrupamento                                    INTEGER   -- PK da tabela fonte
codterritoriosaber                                INTEGER   -- código território saber
codexperienciapedagogica                          INTEGER   -- código experiência pedagógica
dtinicioatribuicao                                DATETIME  -- início da atribuição
anoatribuicao                                     INTEGER   -- ano letivo da atribuição
dtfimatribuicao                                   DATETIME  -- fim da atribuição (nullable)
dtfimturma                                        DATETIME  -- fim da turma (nullable)
rfprofessor                                       VARCHAR   -- RF do professor
codturma                                          VARCHAR   -- código da turma
codcomponentescurriculares                        VARCHAR   -- CSV de códigos "1,2,3"
anoletivo                                         INTEGER   -- ano letivo
codmotivodisponibilizacao                         INTEGER   -- código motivo (nullable)
descterritoriosaber                               VARCHAR   -- descrição território (inline)
descexperienciapedagogica                         VARCHAR   -- descrição exp. pedagógica (inline)
encerramento_atribuicao_agrupamento_atualizado    BOOLEAN   -- flag de encerramento
criado_em                                         DATETIME  -- timestamp de criação
alterado_em                                       DATETIME  -- timestamp de atualização (watermark)
```

> **Obs F1:** O campo `codcomponentescurriculares` é um **CSV de inteiros** (ex: `"512,513,514"`). O ETL deve fazer `string.split(',')` e inserir uma linha por código na tabela `componente_curricular_agrupamento`.

> **Obs F2:** O watermark desta pipeline usa o campo `alterado_em`. Registros novos e atualizados têm `alterado_em > último_watermark`.

---

## SEÇÃO 4 — Model_OUT (Saída — PEDAGOGICO_DB)

> O **Model_OUT** define exatamente como os dados devem ser persistidos no PostgreSQL. Cada tabela materializa o resultset de um ou mais endpoints. **Zero FK física. Zero JOIN no microsserviço.**

### Convenções Gerais

- Todas as tabelas têm `id SERIAL PRIMARY KEY` (surrogate — uso interno, não exposto na API)
- Campos de negócio com unicidade têm `UNIQUE` constraint ou fazem parte da chave de upsert
- Nomes em `snake_case`, português normalizado, sem prefixos legados (`cd_`, `dc_`, `st_`)
- Não há `ForeignKey()`, `related_name`, `on_delete` em nenhum model
- Campos de controle ETL ficam no SINC_REC_DB, não nas tabelas de domínio
- Campos que o endpoint não retorna diretamente mas são necessários para filtro de query podem existir na tabela (ex: `ano_letivo`, `ue_codigo`)
- **Todas as tabelas têm `criado_em`, `alterado_em` e `transferido_em`** — campos de auditoria ETL, nunca retornados pela API:
  - `criado_em`: `DEFAULT NOW()` no INSERT — **nunca atualizado** no ON CONFLICT
  - `alterado_em`: `NOW()` no ON CONFLICT — rastreia quando o **dado** mudou
  - `transferido_em`: `NOW()` em toda execução ETL (INSERT e ON CONFLICT) — rastreia quando o ETL **tocou** o registro, independente de mudança. Permite cruzar com SINC_REC_DB ("o ETL rodou às 02:00 — registros com `transferido_em` anterior a isso não foram alcançados nessa carga")
  - Exceção Tabela 7: `criado_em` e `alterado_em` **vêm da fonte** (ApiEolConnection); `transferido_em` ainda é ETL-controlado

---

### Tabela 1 — `componente_curricular`

**Endpoint:** 11 — `GET /api/v1/componentes-curriculares`  
**Shape:** C — lista simples  
**Pipeline fonte:** C (Query C1 — EolConnection)

| Coluna | Tipo PostgreSQL | Nullable | Descrição |
|--------|----------------|----------|-----------|
| `id` | `SERIAL` | NOT NULL | PK surrogate — uso interno |
| `codigo` | `INTEGER` | NOT NULL | cd_componente_curricular — chave de negócio |
| `descricao` | `VARCHAR(300)` | NOT NULL | dc_componente_curricular |
| `criado_em` | `TIMESTAMP` | NOT NULL | Timestamp de criação pelo ETL — `DEFAULT NOW()` |
| `alterado_em` | `TIMESTAMP` | NOT NULL | Timestamp da última atualização pelo ETL |
| `transferido_em` | `TIMESTAMP` | NOT NULL | Timestamp da última vez que o ETL tocou o registro |

**Constraints:**
```sql
PRIMARY KEY (id)
UNIQUE (codigo)
```

**Chave de Upsert:**
```sql
ON CONFLICT (codigo) DO UPDATE SET
  descricao      = EXCLUDED.descricao,
  alterado_em    = NOW(),
  transferido_em = NOW()
-- criado_em NÃO é atualizado no ON CONFLICT
```

**Query de leitura pelo microsserviço:**
```sql
SELECT codigo, descricao FROM componente_curricular ORDER BY descricao;
```

> **Obs:** Shape C (endpoint 11) retorna apenas `{"codigo": 0, "descricao": "string"}`. Tabela extremamente simples.

---

### Tabela 2 — `componente_curricular_por_turma`

**Endpoints:** 1, 2, 3, 9, 10 (e insumo para validações 5, 8, 17)  
**Shape:** A — shape completo  
**Pipeline fonte:** A (Queries A1 + A2 + A3 + A4)

| Coluna | Tipo PostgreSQL | Nullable | Descrição | Origem no Model_IN |
|--------|----------------|----------|-----------|-------------------|
| `id` | `SERIAL` | NOT NULL | PK surrogate | — |
| `codigo` | `INTEGER` | NOT NULL | Código do componente | A1: `Codigo` |
| `codigo_componente_territorio_saber` | `INTEGER` | NULL | Código do território saber | Calculado via F1 ou A2 |
| `codigo_componente_curricular_pai` | `INTEGER` | NULL | Código do componente pai | A2: `CodigoPai` |
| `descricao` | `VARCHAR(300)` | NOT NULL | Descrição do componente | A1: `Descricao` |
| `regencia` | `BOOLEAN` | NOT NULL | É componente de regência? | A2: `EhRegencia` |
| `planejamento_regencia` | `BOOLEAN` | NOT NULL | Está na tabela de planejamento de regência? | A3: cruzamento |
| `territorio_saber` | `BOOLEAN` | NOT NULL | É território do saber? | A2: `EhTerritorio` |
| `turma_codigo` | `VARCHAR(20)` | NULL | Código da turma | A1: `TurmaCodigo` |
| `exibir_componente_eol` | `BOOLEAN` | NOT NULL | Não é PAP? | A4: `Id NOT IN lista_pap` |
| `professor` | `VARCHAR(20)` | NULL | RF (SME) ou CPF (externo) do professor | A1: `Professor` |
| `ano_letivo` | `INTEGER` | NOT NULL | Ano letivo — filtro ETL | A1: `AnoLetivo` |
| `criado_em` | `TIMESTAMP` | NOT NULL | Timestamp de criação pelo ETL — `DEFAULT NOW()` | — |
| `alterado_em` | `TIMESTAMP` | NOT NULL | Timestamp da última atualização pelo ETL | — |
| `transferido_em` | `TIMESTAMP` | NOT NULL | Timestamp da última vez que o ETL tocou o registro | — |

**Constraints:**
```sql
PRIMARY KEY (id)
UNIQUE (codigo, turma_codigo, COALESCE(professor, ''))
INDEX ON (turma_codigo)
INDEX ON (codigo)
INDEX ON (ano_letivo)
```

**Chave de Upsert:**
```sql
ON CONFLICT (codigo, turma_codigo, COALESCE(professor, ''))
DO UPDATE SET
  codigo_componente_territorio_saber = EXCLUDED.codigo_componente_territorio_saber,
  codigo_componente_curricular_pai   = EXCLUDED.codigo_componente_curricular_pai,
  descricao                          = EXCLUDED.descricao,
  regencia                           = EXCLUDED.regencia,
  planejamento_regencia              = EXCLUDED.planejamento_regencia,
  territorio_saber                   = EXCLUDED.territorio_saber,
  exibir_componente_eol              = EXCLUDED.exibir_componente_eol,
  ano_letivo                         = EXCLUDED.ano_letivo,
  alterado_em                        = NOW(),
  transferido_em                     = NOW()
-- criado_em NÃO é atualizado no ON CONFLICT
```

**Query de leitura pelo microsserviço (exemplo endpoint 1):**
```sql
SELECT codigo, codigo_componente_territorio_saber, codigo_componente_curricular_pai,
       descricao, regencia, planejamento_regencia, territorio_saber,
       turma_codigo, exibir_componente_eol, professor
FROM componente_curricular_por_turma
WHERE turma_codigo = :codigo_turma
  AND professor = :login;
```

> **Obs 1:** `codigosTerritoriosAgrupamento` é um array no JSON. **NÃO vai nesta tabela** — vai na tabela companion `componente_curricular_agrupamento`.

> **Obs 2:** A chave de upsert usa `COALESCE(professor, '')` porque professor pode ser NULL (componente sem professor atribuído). Isso evita que `NULL != NULL` cause duplicatas.

> **Obs 3:** `codigo_componente_territorio_saber` pode precisar de confirmação sobre como é derivado — aparentemente vem do cruzamento com os agrupamentos ou do campo `CodigoTerritorioSaber` da query de território.

---

### Tabela 3 — `componente_curricular_agrupamento`

**Descrição:** Tabela companion da Tabela 2. Cada linha representa um item do array `codigosTerritoriosAgrupamento` retornado pelo Shape A.  
**Pipeline fonte:** F (Query F1 — campo `codcomponentescurriculares`, CSV)

| Coluna | Tipo PostgreSQL | Nullable | Descrição | Origem no Model_IN |
|--------|----------------|----------|-----------|-------------------|
| `id` | `SERIAL` | NOT NULL | PK surrogate | — |
| `componente_codigo` | `INTEGER` | NOT NULL | FK lógica para componente_curricular_por_turma.codigo | F1: `codcomponentescurriculares` (split) |
| `turma_codigo` | `VARCHAR(20)` | NOT NULL | Código da turma | F1: `codturma` |
| `codigo_agrupamento` | `INTEGER` | NOT NULL | Código do agrupamento | F1: `codagrupamento` |
| `rf_professor` | `VARCHAR(20)` | NULL | RF do professor | F1: `rfprofessor` |
| `ano_letivo` | `INTEGER` | NOT NULL | Ano letivo | F1: `anoletivo` |
| `criado_em` | `TIMESTAMP` | NOT NULL | Timestamp de criação pelo ETL — `DEFAULT NOW()` | — |
| `alterado_em` | `TIMESTAMP` | NOT NULL | Timestamp da última atualização pelo ETL | — |
| `transferido_em` | `TIMESTAMP` | NOT NULL | Timestamp da última vez que o ETL tocou o registro | — |

**Constraints:**
```sql
PRIMARY KEY (id)
UNIQUE (componente_codigo, turma_codigo, codigo_agrupamento)
INDEX ON (turma_codigo)
INDEX ON (componente_codigo)
```

**Chave de Upsert:**
```sql
ON CONFLICT (componente_codigo, turma_codigo, codigo_agrupamento)
DO UPDATE SET
  rf_professor   = EXCLUDED.rf_professor,
  ano_letivo     = EXCLUDED.ano_letivo,
  alterado_em    = NOW(),
  transferido_em = NOW()
-- criado_em NÃO é atualizado no ON CONFLICT
```

**Query de leitura pelo microsserviço:**
```sql
SELECT codigo_agrupamento
FROM componente_curricular_agrupamento
WHERE componente_codigo = :codigo
  AND turma_codigo = :turma_codigo;
-- Resultado: array de inteiros → "codigosTerritoriosAgrupamento": [0, 1, 2]
```

> **Obs:** O campo `codcomponentescurriculares` no SE1426 é um VARCHAR com CSV de inteiros (`"512,513"`). O ETL faz `split(',')` e gera uma linha por inteiro. Exemplo: para `codturma="T001"` e `codcomponentescurriculares="512,513"`, o ETL insere 2 linhas na tabela com `componente_codigo=512` e `componente_codigo=513`.

---

### Tabela 4 — `componente_curricular_regencia`

**Endpoint:** 4 — `GET /api/v1/componentes-curriculares/anos/{anoTurma}/regencia`  
**Shape:** B  
**Pipeline fonte:** B (Query B1 — EolConnection) + A3 (RegenciaComponenteCurricular)

| Coluna | Tipo PostgreSQL | Nullable | Descrição | Origem no Model_IN |
|--------|----------------|----------|-----------|-------------------|
| `id` | `SERIAL` | NOT NULL | PK surrogate | — |
| `codigo` | `INTEGER` | NOT NULL | Código do componente | B1: `CodigoComponenteCurricular` |
| `codigo_componente_territorio_saber` | `INTEGER` | NULL | Código território saber | B1: `CodigoTerritorioSaber` |
| `descricao` | `VARCHAR(300)` | NOT NULL | Descrição do componente | B1: `DescricaoComponenteCurricular` |
| `territorio_saber` | `BOOLEAN` | NOT NULL | É território do saber | B1: `CodigoTerritorioSaber IS NOT NULL` |
| `tipo_escola` | `VARCHAR(10)` | NULL | Tipo da escola | B1: `TipoEscola` |
| `turno_turma` | `INTEGER` | NULL | Horas de duração do turno | B1: `TurnoTurma` |
| `componente_planejamento_regencia` | `BOOLEAN` | NOT NULL | Está na tabela de planejamento | A3: cruzamento |
| `turma_codigo` | `VARCHAR(20)` | NULL | Código da turma | B1: `TurmaCodigo` |
| `professor` | `VARCHAR(20)` | NULL | RF ou CPF do professor | B1: `rfProfessor` |
| `ano_turma` | `VARCHAR(10)` | NOT NULL | Ano/série da turma (ex: "1", "2") | B1: `AnoTurma` |
| `ano_letivo` | `INTEGER` | NOT NULL | Ano letivo | B1: `anoletivo` |
| `inicio_atribuicao` | `TIMESTAMP` | NULL | Data de início da atribuição | B1: `dataAtribuicao` |
| `fim_atribuicao` | `TIMESTAMP` | NULL | Data de fim (dt_fim_turma) | B1: `DataFimTurma` |
| `criado_em` | `TIMESTAMP` | NOT NULL | Timestamp de criação pelo ETL — `DEFAULT NOW()` | — |
| `alterado_em` | `TIMESTAMP` | NOT NULL | Timestamp da última atualização pelo ETL | — |
| `transferido_em` | `TIMESTAMP` | NOT NULL | Timestamp da última vez que o ETL tocou o registro | — |

**Constraints:**
```sql
PRIMARY KEY (id)
UNIQUE (codigo, turma_codigo, COALESCE(professor, ''), ano_letivo)
INDEX ON (ano_turma, ano_letivo)
INDEX ON (turma_codigo)
```

**Chave de Upsert:**
```sql
ON CONFLICT (codigo, turma_codigo, COALESCE(professor, ''), ano_letivo)
DO UPDATE SET
  descricao                          = EXCLUDED.descricao,
  codigo_componente_territorio_saber = EXCLUDED.codigo_componente_territorio_saber,
  territorio_saber                   = EXCLUDED.territorio_saber,
  tipo_escola                        = EXCLUDED.tipo_escola,
  turno_turma                        = EXCLUDED.turno_turma,
  componente_planejamento_regencia   = EXCLUDED.componente_planejamento_regencia,
  inicio_atribuicao                  = EXCLUDED.inicio_atribuicao,
  fim_atribuicao                     = EXCLUDED.fim_atribuicao,
  alterado_em                        = NOW(),
  transferido_em                     = NOW()
-- criado_em NÃO é atualizado no ON CONFLICT
```

**Query de leitura pelo microsserviço:**
```sql
SELECT codigo, codigo_componente_territorio_saber, NULL AS codigo_componente_curricular_pai,
       descricao, TRUE AS regencia, componente_planejamento_regencia AS planejamento_regencia,
       territorio_saber, tipo_escola, turno_turma, turma_codigo, professor,
       ano_turma, ano_letivo, inicio_atribuicao, fim_atribuicao
FROM componente_curricular_regencia
WHERE ano_turma = :ano_turma
  AND ano_letivo = :ano_letivo;
```

---

### Tabela 5 — `dados_aula_turma`

**Endpoint:** 12 — `GET /api/v1/componentes-curriculares/dados-aula-turma`  
**Shape:** D  
**Pipeline fonte:** D (Query D1 — EolConnection)

| Coluna | Tipo PostgreSQL | Nullable | Descrição | Origem no Model_IN |
|--------|----------------|----------|-----------|-------------------|
| `id` | `SERIAL` | NOT NULL | PK surrogate | — |
| `componente_codigo` | `VARCHAR(20)` | NOT NULL | Código do componente | D1: `ComponenteCurricularCodigo` |
| `componente_descricao` | `VARCHAR(300)` | NOT NULL | Descrição do componente | D1: `ComponenteCurricularDescricao` |
| `turma_codigo` | `VARCHAR(20)` | NOT NULL | Código da turma | D1: `TurmaCodigo` |
| `data_inicio_turma` | `TIMESTAMP` | NULL | Data de início da turma | D1: `DataInicioTurma` |
| `ue_codigo` | `VARCHAR(10)` | NULL | Código da UE — filtro de query | Parâmetro da query |
| `ano_letivo` | `INTEGER` | NULL | Ano letivo — filtro de query | Parâmetro da query |
| `criado_em` | `TIMESTAMP` | NOT NULL | Timestamp de criação pelo ETL — `DEFAULT NOW()` | — |
| `alterado_em` | `TIMESTAMP` | NOT NULL | Timestamp da última atualização pelo ETL | — |
| `transferido_em` | `TIMESTAMP` | NOT NULL | Timestamp da última vez que o ETL tocou o registro | — |

**Constraints:**
```sql
PRIMARY KEY (id)
UNIQUE (componente_codigo, turma_codigo)
INDEX ON (ue_codigo, ano_letivo)
INDEX ON (turma_codigo)
```

**Chave de Upsert:**
```sql
ON CONFLICT (componente_codigo, turma_codigo)
DO UPDATE SET
  componente_descricao = EXCLUDED.componente_descricao,
  data_inicio_turma    = EXCLUDED.data_inicio_turma,
  ue_codigo            = EXCLUDED.ue_codigo,
  ano_letivo           = EXCLUDED.ano_letivo,
  alterado_em          = NOW(),
  transferido_em       = NOW()
-- criado_em NÃO é atualizado no ON CONFLICT
```

**Query de leitura pelo microsserviço:**
```sql
SELECT componente_codigo AS "componenteCurricularCodigo",
       componente_descricao AS "componenteCurricularDescricao",
       turma_codigo AS "turmaCodigo",
       data_inicio_turma AS "dataInicioTurma"
FROM dados_aula_turma
WHERE ue_codigo = :ue_codigo
  AND ano_letivo = :ano_letivo
  AND componente_codigo = ANY(:componentes_curriculares);
```

> **Obs:** O endpoint 12 tem `ueCodigo`, `anoLetivo`, `componentesCurriculares` e `semestre` como parâmetros. Os campos `ue_codigo` e `ano_letivo` são armazenados na tabela para viabilizar essa filtragem sem JOIN.

---

### Tabela 6 — `componente_curricular_por_ano_letivo`

**Endpoints:** 16 + validações 6, 7  
**Shape:** E  
**Pipeline fonte:** E — `ObterComponentesCurricularesEAnosTurmaApiEolPorAnoLetivo` (EolConnection)

| Coluna | Tipo PostgreSQL | Nullable | Descrição | Origem no Model_IN |
|--------|----------------|----------|-----------|-------------------|
| `id` | `SERIAL` | NOT NULL | PK surrogate | — |
| `codigo_componente_curricular` | `INTEGER` | NOT NULL | Código do componente | E: `Codigo` |
| `descricao_componente_curricular` | `VARCHAR(300)` | NOT NULL | Descrição do componente | E: `Descricao` |
| `codigo_ano_turma` | `VARCHAR(10)` | NULL | Código/sigla do ano (ex: "1") | E: `CodigoAnoTurma` |
| `descricao_serie_ensino` | `VARCHAR(200)` | NULL | Descrição da série de ensino | E: `DescricaoSerieEnsino` |
| `codigo_serie_ensino` | `INTEGER` | NULL | Código da série de ensino | E: `CodigoSerieEnsino` |
| `modalidade` | `INTEGER` | NULL | Código da modalidade (1,3,4,5...) | E: `Modalidade` |
| `ano_letivo` | `INTEGER` | NOT NULL | Ano letivo — filtro principal | E: `AnoLetivo` |
| `criado_em` | `TIMESTAMP` | NOT NULL | Timestamp de criação pelo ETL — `DEFAULT NOW()` | — |
| `alterado_em` | `TIMESTAMP` | NOT NULL | Timestamp da última atualização pelo ETL | — |
| `transferido_em` | `TIMESTAMP` | NOT NULL | Timestamp da última vez que o ETL tocou o registro | — |

**Constraints:**
```sql
PRIMARY KEY (id)
UNIQUE (codigo_componente_curricular, ano_letivo, COALESCE(modalidade, 0))
INDEX ON (ano_letivo, modalidade)
INDEX ON (codigo_ano_turma)
```

**Chave de Upsert:**
```sql
ON CONFLICT (codigo_componente_curricular, ano_letivo, COALESCE(modalidade, 0))
DO UPDATE SET
  descricao_componente_curricular = EXCLUDED.descricao_componente_curricular,
  codigo_ano_turma                = EXCLUDED.codigo_ano_turma,
  descricao_serie_ensino          = EXCLUDED.descricao_serie_ensino,
  codigo_serie_ensino             = EXCLUDED.codigo_serie_ensino,
  alterado_em                     = NOW(),
  transferido_em                  = NOW()
-- criado_em NÃO é atualizado no ON CONFLICT
```

> **Obs:** Coluna `modalidade` é calculada pelo ETL a partir do CASE da query — os valores possíveis são: `1` (EI), `3` (EJA), `4` (CIEJA), `5` (EF), `6` (EM). Componentes cujo CASE não encaixe em nenhuma categoria retornam `modalidade = NULL` e são filtrados pela própria query antes de chegar ao ETL.

---

### Tabela 7 — `agrupamento_atribuicao_territorio_saber`

**Endpoints:** 13, 14, 15  
**Pipeline fonte:** F (Query F1 — ApiEolConnection)

| Coluna | Tipo PostgreSQL | Nullable | Descrição | Origem no Model_IN |
|--------|----------------|----------|-----------|-------------------|
| `id` | `SERIAL` | NOT NULL | PK surrogate | — |
| `cod_agrupamento` | `INTEGER` | NOT NULL | PK de negócio do agrupamento | F1: `codagrupamento` |
| `cod_territorio_saber` | `INTEGER` | NOT NULL | Código do território saber | F1: `codterritoriosaber` |
| `cod_experiencia_pedagogica` | `INTEGER` | NULL | Código da experiência pedagógica | F1: `codexperienciapedagogica` |
| `dt_inicio_atribuicao` | `TIMESTAMP` | NOT NULL | Data de início | F1: `dtinicioatribuicao` |
| `ano_atribuicao` | `INTEGER` | NOT NULL | Ano da atribuição | F1: `anoatribuicao` |
| `dt_fim_atribuicao` | `TIMESTAMP` | NULL | Data de fim | F1: `dtfimatribuicao` |
| `dt_fim_turma` | `TIMESTAMP` | NULL | Data de fim da turma | F1: `dtfimturma` |
| `rf_professor` | `VARCHAR(20)` | NULL | RF do professor | F1: `rfprofessor` |
| `cod_turma` | `VARCHAR(20)` | NULL | Código da turma | F1: `codturma` |
| `cod_componentes_curriculares` | `VARCHAR(500)` | NULL | CSV dos componentes ("512,513") — valor original mantido | F1: `codcomponentescurriculares` |
| `ano_letivo` | `INTEGER` | NOT NULL | Ano letivo | F1: `anoletivo` |
| `cod_motivo_disponibilizacao` | `INTEGER` | NULL | Código do motivo | F1: `codmotivodisponibilizacao` |
| `desc_territorio_saber` | `VARCHAR(200)` | NULL | Descrição inline do território | F1: `descterritoriosaber` |
| `desc_experiencia_pedagogica` | `VARCHAR(200)` | NULL | Descrição inline da experiência | F1: `descexperienciapedagogica` |
| `encerramento_atribuicao_agrupamento_atualizado` | `BOOLEAN` | NULL | Flag de encerramento | F1: campo homônimo |
| `criado_em` | `TIMESTAMP` | NULL | Timestamp de criação — **vem da fonte** (ApiEolConnection) | F1: `criado_em` |
| `alterado_em` | `TIMESTAMP` | NULL | Timestamp de atualização — **vem da fonte** e serve como **watermark** | F1: `alterado_em` |
| `transferido_em` | `TIMESTAMP` | NOT NULL | Timestamp ETL-controlado — atualizado em toda execução (não vem da fonte) | — |

**Constraints:**
```sql
PRIMARY KEY (id)
UNIQUE (cod_agrupamento)
INDEX ON (cod_turma)
INDEX ON (rf_professor)
INDEX ON (alterado_em)   -- índice para watermark
INDEX ON (ano_letivo)
```

**Chave de Upsert:**
```sql
ON CONFLICT (cod_agrupamento)
DO UPDATE SET
  cod_territorio_saber                             = EXCLUDED.cod_territorio_saber,
  cod_experiencia_pedagogica                       = EXCLUDED.cod_experiencia_pedagogica,
  dt_inicio_atribuicao                             = EXCLUDED.dt_inicio_atribuicao,
  dt_fim_atribuicao                                = EXCLUDED.dt_fim_atribuicao,
  dt_fim_turma                                     = EXCLUDED.dt_fim_turma,
  rf_professor                                     = EXCLUDED.rf_professor,
  cod_turma                                        = EXCLUDED.cod_turma,
  cod_componentes_curriculares                     = EXCLUDED.cod_componentes_curriculares,
  cod_motivo_disponibilizacao                      = EXCLUDED.cod_motivo_disponibilizacao,
  desc_territorio_saber                            = EXCLUDED.desc_territorio_saber,
  desc_experiencia_pedagogica                      = EXCLUDED.desc_experiencia_pedagogica,
  encerramento_atribuicao_agrupamento_atualizado   = EXCLUDED.encerramento_atribuicao_agrupamento_atualizado,
  alterado_em                                      = EXCLUDED.alterado_em,
  transferido_em                                   = NOW()
```

> **Obs:** `desc_territorio_saber` e `desc_experiencia_pedagogica` são desnormalizados (inline) — não há tabela de catálogo separada para território e experiência. Esta é a modelagem correta segundo Risso.

---

## SEÇÃO 5 — Mapeamento Rápido: Endpoint → Tabela → Chave de Query

| # | Endpoint (resumido) | Tabela | WHERE Principal |
|---|---------------------|--------|-----------------|
| 1 | turmas/{codigoTurma}/funcionarios/{login}/perfis/{idPerfil}/agrupaComponente | `componente_curricular_por_turma` | `turma_codigo = ? AND professor = ?` |
| 2 | funcionarios/{login}/perfis/{idPerfil} | `componente_curricular_por_turma` | `professor = ?` |
| 3 | turmas/{codigoTurma}/funcionarios/{login}/perfis/{idPerfil}/planejamento | `componente_curricular_por_turma` | `turma_codigo = ? AND professor = ?` |
| 4 | anos/{anoTurma}/regencia | `componente_curricular_regencia` | `ano_turma = ? AND ano_letivo = ?` |
| 5 | turmas/{codigoTurma}/funcionarios/{login}/validar/pap | `componente_curricular_por_turma` | `turma_codigo = ? AND exibir_componente_eol = false` |
| 6 | ues/{ueId}/modalidades/{modalidade}/anos/{anoLetivo}/anos-escolares | `componente_curricular_por_ano_letivo` | `ano_letivo = ? AND modalidade = ?` |
| 7 | ues/{ueId}/modalidades/{modalidade}/anos/{anoLetivo} | `componente_curricular_por_ano_letivo` | `ano_letivo = ? AND modalidade = ?` |
| 8 | ues/{ueId}/turmas | `componente_curricular_por_turma` | `turma_codigo IN (?)` |
| 9 | turmas (codigoTurmas[]) | `componente_curricular_por_turma` | `turma_codigo = ANY(?)` |
| 10 | turmas/regulares | `componente_curricular_por_turma` | `turma_codigo = ANY(?) AND territorio_saber = false` |
| 11 | (todos) | `componente_curricular` | — (lista completa) |
| 12 | dados-aula-turma | `dados_aula_turma` | `ue_codigo = ? AND ano_letivo = ? AND componente_codigo = ANY(?)` |
| 13 | territorio-saber/agrupamentos-correlacionados (GET) | `agrupamento_atribuicao_territorio_saber` | `cod_agrupamento = ?` |
| 14 | territorio-saber/agrupamentos-correlacionados (POST) | `agrupamento_atribuicao_territorio_saber` | `cod_agrupamento = ANY(?)` |
| 15 | territorio-saber/agrupamentos (POST) | `agrupamento_atribuicao_territorio_saber` | `cod_agrupamento = ANY(?)` |
| 16 | ano-turma/ano-letivo/{anoLetivo} | `componente_curricular_por_ano_letivo` | `ano_letivo = ?` |
| 17 | turmas/{codigoTurma}/sem-atribuicao/{dataBaseTick} | `componente_curricular_por_turma` | `turma_codigo = ? AND professor IS NULL` |

---

## SEÇÃO 6 — Regras de Transformação (Model_IN → Model_OUT)

| Campo Model_OUT | Lógica de Derivação |
|----------------|---------------------|
| `regencia` | `A2.EhRegencia` (booleano direto) |
| `territorio_saber` | `A2.EhTerritorio` (booleano direto) |
| `exibir_componente_eol` | `A1.Codigo NOT IN [lista ids de A4.BuscarComponentesCurricularesPAP]` |
| `planejamento_regencia` | `A1.Codigo IN A3.IdComponenteCurricular AND (A3.Turno matches TurnoTurma OR sem filtro de turno)` |
| `codigo_componente_curricular_pai` | `A2.CodigoPai` (nullable — LEFT JOIN) |
| `codigo_componente_territorio_saber` | A confirmar — provavelmente vem do agrupamento ou de flag em ApiEolConnection |
| `professor` (normalização) | SE `AtribuicaoExterna = 0`: usar `cd_registro_funcional` (RF) — SE `AtribuicaoExterna = 1`: usar `cd_cpf_pessoa` (CPF) |
| `componente_planejamento_regencia` | Mesmo que `planejamento_regencia` acima, contexto da tabela 4 |
| `territorio_saber` (tabela 4) | `B1.CodigoTerritorioSaber IS NOT NULL` |
| CSV split (agrupamento) | `F1.codcomponentescurriculares.split(',')` → lista de integers |

---

## SEÇÃO 7 — Estratégia de Watermark por Pipeline

> **Observação Risso:** O watermark não pode ser baseado apenas no `ano_letivo`. Precisa ser **composto** por três dimensões para garantir rastreabilidade fina no SINC_REC_DB.

### 7.1 Estrutura do Watermark Composto

```
watermark = (pipeline_id, ano_letivo, data_corte)
```

| Dimensão | Descrição |
|----------|-----------|
| `pipeline_id` | Identificador do pipeline/entidade (ex: `"componente_por_turma"`, `"regencia"`) — o **índice do que está mudando** |
| `ano_letivo` | Ano letivo em processamento (ex: `2026`) — delimita o escopo da carga |
| `data_corte` | Data/hora específica até onde os dados foram buscados (ex: `2026-04-07 23:59:59`) — o **"peguei dados até aqui"** |

O SINC_REC_DB armazena uma entrada por `(pipeline_id, ano_letivo)` com o campo `data_corte` atualizado após cada execução bem-sucedida. Na próxima rodada, o ETL sabe: "para este pipeline, neste ano, já processei até esta data."

### 7.2 Watermark por Pipeline

| Pipeline | `pipeline_id` | `ano_letivo` | `data_corte` | Banco Fonte |
|----------|---------------|--------------|--------------|-------------|
| A (por turma) | `componente_por_turma` | ano corrente | data D-1 | EolConnection |
| B (regência) | `componente_regencia` | ano corrente | data D-1 | EolConnection |
| C (lista simples) | `componente_lista` | — | data D-1 | EolConnection |
| D (dados aula) | `dados_aula_turma` | ano corrente | data D-1 | EolConnection |
| E (por ano letivo) | `componente_por_ano_letivo` | ano corrente | data D-1 | EolConnection |
| F (agrupamento) | `agrupamento_territorio` | — | `alterado_em` da fonte | ApiEolConnection |

> **Obs Pipeline F:** Único com watermark por **timestamp real** (`alterado_em` da tabela `agrupamentoatribuicaoterritoriosaber`). Os demais usam `data_corte` = início do dia D-1 como referência de corte.

---

## SEÇÃO 8 — Deduplicação e Idempotência

> **Observação Risso:** São dois filtros distintos e sequenciais. Não confundir.

### 8.1 Primeiro Filtro — Deduplicação

Aplicado **antes** do processamento, na entrada do worker Celery.

**Objetivo:** Detectar se o batch/registro já foi processado nesta execução (mesmo `execution_id`). Se for duplicata, **descartar** — não entrar no pipeline de transformação.

**Como detectar:**
- Cada registro carrega o `execution_id` da rodada ETL
- O worker verifica em cache (KeyDB) ou SINC_REC_DB se aquele `(execution_id, chave_negocio)` já foi processado
- Se sim → skip. Não trabalha, não grava, não incrementa contador.

**Quando ocorre:** Retries automáticos do Celery, reenvio de mensagem por falha de ACK, publicação dupla acidental.

### 8.2 Segundo Filtro — Idempotência

Aplicado **durante** a persistência, via `ON CONFLICT DO UPDATE`.

**Objetivo:** Garantir que, mesmo que uma duplicata passe do primeiro filtro, o resultado final no banco seja **idêntico** à primeira execução — sem registros duplicados, sem estado inconsistente.

**Como funciona:**
- O ETL reprocessa o ano letivo inteiro (ou o escopo do batch)
- Compara com o que já existe no PEDAGOGICO_DB linha a linha
- O `ON CONFLICT DO UPDATE` atualiza com os mesmos valores — o dado final é o mesmo
- `transferido_em = NOW()` é atualizado (esperado — auditoria de execução)
- `criado_em` permanece intacto

```
[Dados chegando ao Worker]
          |
    [DEDUP CHECK] ←─── Primeiro filtro
    ┌─────┴─────┐
  SIM          NÃO
(duplicata)  (novo)
    │            │
  SKIP        TRANSFORMA
              (Model_IN → Model_OUT)
                  │
          [ON CONFLICT DO UPDATE] ←─── Segundo filtro
          ┌────────┴────────┐
       EXISTE           NÃO EXISTE
    (atualiza com      (insere novo
     mesmos valores)    registro)
```

> **Regra:** A deduplicação protege **performance** (evita retrabalho). A idempotência protege **corretude** (garante que retrabalho acidental não quebra o estado). Os dois filtros devem coexistir — nunca substituir um pelo outro.

---

## SEÇÃO 9 — Pendências para Confirmação

| # | Pendência | 
|---|-----------|
| 1 | Derivação de `codigo_componente_territorio_saber` no Shape A |
| 2 | Confirmação de que o ETL terá acesso à tabela `agrupamentoatribuicaoterritoriosaber` no ApiEolConnection (CONFIRMAR COM O MARIO)|



