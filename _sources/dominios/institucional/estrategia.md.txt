# Estratégia por Tabela

## Incremental (`_upsert_incremental`)

Usa `bulk_create(update_conflicts=True)` com controle de hash SHA-256 por linha.
Apenas registros novos ou alterados são escritos.

- `dre`
- `tipo_escola`
- `sub_prefeitura`
- `unidade_educacional`

## Full Refresh (`_full_refresh`)

Faz `delete()` seguido de `bulk_create()` em transação no `institucional_db`.
Usado em tabelas sem chave natural estável para hash por linha.

- `dre_abrangencia`: substitui integralmente as DREs elegíveis para remover
  registros que deixaram de atender aos critérios da origem.

## Regras do código

- `_upsert_incremental` calcula hash com SHA-256 dos `update_fields`, consulta
  `EtlAuditoriaLinha`, filtra apenas o que mudou e faz `bulk_create(update_conflicts=True)`.
- `_full_refresh` executa `delete()` + `bulk_create()` em transação no `institucional_db`.
- O comando registra `modo_escrita` como `"upsert"` ou `"full_refresh"` em
  `EtlExecucaoTabelaEscrita` com base na constante `_TABELAS_UPSERT`.
