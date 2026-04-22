# Visão Geral do Domínio Pedagógico

## Objetivo

Popular `pedagogico_db` com os dados de componentes curriculares do EOL — catálogo, atribuições por turma e professor, agrupamentos de território do saber, regência e oferta por ano letivo — servindo de base para os endpoints de planejamento pedagógico do SGP.

## Origem dos Dados

Todos os dados são extraídos exclusivamente do banco **EOL (SQL Server)** via `EOLService`.

Não há fonte secundária (o banco Postgres legado `ApiEolConnection` foi removido). Ver [remocao_dependencia_apieolconnection(postgres).md](remocao_dependencia_apieolconnection(postgres).md) para o histórico completo.

## Classe principal

`EtlPedagogicoService` em `apps/pedagogico/services.py`.

Herda de `BaseEtlService` (pipeline Producer-Consumer com ThreadPool, auditoria incremental via SHA-256 e retry em deadlock).

## Customizações em relação ao `BaseEtlService`

| Customização | Descrição |
| :--- | :--- |
| `_iter_chunks` | Quando o SQL contém `?`, itera para cada ano letivo substituindo o placeholder. |
| `_criar_transform` | Injeta `_agora` e lookups A2/A3 via closure por fase, sem overhead por linha. |
| `_executar_fase` | Fase 3 (agrupamentos) é tratada à parte: coleta tudo em memória, agrega em Python e escreve em duas tabelas. |
| `executar` | Pré-carrega lookups A2/A3 antes das fases 2 e 4 e registra resultado duplo da fase 3. |

## Lookups pré-carregados

Antes das fases que dependem de classificação de componentes, `_carregar_lookups` carrega:

- **A2** — `SQL_DISCIPLINAS_EOL` → `dict[int, DisciplinaEolIn]` indexado por `id_componente_curricular`. Fonte de `regencia` e `territorio_saber`.
- **A3** — `SQL_REGENCIA_COMPONENTE_CURRICULAR` → dois sets: `exact: set[(codigo, turno, ano)]` e `fallback: set[int]`. Fonte de `planejamento_regencia` / `componente_planejamento_regencia`.

## Total de modelos do app

O código define **7 modelos** em `apps/pedagogico/models.py`:

1. `ComponenteCurricular`
2. `ComponenteCurricularPorTurma`
3. `ComponenteCurricularAgrupamento`
4. `AgrupamentoAtribuicaoTerritorioSaber`
5. `ComponenteCurricularRegencia`
6. `DadosAulaTurma`
7. `ComponenteCurricularPorAnoLetivo`

## Fases implementadas

### Fase 1 — ComponenteCurricular
- Catálogo de componentes ativos (sem cancelamento).
- **Query:** `SQL_COMPONENTES_NAO_CANCELADOS` — sem parâmetro de ano.

### Fase 2 — ComponenteCurricularPorTurma
- Atribuições reais de componente por turma e professor.
- **Query:** `SQL_COMPONENTES_POR_TURMA` com `?` por ano letivo.
- **Lookups:** A2 (regencia/territorio) e A3 (planejamento).

### Fase 3 — Agrupamentos de Território do Saber
- Escreve em **duas** tabelas: `AgrupamentoAtribuicaoTerritorioSaber` e `ComponenteCurricularAgrupamento`.
- **Query:** `SQL_ATRIBUICOES_TERRITORIO_SABER` (UNION ALL SME RF + Externo CPF, todos os anos).
- Agrupamento ocorre em Python via `_agrupar()`. `cod_agrupamento` é hash MD5 determinístico.

### Fase 4 — ComponenteCurricularRegencia
- Componentes de território atribuídos a turmas de regência.
- **Query:** `SQL_COMPONENTES_TERRITORIO_ATRIBUIDOS` com `?` por ano letivo.
- **Lookups:** A3 (planejamento).

### Fase 5 — DadosAulaTurma
- Data de início de cada componente por turma.
- **Query:** `SQL_DADOS_AULA_TURMA` com `?` por ano letivo.

### Fase 6 — ComponenteCurricularPorAnoLetivo
- Catálogo de oferta de componentes por ano letivo e modalidade.
- **Query:** `SQL_COMPONENTES_POR_ANO_LETIVO` com `?` por ano letivo.

## Fluxo

```{graphviz}
digraph G {
    rankdir=TB;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1\nComponenteCurricular"];
    F2 [label="Fase 2\nComponentePorTurma\n(lookups A2+A3)"];
    F3 [label="Fase 3\nAgrupamentos TS\n(2 tabelas)"];
    F4 [label="Fase 4\nRegencia\n(lookup A3)"];
    F5 [label="Fase 5\nDadosAulaTurma"];
    F6 [label="Fase 6\nPorAnoLetivo"];

    F1 -> F2 -> F3 -> F4 -> F5 -> F6;
}
```
