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
2. `ComponenteCurricularApiEol`
3. `ComponenteTurma`
4. `ComponenteCurricularAgrupamento` (tabela mantida para compatibilidade e para a geração backup)
5. `AtribuicaoComponente`
6. `GradeComponenteCurricular`
7. `AgrupamentoAtribuicaoTerritorioSaber`
8. `Turma`
9. `AtribuicaoTerritorioSaber`
10. `TurmaItinerarioEnsinoMedio`
11. `ComponenteCurricularPlanejamentoRegencia`
12. `ComponenteCurricularHierarquia`
13. `ComponenteCurricularPAP`

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

### Fases 5 a 9 — Tabelas auxiliares da API EOL

- Cópia via `API_EOL_DB`, em modo `full_refresh`.
- Tabelas:
  - `componentecurricular LEFT JOIN componentecurricularpai` → `componente_curricular_api_eol`
  - `componentecurricularpai` → `componente_curricular_hierarquia`
  - `componentecurricularpap` → `componente_curricular_pap`
  - `regenciacomponentecurricular` → `componente_curricular_planejamento_regencia`
  - `turma_tipo_itinerario` → `turma_itinerario_ensino_medio`

### Fase 10 — AgrupamentoAtribuicaoTerritorioSaber

- Copia a tabela oficial `agrupamentoatribuicaoterritoriosaber` da API EOL para `agrupamento_atribuicao_territorio_saber`.
- **Query:** `SQL_API_EOL_AGRUPAMENTO_ATRIBUICAO_TERRITORIO_SABER`.
- Modo `full_refresh`, preservando os códigos de agrupamento e as linhas físicas da origem.
- `cod_agrupamento` é o identificador público usado pelos consumidores, mas não é chave única física.

### Fase backup — agrupamento_territorio_saber_gerado

- Fase opcional, executada apenas quando selecionada explicitamente por nome.
- Recalcula agrupamentos a partir de `SQL_ATRIBUICOES_TERRITORIO_SABER` e grava também `componente_curricular_agrupamento`.
- Mantida como contingência para comparação/recuperação, não como fonte principal.

### Fase 11 — GradeComponenteCurricular

- Catálogo de oferta de componentes por série, ano letivo e modalidade.
- Chave de upsert: componente, ano letivo, modalidade e série de ensino.
- **Query:** `SQL_GRADE_COMPONENTE_CURRICULAR` com `?` por ano letivo.

### Fase 12 — Turma

- Dados cadastrais de turmas do EOL (situação, modalidade, série, UE).
- **Query:** `SQL_TURMAS` com `?` por ano letivo. Filtra `st_turma_escola IN ('O', 'A', 'E', 'C')`.
- `Modalidade`, `CodigoModalidade`, `Semestre` e `Extinta` são calculados via `CASE` inline na query.

### Fase 13 — TurmaAtribuidaDreUe

- Consolida turmas por DRE e UE para o ano letivo.
- A carga usa `full_refresh` na tabela `turma_atribuida_dre_ue`.

## Fluxo

```{graphviz}
digraph G {
    rankdir=TB;
    node [shape=box, style="rounded"];

    F1 [label="Fase 1\nComponenteCurricular"];
    F2 [label="Fase 2\nComponenteTurma"];
    F3 [label="Fase 3\nAtribuicaoComponente"];
    F4 [label="Fase 4\nAtribuicaoTerritorioSaber"];
    F5 [label="Fases 5-9\nApoio API EOL"];
    F10 [label="Fase 10\nAgrupamentos TS\nAPI EOL"];
    F11 [label="Fase 11\nGradeComponenteCurricular"];
    F12 [label="Fase 12\nTurma"];
    F13 [label="Fase 13\nTurmaAtribuidaDreUe"];

    F1 -> F2 -> F3 -> F4 -> F5 -> F10 -> F11 -> F12 -> F13;
}
```
