# Mapeamento ETL (Origem → Destino)

Esta página documenta o fluxo real implementado nos métodos `popular_*` do serviço.

| Método | Tabela destino | Estratégia | SQL de origem |
|---|---|---|---|
| `popular_dre` | `dre` | `upsert_incremental` | `SQL_DRE` |
| `popular_tipos_escola` | `tipo_escola` | `upsert_incremental` | `SQL_TIPO_ESCOLA` |
| `popular_componentes_curriculares` | `componente_curricular` | `upsert_incremental` | `SQL_COMPONENTES_CURRICULARES` |
| `popular_series_ensino` | `serie_ensino` | `upsert_incremental` | `SQL_SERIES_ENSINO` |
| `popular_territorios_saber` | `territorio_saber` | `upsert_incremental` | `SQL_TERRITORIOS_SABER` |
| `popular_tipos_experiencia` | `tipo_experiencia_pedagogica` | `upsert_incremental` | `SQL_TIPOS_EXPERIENCIA` |
| `popular_grades` | `grade` | `upsert_incremental` | `SQL_GRADES` |
| `popular_cargos` | `cargo` | `upsert_incremental` | `SQL_CARGOS` |
| `popular_funcoes_funcionario_externo` | `funcao_funcionario_externo` | `upsert_incremental` | `SQL_FUNCOES_EXTERNO` |
| `popular_unidades_educacionais` | `unidades_educacionais` | `full_refresh` | `SQL_UNIDADES_EDUCACIONAIS` |
| `popular_escola_grades` | `escola_grade` | `upsert_incremental` | `SQL_ESCOLA_GRADES` |
| `popular_turmas_escola` | `turma_escola` | `upsert_incremental` | `SQL_TURMAS_ESCOLA` |
| `popular_professores` | `professor` | `upsert_incremental` | `SQL_PROFESSORES` |
| `popular_pessoas` | `pessoa` | `upsert_incremental` | `SQL_PESSOAS` |
| `popular_serie_turma_grade` | `serie_turma_grade` | `upsert_incremental` | `SQL_SERIE_TURMA_GRADE` |
| `popular_turma_escola_grade_programa` | `turma_escola_grade_programa` | `upsert_incremental` | `SQL_TURMA_ESCOLA_GRADE_PROGRAMA` |
| `popular_cargos_base` | `cargo_base_servidor` | `upsert_incremental` | `SQL_CARGOS_BASE` |
| `popular_contratos_externos` | `contrato_externo` | `upsert_incremental` | `SQL_CONTRATOS_EXTERNOS` |
| `popular_turma_grade_territorio_experiencia` | `turma_grade_territorio_experiencia` | `full_refresh` | `SQL_TURMA_GRADE_TERRITORIO` |
| `popular_lotacoes` | `lotacoes` | `full_refresh` | `SQL_LOTACOES` |
| `popular_cargos_sobrepostos` | `cargos_sobrepostos` | `full_refresh` | `SQL_CARGOS_SOBREPOSTOS` |
| `popular_funcoes_atividade` | `funcoes_atividade` | `full_refresh` | `SQL_FUNCOES_ATIVIDADE` |
| `popular_laudos` | `laudos` | `full_refresh` | `SQL_LAUDOS` |
| `popular_atribuicoes_aula` | `atribuicao_aula` | `upsert_incremental` | `SQL_ATRIBUICOES_AULA` |
| `popular_atribuicoes_externo` | `atribuicao_externo` | `upsert_incremental` | `SQL_ATRIBUICOES_EXTERNO` |

## Observações importantes

- `popular_unidades_educacionais` usa `full_refresh`.
- `popular_turma_grade_territorio_experiencia`, `popular_lotacoes`, `popular_cargos_sobrepostos`, `popular_funcoes_atividade` e `popular_laudos` usam `full_refresh`.
- `popular_atribuicoes_aula` e `popular_atribuicoes_externo` usam `upsert_incremental` com hash.
- a constante `_TABELAS_UPSERT` no comando confirma quais tabelas são tratadas como incremental no log de auditoria.
