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
| `_criar_transform` | Injeta `_agora` e lookup de regência via closure por fase, sem overhead por linha. |
| `_executar_fase` | Fase 3 (agrupamentos) é tratada à parte: coleta tudo em memória, agrega em Python e escreve em duas tabelas. |
| `executar` | Pré-carrega lookup antes da fase 2 e registra resultado duplo da fase 3. |

## Lookup pré-carregado

`_carregar_lookups` é chamado uma vez antes da fase 2:

- **A3** — `SQL_LOOKUP_PLANEJAMENTO_REGENCIA` → dois sets: `exact: set[(codigo, turno, ano)]` e `fallback: set[int]`. Fonte de `planejamento_regencia`.

`regencia` e `territorio_saber` **não** dependem de lookup separado — os flags `EhRegencia` e `EhTerritorio` são calculados diretamente nas cláusulas `CASE` de `SQL_COMPONENTES_POR_TURMA`.

## Modelos do app

O código define **8 modelos** em `apps/pedagogico/models.py`:

1. `ComponenteCurricular`
2. `ComponenteCurricularPorTurma`
3. `ComponenteCurricularAgrupamento`
4. `ComponenteInicioTurma`
5. `GradeCurricularSerie`
6. `AgrupamentoAtribuicaoTerritorioSaber`
7. `RegenciaComponenteCurricular` (tabela local de apoio; não é fase do ETL)
8. `ComponenteCurricularPAP` (tabela local de apoio; não é fase do ETL)

## Fases implementadas

### Fase 1 — ComponenteCurricular
- Catálogo de componentes ativos (sem cancelamento).
- **Query:** `SQL_COMPONENTES_NAO_CANCELADOS` — sem parâmetro de ano.

### Fase 2 — ComponenteCurricularPorTurma
- Atribuições reais de componente por turma e professor.
- **Query:** `SQL_COMPONENTES_POR_TURMA` com `?` por ano letivo.
- **Lookup:** A3 (planejamento de regência). `regencia` e `territorio_saber` vêm inline da query.

### Fase 3 — Agrupamentos de Território do Saber
- Escreve em **duas** tabelas: `AgrupamentoAtribuicaoTerritorioSaber` e `ComponenteCurricularAgrupamento`.
- **Query:** `SQL_ATRIBUICOES_TERRITORIO_SABER` (UNION ALL SME RF + Externo CPF, todos os anos).
- Agrupamento ocorre em Python via `_agrupar()`. `cod_agrupamento` é hash MD5 determinístico.

### Fase 4 — ComponenteInicioTurma
- Data de início e periodicidade de cada componente por turma.
- **Query:** `SQL_COMPONENTE_INICIO_TURMA` com `?` por ano letivo.

### Fase 5 — GradeCurricularSerie
- Catálogo de oferta de componentes por série, ano letivo e modalidade.
- **Query:** `SQL_GRADE_CURRICULAR_SERIE` com `?` por ano letivo.

## Fluxo

```{graphviz}
digraph G {
    rankdir=TB;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1\nComponenteCurricular"];
    F2 [label="Fase 2\nComponentePorTurma\n(lookup A3)"];
    F3 [label="Fase 3\nAgrupamentos TS\n(2 tabelas)"];
    F4 [label="Fase 4\nComponenteInicioTurma"];
    F5 [label="Fase 5\nGradeCurricularSerie"];

    F1 -> F2 -> F3 -> F4 -> F5;
}
```
