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

| Campo Origem | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `Codigo` (EOL) | `codigo` | `int()` |
| `Descricao` (EOL) | `descricao` | `strip_str()` |
| lookup A2 (`SQL_DISCIPLINAS_EOL`) | `regencia` | `bool(disciplina.eh_regencia)` |
| lookup A2 | `territorio_saber` | `bool(disciplina.eh_territorio)` |
| lookup A3 (`SQL_REGENCIA_COMPONENTE_CURRICULAR`) | `planejamento_regencia` | exact → fallback |
| `codigo` se `territorio_saber` | `codigo_componente_territorio_saber` | `codigo` ou `None` |
| `MAPA_COMPONENTE_PAI` | `codigo_componente_curricular_pai` | `.get(codigo)` |
| `cd_turma_escola` | `turma_codigo` | `str()` ou `None` |
| RF ou CPF (por `atribuicao_externa`) | `professor` | `str()` ou `None` |
| `an_letivo` | `ano_letivo` | `int()` |
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

## Fase 4 — ComponenteCurricularRegencia

**Query:** `SQL_COMPONENTES_TERRITORIO_ATRIBUIDOS` (parâmetro `?` por ano letivo)

| Campo EOL | Campo Destino | Transformação |
| :--- | :--- | :--- |
| `CodigoComponenteCurricular` | `codigo` | `int()` |
| `CodigoTerritorioSaber` | `codigo_componente_territorio_saber` | `int()` ou `None` |
| `DescricaoComponenteCurricular` | `descricao` | `strip_str()` |
| `CodigoTerritorioSaber IS NOT NULL` | `territorio_saber` | `bool` |
| `TipoEscola` | `tipo_escola` | `str()` ou `None` |
| `TurnoTurma` | `turno_turma` | `int()` ou `None` |
| lookup A3 | `componente_planejamento_regencia` | exact → fallback |
| `TurmaCodigo` | `turma_codigo` | `str()` ou `None` |
| `rfProfessor` | `professor` | `str()` ou `None` |
| `AnoTurma` | `ano_turma` | `str()` |
| `anoletivo` | `ano_letivo` | `int()` |
| `dataAtribuicao` | `inicio_atribuicao` | `make_aware()` |
| `dataDisponibilizacao` | `fim_atribuicao` | `make_aware()` |
| — | `transferido_em` | `timezone.now()` |

---

## Fase 5 — DadosAulaTurma

**Query:** `SQL_DADOS_AULA_TURMA` (parâmetro `?` por ano letivo)

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

## Fase 6 — ComponenteCurricularPorAnoLetivo

**Query:** `SQL_COMPONENTES_POR_ANO_LETIVO` (parâmetro `?` por ano letivo)

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
