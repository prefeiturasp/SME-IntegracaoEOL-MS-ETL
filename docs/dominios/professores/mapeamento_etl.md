# Mapeamento ETL (Origem → Destino)

Documenta o fluxo real implementado nos métodos `popular_*` do serviço.

## Fase 1 — sem dependências internas

| Método | Tabela destino | Estratégia | SQL / Fonte |
|---|---|---|---|
| `popular_unidades_educacionais` | `unidade_educacional` | `upsert_incremental` | `v_cadastro_unidade_educacao` |
| `popular_turmas_escola` | `turma_escola` | `upsert_incremental` | `turma_escola` |
| `popular_professores` | `professor` | `upsert_incremental` | `v_servidor_cotic` |
| `popular_pessoas` | `pessoa` | `upsert_incremental` | `pessoa` |

## Fase 2 — dependem da Fase 1

| Método | Tabela destino | Estratégia | SQL / Fonte |
|---|---|---|---|
| `popular_serie_turma_grade` | `serie_turma_grade` | `upsert_incremental` | `serie_turma_grade` |
| `popular_turma_escola_grade_programa` | `turma_escola_grade_programa` | `upsert_incremental` | `turma_escola_grade_programa` |
| `popular_cargos_base` | `cargo_base_servidor` | `upsert_incremental` | `v_cargo_base_cotic` |
| `popular_contratos_externos` | `contrato_externo` | `upsert_incremental` | `contrato_externo` |

## Fase 3 — dependem da Fase 2

| Método | Tabela destino | Estratégia | SQL / Fonte |
|---|---|---|---|
| `popular_turma_grade_territorio_experiencia` | `turma_grade_territorio_experiencia` | `full_refresh` | `turma_grade_territorio_experiencia` |
| `popular_lotacoes` | `lotacao_servidor` | `full_refresh` | `lotacao_servidor` |
| `popular_cargos_sobrepostos` | `cargo_sobreposto_servidor` | `full_refresh` | `cargo_sobreposto_servidor` |
| `popular_funcoes_atividade` | `funcao_atividade_cargo_servidor` | `full_refresh` | `funcao_atividade_cargo_servidor` |
| `popular_laudos` | `laudo_medico` | `full_refresh` | `laudo_medico` |
| `popular_atribuicoes_aula` | `atribuicao_aula` | `upsert_incremental` | `atribuicao_aula` |
| `popular_atribuicoes_externo` | `atribuicao_externo` | `upsert_incremental` | `atribuicao_externo` |

## Observações

- Domínios externos (DRE, TipoEscola, ComponenteCurricular, Cargo, etc.) **não são carregados**.
  Apenas seus IDs são armazenados nos campos `codigo_*` dos modelos acima.
- `_TABELAS_UPSERT` no comando `etl_professores` define quais tabelas registram
  `modo_escrita="upsert"` em `EtlExecucaoTabelaEscrita`.
- As 5 tabelas `full_refresh` não possuem chave natural para hash por linha —
  o controle de mudanças é feito via recarga completa em transação.
