# Visão Geral do Domínio Pedagógico

## Objetivo

Popular `pedagogico_db` com os dados de componentes curriculares do EOL — catálogo, vínculo turma × componente, atribuições de professor, agrupamentos de território do saber, turmas e oferta por ano letivo — servindo de base para os endpoints de planejamento pedagógico do SGP.

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
| `_criar_transform` | Injeta `_agora` via closure por fase, sem overhead por linha. |
| `_executar_fase` | Fase 4 (agrupamentos) é tratada à parte: coleta tudo em memória, agrega em Python e escreve em duas tabelas. |
| `executar` | Registra o resultado duplo da fase de agrupamentos. |

## Regras mantidas fora do ETL

O ETL não calcula mais `planejamento_regencia`, nem grava relação pai de componente em `ComponenteTurma`. Essas regras pertencem ao microsserviço de consumo e às tabelas locais de apoio:

- `componente_curricular_planejamento_regencia`
- `componente_curricular_hierarquia`

No ETL, `regencia` fica no catálogo `ComponenteCurricular` e é calculada por `CASE` sobre `_IDS_REGENCIA` em `SQL_COMPONENTES_NAO_CANCELADOS`.

## Modelos do app

O código define **11 modelos** em `apps/pedagogico/models.py`:

1. `ComponenteCurricular`
2. `ComponenteTurma`
3. `ComponenteCurricularAgrupamento`
4. `AtribuicaoComponente`
5. `GradeComponenteCurricular`
6. `AgrupamentoAtribuicaoTerritorioSaber`
7. `Turma`
8. `TurmaItinerarioEnsinoMedio` (fixture estática; não é fase do ETL)
9. `ComponenteCurricularPlanejamentoRegencia` (tabela local de apoio; não é fase do ETL)
10. `ComponenteCurricularHierarquia` (tabela local de apoio; não é fase do ETL)
11. `ComponenteCurricularPAP` (tabela local de apoio; não é fase do ETL)

## Fases implementadas

### Fase 1 — ComponenteCurricular
- Catálogo de componentes ativos (sem cancelamento).
- **Query:** `SQL_COMPONENTES_NAO_CANCELADOS` — sem parâmetro de ano.
- Também grava a flag `regencia`.

### Fase 2 — ComponenteTurma
- Estrutura turma × componente, sem professor.
- **Query:** `SQL_COMPONENTE_TURMA` com `?` por ano letivo.

### Fase 3 — AtribuicaoComponente
- Relação professor × turma × componente.
- **Query:** `SQL_ATRIBUICAO_COMPONENTE` com `?` por ano letivo.

### Fase 4 — Agrupamentos de Território do Saber
- Escreve em **duas** tabelas: `AgrupamentoAtribuicaoTerritorioSaber` e `ComponenteCurricularAgrupamento`.
- **Query:** `SQL_ATRIBUICOES_TERRITORIO_SABER` (UNION ALL SME RF + Externo CPF, todos os anos).
- Agrupamento ocorre em Python via `_agrupar()`. `cod_agrupamento` é hash MD5 determinístico.

### Fase 5 — GradeComponenteCurricular
- Catálogo de oferta de componentes por série, ano letivo e modalidade.
- Chave de upsert: componente, ano letivo, modalidade, ano turma e série de ensino.
- **Query:** `SQL_GRADE_COMPONENTE_CURRICULAR` com `?` por ano letivo.

### Fase 6 — Turma
- Dados cadastrais de turmas do EOL (situação, modalidade, série, UE).
- **Query:** `SQL_TURMAS` com `?` por ano letivo. Filtra `cd_tipo_turma <> 4` e `st_turma_escola IN ('O', 'A', 'E', 'C')`.
- `Modalidade`, `CodigoModalidade`, `Semestre` e `Extinta` são calculados via `CASE` inline na query.

## Fluxo

```{graphviz}
digraph G {
    rankdir=TB;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1\nComponenteCurricular"];
    F2 [label="Fase 2\nComponenteTurma"];
    F3 [label="Fase 3\nAtribuicaoComponente"];
    F4 [label="Fase 4\nAgrupamentos TS\n(2 tabelas)"];
    F5 [label="Fase 5\nGradeComponenteCurricular"];
    F6 [label="Fase 6\nTurma"];

    F1 -> F2 -> F3 -> F4 -> F5 -> F6;
}
```
