# Estratégia por Tabela

## Incremental (`_upsert_incremental`)

Usa `bulk_create(update_conflicts=True)` com controle de hash SHA-256 por linha.
Apenas registros novos ou alterados são escritos.

- `professor`
- `pessoa`
- `cargo_base_servidor`
- `contrato_externo`
- `atribuicao_aula`
- `atribuicao_externo`
- `funcionario_unidade_educacional`

## Full Refresh (`_full_refresh_por_lote`)

Faz `delete()` em todos os registros uma única vez, seguido de `bulk_create()` a cada lote recebido.
Não usa transação global — a tabela fica temporariamente vazia durante a carga.
Usado em tabelas sem chave natural estável para hash por linha.

- `lotacao_servidor`
- `cargo_sobreposto_servidor`
- `funcao_atividade_cargo_servidor`
- `laudo_medico`

## Regras do código

- `_upsert_incremental` calcula hash com SHA-256 dos `update_fields`, consulta
  `EtlAuditoriaLinha`, filtra apenas o que mudou e faz `bulk_create(update_conflicts=True)`.
- `_full_refresh_por_lote` executa `delete()` global seguido de `bulk_create()` por lote, sem transação global.
- O comando registra `modo_escrita` como `"upsert"` ou `"full_refresh"` em
  `EtlExecucaoTabelaEscrita` com base na constante `_TABELAS_UPSERT`.
