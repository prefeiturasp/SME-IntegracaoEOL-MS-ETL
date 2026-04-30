# Estratégia por Tabela

## Upsert Incremental — todas as tabelas

Todas as tabelas do domínio pedagógico usam `upsert` incremental via `BaseEtlService._sync_batch`. Não há `full_refresh` neste domínio.

O controle incremental é feito por hash SHA-256 dos `update_fields` de cada linha, via `EtlAuditoriaLinha`. Apenas registros novos ou alterados são escritos em `pedagogico_db`.

| Tabela | Unique (chave de upsert) |
| :--- | :--- |
| `componente_curricular` | `codigo` |
| `componente_curricular_por_turma` | `(codigo, turma_codigo, professor)` |
| `agrupamento_atribuicao_territorio_saber` | `cod_agrupamento` |
| `componente_curricular_agrupamento` | `(componente_codigo, turma_codigo, codigo_agrupamento)` |
| `componente_inicio_turma` | `(componente_codigo, turma_codigo)` |
| `grade_curricular_serie` | `(codigo_componente_curricular, ano_letivo, modalidade)` |

## Tratamento de `None` no transform

Fases 2 e 5 podem emitir `None` do transform quando a linha está incompleta (ex: `codigo` ou `turma_codigo` nulos). O método `_processar_batch` é sobrescrito em `EtlPedagogicoService` para filtrar esses `None` antes de passar ao batch.

## Fase 3 — escrita em duas tabelas

A fase de agrupamentos escreve sequencialmente em `AgrupamentoAtribuicaoTerritorioSaber` e depois em `ComponenteCurricularAgrupamento`, em lotes de 500. O resultado da fase reporta ambas as contagens separadamente no dict de retorno de `executar()`.
