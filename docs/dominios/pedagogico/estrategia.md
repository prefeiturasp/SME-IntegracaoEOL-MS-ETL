# Estratégia por Tabela

## Upsert Incremental — todas as tabelas

Todas as tabelas do domínio pedagógico usam `upsert` incremental via `BaseEtlService._sync_batch`. Não há `full_refresh` neste domínio.

O controle incremental é feito por hash SHA-256 dos `update_fields` de cada linha, via `EtlAuditoriaLinha`. Apenas registros novos ou alterados são escritos em `pedagogico_db`.

| Tabela | Unique (chave de upsert) |
| :--- | :--- |
| `componente_curricular` | `codigo` |
| `componente_turma` | `(turma_codigo, componente_codigo)` |
| `atribuicao_componente` | `(turma_codigo, componente_codigo, professor)` |
| `agrupamento_atribuicao_territorio_saber` | `(cod_turma, cod_territorio_saber, cod_experiencia_pedagogica, rf_professor, dt_inicio_atribuicao, cod_componentes_curriculares)` |
| `componente_curricular_agrupamento` | `(componente_codigo, turma_codigo, codigo_agrupamento, rf_professor)` |
| `grade_componente_curricular` | `(codigo_componente_curricular, ano_letivo, modalidade, codigo_serie_ensino)` |
| `turma` | `codigo` |

## Tratamento de `None` no transform

Fases 2 e 3 podem emitir `None` do transform quando a linha está incompleta (ex: `turma_codigo`, `componente_codigo` ou `professor` nulos). O método `_processar_batch` é sobrescrito em `EtlPedagogicoService` para filtrar esses `None` antes de passar ao batch.

## Fase 4 — escrita em duas tabelas

A fase de agrupamentos escreve sequencialmente em `AgrupamentoAtribuicaoTerritorioSaber` e depois em `ComponenteCurricularAgrupamento`, em lotes de 500. O resultado da fase reporta ambas as contagens separadamente no dict de retorno de `executar()`.

`cod_agrupamento` permanece como ID de contrato/legado e possui índice para consulta, mas não é chave única: a mesma origem de agrupamento pode ter linhas distintas por professor ou histórico.
