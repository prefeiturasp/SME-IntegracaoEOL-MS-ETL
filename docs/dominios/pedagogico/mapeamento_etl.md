# Mapeamento do ETL Pedagógico

Resumo de origem e destino por fase. Para o mapeamento campo a campo e decisões de migração do banco legado (ApiEolConnection), ver [remocao_dependencia_apieolconnection(postgres).md](remocao_dependencia_apieolconnection(postgres).md).

---

## Fase 1 — ComponenteCurricular

**Query:** `SQL_COMPONENTES_NAO_CANCELADOS` (sem parâmetro de ano)

| Campo EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `cd_componente_curricular` | `codigo` | `int()` |
| `dc_componente_curricular` | `descricao` | `strip_str()` |
| — | `transferido_em` | `timezone.now()` |

---

## Fase 2 — ComponenteCurricularPorTurma

**Query:** `SQL_COMPONENTES_POR_TURMA` (parâmetro `?` por ano letivo)

`regencia` e `territorio_saber` são calculados via `CASE` inline na query (`EhRegencia`, `EhTerritorio`) — não há lookup A2 separado.

| Campo Origem | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `Codigo` (EOL) | `codigo` | `int()` |
| `Descricao` (EOL) | `descricao` | `strip_str()` |
| `EhRegencia` (CASE inline) | `regencia` | `bool()` |
| `EhTerritorio` (CASE inline) | `territorio_saber` | `bool()` |
| lookup A3 (`SQL_LOOKUP_PLANEJAMENTO_REGENCIA`) | `planejamento_regencia` | exact → fallback |
| `codigo` se `territorio_saber` | `codigo_componente_territorio_saber` | `codigo` ou `None` |
| `MAPA_COMPONENTE_PAI` | `codigo_componente_curricular_pai` | `.get(codigo)` |
| `cd_turma_escola` | `turma_codigo` | `str()` ou `None` |
| RF ou CPF (por `AtribuicaoExterna`) | `professor` | `str()` ou `None` |
| `anoletivo` | `ano_letivo` | `int()` |
| `MAPA_COMPONENTE_PAI` + `ano_letivo` | `exibir_componente_eol` | `not (ano <= 2021 and cod in mapa)` |
| — | `transferido_em` | `timezone.now()` |

---

## Fase 3 — AgrupamentoAtribuicaoTerritorioSaber + ComponenteCurricularAgrupamento

**Query:** `SQL_ATRIBUICOES_TERRITORIO_SABER` (UNION ALL SME RF + Externo CPF, todos os anos)

O agrupamento ocorre em Python via `_agrupar()`. Somente grupos com 2+ componentes geram registros.

| Campo Origem | Campo Destino (`AgrupamentoAtribuicaoTerritorioSaber`) | Transformação |
| :--- | :--- | :--- |
| chave natural do grupo | `cod_agrupamento` | MD5 `[:15]` → `int` (BigInteger) |
| `codigo_territorio_saber` | `cod_territorio_saber` | direto |
| `codigo_experiencia_pedagogica` | `cod_experiencia_pedagogica` | nullable |
| `data_atribuicao` | `dt_inicio_atribuicao` | `make_aware()` |
| `data_disponibilizacao` | `dt_fim_atribuicao` | `make_aware()` |
| `data_fim_turma` | `dt_fim_turma` | `make_aware()` |
| `rf_professor` | `rf_professor` | direto |
| `codigo_turma` | `cod_turma` | `str()` |
| componentes ordenados | `cod_componentes_curriculares` | `",".join(...)` |
| `ano_letivo` | `ano_letivo` | direto |

| Campo Origem | Campo Destino (`ComponenteCurricularAgrupamento`) | Transformação |
| :--- | :--- | :--- |
| componente do grupo | `componente_codigo` | `int()` |
| `codigo_turma` | `turma_codigo` | `str()` |
| hash do grupo | `codigo_agrupamento` | mesmo `cod_agrupamento` |
| `rf_professor` | `rf_professor` | direto |
| `ano_letivo` | `ano_letivo` | direto |

---

## Fase 4 — ComponenteInicioTurma

**Query:** `SQL_COMPONENTE_INICIO_TURMA` (parâmetro `?` por ano letivo)

| Campo EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `ComponenteCurricularCodigo` | `componente_codigo` | `str()` |
| `ComponenteCurricularDescricao` | `componente_descricao` | `strip_str()` |
| `TurmaCodigo` | `turma_codigo` | `str()` |
| `DataInicioTurma` | `data_inicio_turma` | `make_aware()` |
| `UeCodigo` | `ue_codigo` | `str()` ou `None` |
| `AnoLetivo` | `ano_letivo` | `int()` ou `None` |
| `TipoPeriodicidade` | `tipo_periodicidade` | `int()` ou `None` |
| — | `transferido_em` | `timezone.now()` |

---

## Fase 5 — GradeCurricularSerie

**Query:** `SQL_GRADE_CURRICULAR_SERIE` (parâmetro `?` por ano letivo)

| Campo EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `CodigoComponenteCurricular` | `codigo_componente_curricular` | `int()` |
| `DescricaoComponenteCurricular` | `descricao_componente_curricular` | `strip_str()` |
| `CodigoAnoTurma` | `codigo_ano_turma` | `str()` ou `None` |
| `DescricaoSerieEnsino` | `descricao_serie_ensino` | `strip_str()` ou `None` |
| `CodigoSerieEnsino` | `codigo_serie_ensino` | `int()` ou `None` |
| CASE na query EOL | `modalidade` | `int()` ou `None` |
| `AnoLetivo` | `ano_letivo` | `int()` |
| — | `transferido_em` | `timezone.now()` |

---

## Fase 6 — Turma

**Query:** `SQL_TURMAS` (parâmetro `?` por ano letivo)

Origem: `turma_escola` (NOLOCK) com joins em `escola`, `serie_turma_escola`, `serie_ensino` e `etapa_ensino`. Filtra `cd_tipo_turma <> 4` e `st_turma_escola IN ('O', 'A', 'E', 'C')`.

| Campo EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `cd_turma_escola` | `codigo` | `int()` |
| `an_letivo` | `ano_letivo` | `int()` |
| CASE sobre `dc_turma_escola` (1º char numérico) | `ano` | `str()` ou `None` |
| `cd_tipo_turma` | `tipo_turma` | `int()` |
| `dc_turma_escola` | `nome_turma` | `strip_str()` |
| `cd_duracao` | `duracao_turno` | `int()` ou `None` |
| `cd_tipo_turno` | `tipo_turno` | `int()` ou `None` |
| `dt_inicio_turma` | `data_inicio_turma` | `make_aware()` ou `None` |
| `dt_fim` | `data_fim` | `make_aware()` ou `None` |
| CASE `st_turma_escola = 'E'` | `extinta` | `bool()` |
| `st_turma_escola` | `situacao` | `str()` ou `None` |
| `cd_escola` | `ue_codigo` | `str()` ou `None` |
| `dt_atualizacao_tabela` | `data_atualizacao` | `make_aware()` ou `None` |
| `dt_status_turma_escola` | `data_status_turma_escola` | `make_aware()` ou `None` |
| `dc_serie_ensino` | `serie_ensino` | `strip_str()` ou `None` |
| CASE sobre `cd_etapa_ensino` | `modalidade` | `str()` (`'EJA'`, `'Fundamental'`, `'Médio'`, `'Infantil'`) ou `None` |
| CASE sobre `cd_etapa_ensino` + `tp_escola` | `codigo_modalidade` | `int()` (1=EI, 3=EJA, 4=CIEJA, 5=EF, 6=EM) |
| `cd_tipo_programa` | `codigo_tipo_programa` | `int()` ou `None` |
| CASE EJA pelo mês de `dt_inicio_turma` | `semestre` | `int()` (1 ou 2 para EJA; 0 demais) |
| `cd_etapa_ensino = 13` e `cd_modalidade_ensino = 2` | `ensino_especial` | `bool()` |
| — | `transferido_em` | `timezone.now()` |
