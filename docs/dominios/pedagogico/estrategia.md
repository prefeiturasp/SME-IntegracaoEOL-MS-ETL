# Estratégia por Tabela

## Modos de escrita

As fases extraídas do EOL SQL Server usam `upsert` incremental via `BaseEtlService._sync_batch`.

O controle incremental é feito por hash SHA-256 dos `update_fields` de cada linha, via `EtlAuditoriaLinha`. Apenas registros novos ou alterados são escritos em `pedagogico_db`.

As fases extraídas da API EOL PostgreSQL usam `full_refresh` com `truncate_on_full_sync=True`, porque essas tabelas são pequenas/de apoio ou precisam espelhar a origem inteira.

| Tabela | Unique (chave de upsert) |
| :--- | :--- |
| `componente_curricular` | `codigo` |
| `componente_turma` | `(turma_codigo, componente_codigo)` |
| `atribuicao_componente` | `(turma_codigo, componente_codigo, professor)` |
| `atribuicao_territorio_saber` | `(turma_codigo, componente_codigo, professor, codigo_territorio_saber, codigo_experiencia_pedagogica, dt_atribuicao, dt_disponibilizacao)` |
| `grade_componente_curricular` | `(codigo_componente_curricular, ano_letivo, modalidade, codigo_serie_ensino)` |
| `turma` | `codigo` |

| Tabela | Modo | Origem |
| :--- | :--- | :--- |
| `componente_curricular_hierarquia` | `full_refresh` | `componentecurricularpai` |
| `componente_curricular_pap` | `full_refresh` | `componentecurricularpap` |
| `componente_curricular_planejamento_regencia` | `full_refresh` | `regenciacomponentecurricular` |
| `turma_itinerario_ensino_medio` | `full_refresh` | `turma_tipo_itinerario` |
| `agrupamento_atribuicao_territorio_saber` | `full_refresh` | `agrupamentoatribuicaoterritoriosaber` |

## Tratamento de `None` no transform

Fases 2 e 3 podem emitir `None` do transform quando a linha está incompleta (ex: `turma_codigo`, `componente_codigo` ou `professor` nulos). O método `_processar_batch` é sobrescrito em `EtlPedagogicoService` para filtrar esses `None` antes de passar ao batch.

## Agrupamento de Território do Saber

A carga principal de agrupamentos copia `agrupamentoatribuicaoterritoriosaber` da API EOL para `AgrupamentoAtribuicaoTerritorioSaber`, em `full_refresh`.

`cod_agrupamento` permanece como ID de contrato e possui índice para consulta, mas não é chave única: a mesma origem de agrupamento pode ter linhas distintas por professor ou histórico.

A fase `agrupamento_territorio_saber_gerado` continua disponível como backup selecionável. Quando executada explicitamente, ela gera agrupamentos localmente e também grava `ComponenteCurricularAgrupamento`.
