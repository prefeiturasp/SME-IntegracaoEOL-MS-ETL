# ETL Pedagógico — Remoção da dependência ApiEolConnection

---

### O que era ApiEolConnection

`ApiEolConnection` era uma segunda fonte de dados (PostgreSQL legado) utilizada pelo .NET para enriquecer os dados do EOL. Quatro grupos de dados dependiam dela:

| Dado                                               | Tabela ApiEol (Postgres)                      | Motivo original                                              |
| -------------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------ |
| Flags de componente (`EhRegencia`, `EhTerritorio`) | `ComponenteCurricular`                        | Atributos não disponíveis diretamente no EOL                 |
| Lookup de `planejamento_regencia`                  | `regencia_componente_curricular`              | Relacionamento regência → componente por turno/ano           |
| Pai do componente e IDs PAP                        | `componentecurricularpai` + `componentes_pap` | `codigo_componente_curricular_pai` e `exibir_componente_eol` |
| Agrupamentos território do saber                   | `agrupamento_atribuicao_territorio_saber`     | Agrupamentos pré-calculados com sequence Postgres            |

### Como cada dependência foi resolvida

#### Flags de componente — `SQL_DISCIPLINAS_EOL` + `DisciplinaEolIn`

**Antes:** o .NET consultava o Postgres legado (`DisciplinasEolRepository.ObterDisciplinasAsync`) que lia a tabela `ComponenteCurricular` com os campos `EhRegencia` e `EhTerritorio`.

**Depois:** query direta ao SQL Server (EolConnection) via `SQL_DISCIPLINAS_EOL`:

- **`EhRegencia`:** derivado via `CASE WHEN cd_componente_curricular IN (...)` com a constante `_IDS_REGENCIA`.

  Essa lista **não é uma invenção do ETL** — o próprio .NET já a tinha hardcoded em `QueriesComponenteCurricular.cs` (método `ObterTodas`, linha 171):

  ```sql
  WHEN cd_componente_curricular IN (508, 511, 1064, 1065, 1104, 1105, 1112, 1113,
      1114, 1115, 1117, 1121, 1124, 1125, 1211, 1212, 1213, 1290, 1301) THEN 1
  ```

  O Postgres era um espelho dessa lista. O ETL elimina o intermediário sem introduzir divergência.

  **Risco residual:** se um novo componente de regência for criado no EOL, `_IDS_REGENCIA` precisa de atualização manual — mas esse risco já existia no .NET.

- **`EhTerritorio`:** derivado via `EXISTS (SELECT 1 FROM turma_grade_territorio_experiencia WHERE ...)`. A informação de território já existia no EOL; o Postgres apenas a espelhava.

- **`CodigoPai`:** **removido da query** — substituído por `MAPA_COMPONENTE_PAI` (ver seção abaixo).

**DTO:** `DisciplinaApiEolIn` renomeado para `DisciplinaEolIn`; campo `codigo_pai` removido.

---

#### Lookup de `planejamento_regencia` — `SQL_REGENCIA_COMPONENTE_CURRICULAR`

**Antes:** o .NET consultava o Postgres (`BuscarDisciplinasRegenciaAsync`) e depois, em `ComponenteCurricularService.AdicionarComponentesPlanejamentoAsync`, fazia o matching:

```csharp
// ComponenteCurricularService.cs:234-238
var componentesPlanejamento = componentesRegenciaApiEol
    .Where(r => r.Ano.HasValue
             && r.Ano.Value.ToString() == componenteRegencia.AnoTurma
             && r.Turno == componenteRegencia.TurnoTurma);

if (componentesPlanejamento == null || !componentesPlanejamento.Any())
    componentesPlanejamento = componentesRegenciaApiEol
        .Where(r => !r.Ano.HasValue && !r.Turno.HasValue);
```

Ou seja: busca exata por `(codigo, turno, ano)` com fallback para entradas sem turno/ano.

**Depois:** `SQL_REGENCIA_COMPONENTE_CURRICULAR` — query ao SQL Server que une `gcc`, `grade`, `serie_ensino`, `turma_escola` e `duracao_tipo_turno`, filtrando pelos mesmos IDs de `_IDS_REGENCIA`. Retorna `(id_componente_curricular, turno, ano)`.

O matching em Python espelha diretamente a lógica C# acima:

1. `(codigo, turno_turma, ano_turma) in exact` → `True`
2. `codigo in fallback` (turno `IS NULL` e ano `IS NULL`) → `True`
3. Caso contrário → `False`

**DTO:** inalterado (`id_componente_curricular`, `turno`, `ano`).

**Constantes compartilhadas:** `_IDS_REGENCIA` e `_PLACEHOLDERS_REGENCIA` são definidas uma vez e usadas tanto em `SQL_DISCIPLINAS_EOL` quanto em `SQL_REGENCIA_COMPONENTE_CURRICULAR`.

---

#### `codigo_componente_curricular_pai` — `MAPA_COMPONENTE_PAI`

**Antes:** o .NET lia a tabela `componentecurricularpai` do Postgres e aplicava lógica de vigência (`TemComponenteCurricularVigente`) para resolver o pai ativo de cada componente.

**Depois:** `MAPA_COMPONENTE_PAI: dict[int, int]` — constante hardcoded com 7 entradas.

**Por que hardcodar é correto:** toda a lógica de vigência do .NET (`ComponenteCurricular.cs:67–83`) avalia `dataReferencia <= Vigencia`. As 7 entradas da tabela Postgres tinham todas `vigencia = 2021-12-31`. Para qualquer `ano_letivo >= 2022`, `TemComponenteCurricularVigente` retorna `false` para todas elas — o que significa que o mapa estático produz exatamente o mesmo resultado que a consulta dinâmica produziria nos dados reais. Os dados eram estáticos; o mapa hardcoded apenas explicita isso.

**Uso:** `codigo_componente_curricular_pai = MAPA_COMPONENTE_PAI.get(codigo)`.

**Risco residual:** se novas relações pai/filho forem criadas no futuro, o mapa precisará de atualização manual.

---

#### `exibir_componente_eol` — `MAPA_COMPONENTE_PAI` + `ano_letivo`

**Antes:** o .NET calculava em runtime (`ComponenteCurricularService.MapearParaDto`, linha 293):

```csharp
ExibirComponenteEOL = !agrupaComponenteCurricular
                      && !componenteCurricular.TemComponenteVigente(componentesApiEol)
```

`TemComponenteVigente` verificava a tabela `componentecurricularpai` (relação pai/filho de componentes com vigência). A `dataReferencia` usada na comparação era derivada do `AnoLetivo`:

```csharp
// AnoLetivo corrente → DateTime.Now.Date
// AnoLetivo histórico → new DateTime(AnoLetivo, 12, 31)
```

**O estado real de `componentecurricularpai`** — confirmado pela migration `V124__TABELA_COMPONENTE_CURRICULAR_PAI.sql`, o único INSERT que existiu na tabela:

```sql
insert into componentecurricularpai (idcomponentecurricularpai, idcomponentecurricular, vigencia)
select idcomponentecurricularpai, idcomponentecurricular, '2021-12-31'
from componentecurricular c where idcomponentecurricularpai = 512;
```

Todas as entradas tinham `vigencia = '2021-12-31'`. Nenhuma migration posterior inseriu mais registros. Os 7 componentes afetados são exatamente as chaves de `MAPA_COMPONENTE_PAI`.

**Comportamento resultante por ano:**

| `ano_letivo` | `dataReferencia` | `TemComponenteVigente` (7 com pai) | `ExibirComponenteEOL` (7 com pai) | Demais componentes |
|---|---|---|---|---|
| <= 2021 | `31/12/ano` ≤ `2021-12-31` | `True` — vigência ainda ativa | `False` | `True` |
| >= 2022 | `31/12/ano` > `2021-12-31` | `False` — vigência expirada | `True` | `True` |

**Depois:** expressão derivada das migrations, sem dependência do Postgres:

```python
# Chaves de MAPA_COMPONENTE_PAI = os 7 componentes que tinham pai com vigência 2021-12-31
_COMPONENTES_COM_PAI_VIGENTE_ATE_2021 = frozenset(MAPA_COMPONENTE_PAI.keys())

exibir_componente_eol = not (
    ano_letivo <= 2021 and codigo in _COMPONENTES_COM_PAI_VIGENTE_ATE_2021
)
```

**Nota:** `componentecurricularpap` (tabela PAP — Programa de Acompanhamento Pedagógico) é uma tabela completamente distinta de `componentecurricularpai`. No .NET, a tabela PAP era usada exclusivamente por `TurmaPossuiComponenteCurricularPAPAsync` — sem relação com `ExibirComponenteEOL`. `IDS_COMPONENTES_PAP` e `ComponentePapIn` **removidos** do ETL.

---

#### Agrupamentos território do saber — agrupamento em Python

**Antes:** o .NET lia a tabela `agrupamento_atribuicao_territorio_saber` pré-calculada no Postgres, cujo `cod_agrupamento` era gerado por sequence Postgres (não determinístico entre instâncias).

**Depois:** query `SQL_ATRIBUICOES_TERRITORIO_SABER` ao SQL Server (UNION ALL SME RF + Externo CPF, todos os anos letivos), com **agrupamento em Python** via `_agrupar()`.

**`cod_agrupamento` determinístico:** derivado por hash MD5 dos primeiros 15 hex-dígitos da chave natural (turma + território + experiência + professor + datas) + componentes ordenados → `int` que cabe em `bigint` PostgreSQL (`int8`). Garante idempotência entre runs; `ON CONFLICT (cod_agrupamento) DO UPDATE` funciona sem surpresas.

> `BigIntegerField` foi necessário — `IntegerField` transbordava com 15 hex-chars.

**`AgrupamentoTerritorioSaberIn`** renomeado para `AtribuicaoTerritorioSaberIn` com campos atualizados.

**Normalização de tipos na chave** (problema real encontrado em produção — o UNION ALL SME/Externo retornava `codigo_turma` como `int` na parte SME e `str` na parte Externo, gerando dois grupos distintos para a mesma turma):

| Campo da chave                             | Normalização              |
| ------------------------------------------ | ------------------------- |
| `codigo_turma`                             | `str()`                   |
| `codigo_territorio_saber`                  | `int()`                   |
| `codigo_experiencia_pedagogica`            | `int()` ou `-1` se `None` |
| `rf_professor`                             | `str()` ou `""` se `None` |
| `data_atribuicao`, `data_disponibilizacao` | `datetime.min` se `None`  |

Normalizando tipos → mesmo grupo → mesmo hash → sem `ON CONFLICT` duplicado.

**Safety net:** dedup por `cod_agrupamento` e por `(componente_codigo, turma_codigo, codigo_agrupamento)` antes do `bulk_create`.

**Datetimes naive:** SQL Server retorna datetimes sem timezone. Django com `USE_TZ=True` rejeita naive em `DateTimeField`. Fix: `timezone.make_aware(dt)` aplicado em `dt_inicio_atribuicao`, `dt_fim_atribuicao`, `dt_fim_turma`.

---

## Mapeamento por tabela de destino

### `ComponenteCurricular` — `popular_componentes_curriculares`

| Campo origem (EOL)         | Campo destino (Django) | Transformação                      |
| -------------------------- | ---------------------- | ---------------------------------- |
| `cd_componente_curricular` | `codigo`               | `int()`                            |
| `dc_componente_curricular` | `descricao`            | `_strip()` (LTRIM/RTRIM)           |
| —                          | `transferido_em`       | `timezone.now()` injetado pelo ETL |

- **Query:** `SQL_COMPONENTES_NAO_CANCELADOS` — sem parâmetros, filtra `dt_cancelamento IS NULL`.
- **Estratégia:** upsert por `codigo` (`unique=True`); `update_fields = ["descricao", "transferido_em"]`.
- **Deduplicação:** `vistos: set[int]` por `codigo` dentro do run.
- **DTO in:** `ComponenteCurricularSimplesIn`.
- **Proxy out:** `ComponenteCurricularOut`.

---

### `AgrupamentoAtribuicaoTerritorioSaber` + `ComponenteCurricularAgrupamento` — `popular_agrupamentos_territorio_saber`

**Fonte:** `SQL_ATRIBUICOES_TERRITORIO_SABER` — UNION ALL (SME RF + Externo CPF), todos os anos letivos, sem filtro dinâmico.

**Chave de agrupamento (Python):**

```
(codigo_turma, codigo_territorio_saber, codigo_experiencia_pedagogica,
 rf_professor, data_atribuicao, data_disponibilizacao)
```

| Campo origem                    | Campo destino (`AgrupamentoAtribuicaoTerritorioSaber`) | Transformação                           |
| ------------------------------- | ------------------------------------------------------ | --------------------------------------- |
| chave grupo                     | `cod_agrupamento`                                      | MD5 hash `[:15]` → `int`                |
| `codigo_territorio_saber`       | `cod_territorio_saber`                                 | direto                                  |
| `codigo_experiencia_pedagogica` | `cod_experiencia_pedagogica`                           | direto (nullable)                       |
| `data_atribuicao`               | `dt_inicio_atribuicao`                                 | `make_aware` se naive                   |
| `data_disponibilizacao`         | `dt_fim_atribuicao`                                    | `make_aware` se naive                   |
| `data_fim_turma`                | `dt_fim_turma`                                         | `make_aware` se naive                   |
| componentes ordenados           | `cod_componentes_curriculares`                         | `",".join(str(c) for c in componentes)` |
| `ano_letivo`                    | `ano_letivo`                                           | direto                                  |
| `rf_professor`                  | `rf_professor`                                         | direto                                  |
| `codigo_turma`                  | `cod_turma`                                            | `str()`                                 |
| —                               | `transferido_em`                                       | `timezone.now()`                        |

- **Estratégia `AgrupamentoAtribuicaoTerritorioSaber`:** upsert por `cod_agrupamento`; `update_fields = ["dt_fim_atribuicao", "cod_motivo_disponibilizacao", "cod_componentes_curriculares", "transferido_em"]`.
- **Estratégia `ComponenteCurricularAgrupamento`:** upsert por `(componente_codigo, turma_codigo, codigo_agrupamento)`; `update_fields = ["rf_professor", "transferido_em"]`.
- **DTO in:** `AtribuicaoTerritorioSaberIn`.

---

### `ComponenteCurricularPorTurma` — `popular_componentes_por_turma`

**Lookups carregados antes de iterar:**

- `SQL_DISCIPLINAS_EOL` → `dict[int, DisciplinaEolIn]` indexado por `id_componente_curricular` — fonte de `regencia` e `territorio_saber`.
- `SQL_REGENCIA_COMPONENTE_CURRICULAR` → dois sets: `exact: set[(codigo, turno, ano)]` e `fallback: set[int]` — fonte de `planejamento_regencia`.

**Iteração por ano letivo:** `SQL_COMPONENTES_POR_TURMA` sem filtro de ano causava timeout no SQL Server (6 branches de UNION ALL, múltiplos JOINs). Solução: `SQL_ANOS_LETIVOS` retorna anos distintos; `SQL_COMPONENTES_POR_TURMA` é executada uma vez por ano via `SQL_COMPONENTES_POR_TURMA.replace("?", str(ano))`.

| Campo origem                                                     | Campo destino (Django)               | Transformação                       |
| ---------------------------------------------------------------- | ------------------------------------ | ----------------------------------- |
| `Codigo`                                                         | `codigo`                             | `int()`                             |
| `Descricao`                                                      | `descricao`                          | `_strip()`                          |
| `TipoEscola`                                                     | _(ignorado)_                         | presente no DTO, não persistido     |
| — (`SQL_DISCIPLINAS_EOL`)                                        | `regencia`                           | `bool(disciplina.eh_regencia)`      |
| — (`SQL_DISCIPLINAS_EOL` + `SQL_REGENCIA_COMPONENTE_CURRICULAR`) | `planejamento_regencia`              | lookup exact → fallback             |
| — (`SQL_DISCIPLINAS_EOL`)                                        | `territorio_saber`                   | `bool(disciplina.eh_territorio)`    |
| `Codigo` (se territorio)                                         | `codigo_componente_territorio_saber` | `codigo if territorio else None`    |
| — (`MAPA_COMPONENTE_PAI`)                                        | `codigo_componente_curricular_pai`   | `MAPA_COMPONENTE_PAI.get(codigo)`   |
| `TurmaCodigo`                                                    | `turma_codigo`                       | `str()` ou `None`                   |
| — (`MAPA_COMPONENTE_PAI` + `ano_letivo`)                         | `exibir_componente_eol`              | `not (ano_letivo <= 2021 and codigo in _COMPONENTES_COM_PAI_VIGENTE_ATE_2021)` |
| `Professor`                                                      | `professor`                          | `str()` ou `None`                   |
| `anoletivo`                                                      | `ano_letivo`                         | `int()`                             |
| —                                                                | `transferido_em`                     | `timezone.now()`                    |

- **Estratégia:** full refresh (`delete all + bulk_create` em transação).
- **Deduplicação:** `dict` por `(codigo, turma_codigo, professor or "")`.
- **DTO in:** `ComponentePorTurmaIn`.
- **Proxy out:** `ComponenteCurricularPorTurmaOut`.

---

### `ComponenteCurricularRegencia` — `popular_componentes_regencia`

**Lookup carregado antes de iterar:** `SQL_REGENCIA_COMPONENTE_CURRICULAR` — mesmo índice (exact + fallback) usado em `popular_componentes_por_turma`.

**Iteração por ano letivo** (mesma razão de performance).

| Campo origem                             | Campo destino (Django)               | Transformação           |
| ---------------------------------------- | ------------------------------------ | ----------------------- |
| `CodigoComponenteCurricular`             | `codigo`                             | `int()`                 |
| `CodigoTerritorioSaber`                  | `codigo_componente_territorio_saber` | `int()` ou `None`       |
| `DescricaoComponenteCurricular`          | `descricao`                          | `_strip()`              |
| `CodigoTerritorioSaber IS NOT NULL`      | `territorio_saber`                   | `bool`                  |
| `TipoEscola`                             | `tipo_escola`                        | `str()` ou `None`       |
| `TurnoTurma`                             | `turno_turma`                        | `int()` ou `None`       |
| — (`SQL_REGENCIA_COMPONENTE_CURRICULAR`) | `componente_planejamento_regencia`   | lookup exact → fallback |
| `TurmaCodigo`                            | `turma_codigo`                       | `str()` ou `None`       |
| `rfProfessor`                            | `professor`                          | `str()` ou `None`       |
| `AnoTurma`                               | `ano_turma`                          | `str()`                 |
| `anoletivo`                              | `ano_letivo`                         | `int()`                 |
| `dataAtribuicao`                         | `inicio_atribuicao`                  | `make_aware` se naive   |
| `dataDisponibilizacao`                   | `fim_atribuicao`                     | `make_aware` se naive   |
| —                                        | `transferido_em`                     | `timezone.now()`        |

- **Estratégia:** full refresh.
- **Deduplicação:** `dict` por `(codigo, turma_codigo, professor or "", ano_letivo)`.
- **DTO in:** `ComponenteRegenciaIn`.
- **Proxy out:** `ComponenteCurricularRegenciaOut`.

---

### `DadosAulaTurma` — `popular_dados_aula_turma`

**Iteração por ano letivo** (consistência com demais tabelas).

| Campo origem                    | Campo destino (Django) | Transformação         |
| ------------------------------- | ---------------------- | --------------------- |
| `ComponenteCurricularCodigo`    | `componente_codigo`    | `str()`               |
| `ComponenteCurricularDescricao` | `componente_descricao` | `_strip()`            |
| `TurmaCodigo`                   | `turma_codigo`         | `str()`               |
| `DataInicioTurma`               | `data_inicio_turma`    | `make_aware` se naive |
| `UeCodigo`                      | `ue_codigo`            | `str()` ou `None`     |
| `AnoLetivo`                     | `ano_letivo`           | `int()`               |
| —                               | `transferido_em`       | `timezone.now()`      |

- **Estratégia:** full refresh.
- **Deduplicação:** `dict` por `(componente_codigo, turma_codigo)`.
- **DTO in:** `DadosAulaTurmaIn`.
- **Proxy out:** `DadosAulaTurmaOut`.

---

### `ComponenteCurricularPorAnoLetivo` — `popular_componentes_por_ano_letivo`

**Iteração por ano letivo**.

| Campo origem                    | Campo destino (Django)            | Transformação        |
| ------------------------------- | --------------------------------- | -------------------- |
| `CodigoComponenteCurricular`    | `codigo_componente_curricular`    | `int()`              |
| `DescricaoComponenteCurricular` | `descricao_componente_curricular` | `_strip()`           |
| `CodigoAnoTurma`                | `codigo_ano_turma`                | `str()` ou `None`    |
| `DescricaoSerieEnsino`          | `descricao_serie_ensino`          | `_strip()` ou `None` |
| `CodigoSerieEnsino`             | `codigo_serie_ensino`             | `int()` ou `None`    |
| `Modalidade`                    | `modalidade`                      | `int()` ou `None`    |
| `AnoLetivo`                     | `ano_letivo`                      | `int()`              |
| —                               | `transferido_em`                  | `timezone.now()`     |

- **Estratégia:** full refresh.
- **Deduplicação:** `dict` por `(codigo_componente_curricular, ano_letivo, modalidade)`.
- **DTO in:** `ComponentePorAnoLetivoIn`.
- **Proxy out:** `ComponenteCurricularPorAnoLetivoOut`.

---

## Iteração por ano letivo

**Problema:** `SQL_COMPONENTES_POR_TURMA` e a query de regência são pesadas (múltiplos UNION ALL, JOINs em tabelas grandes) — sem filtro de ano, o SQL Server não retornava resultados antes do timeout de conexão.

**Solução:**

```python
def _anos_letivos(self) -> list[int]:
    return [int(r[0]) for chunk in self.eol.iter_query(SQL_ANOS_LETIVOS) for r in chunk]

# No pipeline:
for ano in self._anos_letivos():
    sql = SQL_X.replace("?", str(ano))
    for chunk in self.eol.iter_query(sql):
        ...
```

**Por que `replace("?", str(ano))` e não `cursor.execute(sql, [ano])`:**
O backend Django `mssql` espera placeholders `%s` no SQL (converte para `?` internamente via `format_sql`). O pyodbc usa `?`. Passar `[ano]` via `iter_query` causava `TypeError: not all arguments converted during string formatting`. Pre-formatar inline com inteiro vindo do banco é seguro e evita alterar a infraestrutura compartilhada (`connection_readonly.py`).

---

## Fases de execução

| Fase | Método                                  | Tabela(s)                                                                  | Estratégia | Lookups carregados antes                                    |
| ---- | --------------------------------------- | -------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------- |
| 1    | `popular_componentes_curriculares`      | `ComponenteCurricular`                                                     | upsert     | —                                                           |
| 2    | `popular_agrupamentos_territorio_saber` | `AgrupamentoAtribuicaoTerritorioSaber` + `ComponenteCurricularAgrupamento` | upsert     | —                                                           |
| 3    | `popular_componentes_por_turma`         | `ComponenteCurricularPorTurma`                                             | upsert     | `SQL_DISCIPLINAS_EOL`, `SQL_REGENCIA_COMPONENTE_CURRICULAR` |
| 4    | `popular_componentes_regencia`          | `ComponenteCurricularRegencia`                                             | upsert     | `SQL_REGENCIA_COMPONENTE_CURRICULAR`                        |
| 5    | `popular_dados_aula_turma`              | `DadosAulaTurma`                                                           | upsert     | —                                                           |
| 6    | `popular_componentes_por_ano_letivo`    | `ComponenteCurricularPorAnoLetivo`                                         | upsert     | —                                                           |
