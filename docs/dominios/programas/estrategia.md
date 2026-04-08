# Estratégia por Tabela

## Incremental (`_upsert_incremental`)

Usa `bulk_create(update_conflicts=True)` com controle de hash SHA-256 por linha.
Apenas registros novos ou alterados são escritos.

- `tipo_programa`
- `componente_curricular_programa`
- `turma_programa`
- `turma_programa_componente_curricular`
- `matricula_turma_programa`

## Full Refresh (`_full_refresh`)

Faz `delete()` seguido de `bulk_create()` em transação no `programas_db`.
Usado em tabelas sem chave natural estável para hash por linha.

## Regras do código

- `_upsert_incremental` calcula hash com SHA-256 dos `update_fields`, consulta
  `EtlAuditoriaLinha`, filtra apenas o que mudou e faz `bulk_create(update_conflicts=True)`.
- `_full_refresh` executa `delete()` + `bulk_create()` em transação no `programas_db`.
- O comando registra `modo_escrita` como `"upsert"` ou `"full_refresh"` em
  `EtlExecucaoTabelaEscrita` com base na constante `_TABELAS_UPSERT`.