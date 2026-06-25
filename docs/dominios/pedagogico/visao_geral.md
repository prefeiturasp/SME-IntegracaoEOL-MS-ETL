# Visão Geral do Domínio Pedagógico

## Objetivo

Popular `pedagogico_db` com os dados de componentes curriculares do EOL — catálogo, vínculo turma × componente, atribuições de professor, agrupamentos de território do saber, turmas e oferta por ano letivo — servindo de base para os endpoints de planejamento pedagógico do SGP.

## Origem dos Dados

O domínio pedagógico usa duas fontes:

- **EOL (SQL Server)** via `EOLService`, para catálogo, turma, grade, vínculo turma × componente e atribuições.
- **API EOL (PostgreSQL)** via `API_EOL_DB`, para tabelas auxiliares historicamente mantidas pela API EOL e para o agrupamento oficial de Território do Saber.

O agrupamento de Território do Saber é copiado da tabela `agrupamentoatribuicaoterritoriosaber` da API EOL, preservando os identificadores públicos (`cod_agrupamento`) e o histórico físico da origem.

## Classe principal

`EtlPedagogicoService` em `apps/pedagogico/services.py`.

Herda de `BaseEtlService` (pipeline Producer-Consumer com ThreadPool, auditoria incremental via SHA-256 e retry em deadlock).

## Customizações em relação ao `BaseEtlService`

| Customização       | Descrição                                                                                                    |
| :----------------- | :----------------------------------------------------------------------------------------------------------- |
| `_iter_chunks`     | Quando o SQL contém `?`, itera para cada ano letivo substituindo o placeholder; para SQLs da API EOL, usa `ApiEOLService`. |
| `_criar_transform` | Injeta `_agora` via closure por fase, sem overhead por linha.                                                         |
| `_executar_fase`   | Trata fases especiais de Território do Saber: atribuição granular e geração Python de agrupamento somente quando a fase backup é selecionada. |
| `executar`         | Executa as fases na ordem definida e respeita seleção parcial por nome de fase.                                       |

No ETL, `regencia` fica no catálogo `ComponenteCurricular` e é calculada por `CASE` sobre `_IDS_REGENCIA` em `SQL_COMPONENTES_NAO_CANCELADOS`.

## Modelos do app

O código define os modelos em `apps/pedagogico/models.py`, incluindo:

1. `ComponenteCurricular`
2. `ComponenteTurma`
3. `ComponenteCurricularAgrupamento` (tabela mantida para compatibilidade e para a geração backup)
4. `AtribuicaoComponente`
5. `GradeComponenteCurricular`
6. `AgrupamentoAtribuicaoTerritorioSaber`
7. `Turma`
8. `AtribuicaoTerritorioSaber`
9. `TurmaItinerarioEnsinoMedio`
10. `ComponenteCurricularPlanejamentoRegencia`
11. `ComponenteCurricularHierarquia`
12. `ComponenteCurricularPAP`

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

### Fase 4 — AtribuicaoTerritorioSaber

- Atribuições granulares de Território do Saber por turma, componente e professor.
- **Query:** `SQL_ATRIBUICOES_TERRITORIO_SABER` com `?` por ano letivo.
- Serve de apoio para componentes individuais de Território do Saber e para validação de professores atribuídos.

### Fases 5 a 8 — Tabelas auxiliares da API EOL

- Cópia via `API_EOL_DB`, em modo `full_refresh`.
- Tabelas:
  - `componentecurricularpai` → `componente_curricular_hierarquia`
  - `componentecurricularpap` → `componente_curricular_pap`
  - `regenciacomponentecurricular` → `componente_curricular_planejamento_regencia`
  - `turma_tipo_itinerario` → `turma_itinerario_ensino_medio`

### Fase 9 — AgrupamentoAtribuicaoTerritorioSaber

- Copia a tabela oficial `agrupamentoatribuicaoterritoriosaber` da API EOL para `agrupamento_atribuicao_territorio_saber`.
- **Query:** `SQL_API_EOL_AGRUPAMENTO_ATRIBUICAO_TERRITORIO_SABER`.
- Modo `full_refresh`, preservando os códigos de agrupamento e as linhas físicas da origem.
- `cod_agrupamento` é o identificador público usado pelos consumidores, mas não é chave única física.

### Fase backup — agrupamento_territorio_saber_gerado

- Fase opcional, executada apenas quando selecionada explicitamente por nome.
- Recalcula agrupamentos a partir de `SQL_ATRIBUICOES_TERRITORIO_SABER` e grava também `componente_curricular_agrupamento`.
- Mantida como contingência para comparação/recuperação, não como fonte principal.

### Fase 10 — GradeComponenteCurricular

- Catálogo de oferta de componentes por série, ano letivo e modalidade.
- Chave de upsert: componente, ano letivo, modalidade e série de ensino.
- **Query:** `SQL_GRADE_COMPONENTE_CURRICULAR` com `?` por ano letivo.

### Fase 11 — Turma

- Dados cadastrais de turmas do EOL (situação, modalidade, série, UE).
- **Query:** `SQL_TURMAS` com `?` por ano letivo. Filtra `st_turma_escola IN ('O', 'A', 'E', 'C')`.
- `Modalidade`, `CodigoModalidade`, `Semestre` e `Extinta` são calculados via `CASE` inline na query.

## Fluxo

```{graphviz}
digraph G {
    rankdir=TB;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1\nComponenteCurricular"];
    F2 [label="Fase 2\nComponenteTurma"];
    F3 [label="Fase 3\nAtribuicaoComponente"];
    F4 [label="Fase 4\nAtribuicaoTerritorioSaber"];
    F5 [label="Fases 5-8\nApoio API EOL"];
    F9 [label="Fase 9\nAgrupamentos TS\nAPI EOL"];
    F10 [label="Fase 10\nGradeComponenteCurricular"];
    F11 [label="Fase 11\nTurma"];

    F1 -> F2 -> F3 -> F4 -> F5 -> F9 -> F10 -> F11;
}
```
