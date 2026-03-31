# Estratégia por Tabela

## Incremental (`_upsert_incremental`)

Usa `bulk_create(update_conflicts=True)` com controle de hash SHA-256 por linha.
Apenas registros novos ou alterados são escritos.

- `unidade_educacional`
- `turma_escola`
- `professor`
- `pessoa`
- `serie_turma_grade`
- `turma_escola_grade_programa`
- `cargo_base_servidor`
- `contrato_externo`
- `atribuicao_aula`
- `atribuicao_externo`

## Full Refresh (`_full_refresh`)

Faz `delete()` seguido de `bulk_create()` em transação no `professores_db`.
Usado em tabelas sem chave natural estável para hash por linha.

- `turma_grade_territorio_experiencia`
- `lotacao_servidor`
- `cargo_sobreposto_servidor`
- `funcao_atividade_cargo_servidor`
- `laudo_medico`

## Regras do código

- `_upsert_incremental` calcula hash com SHA-256 dos `update_fields`, consulta
  `EtlAuditoriaLinha`, filtra apenas o que mudou e faz `bulk_create(update_conflicts=True)`.
- `_full_refresh` executa `delete()` + `bulk_create()` em transação no `professores_db`.
- O comando registra `modo_escrita` como `"upsert"` ou `"full_refresh"` em
  `EtlExecucaoTabelaEscrita` com base na constante `_TABELAS_UPSERT`.
