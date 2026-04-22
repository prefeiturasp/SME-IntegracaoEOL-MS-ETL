# Estratégia por Tabela

## Incremental (`_upsert_incremental`)

**Todas as 5 tabelas do domínio `programas` usam esta estratégia.** Não há tabelas com carga `full_refresh` hoje.

Usa `bulk_create(update_conflicts=True)` com controle de hash SHA-256 por linha.
Apenas registros novos ou alterados são escritos.

- `tipo_programa`
- `componente_curricular_programa`
- `turma_programa`
- `turma_programa_componente_curricular`
- `matricula_turma_programa`

## Full Refresh (não usado atualmente)

O `BaseEtlCommand` suporta `modo_escrita="full_refresh"` e o `etl_programas.Command.get_modo_escrita()` retornaria `"full_refresh"` para qualquer tabela **fora** do set `_TABELAS_UPSERT`. Como todas as tabelas do domínio estão em `_TABELAS_UPSERT`, nenhuma cai nesse caminho hoje.

Se, no futuro, uma fase nova for adicionada e precisar de carga destrutiva (ex.: tabela pequena sem chave natural estável), basta não incluí-la em `_TABELAS_UPSERT` — o comando passará a registrar `modo_escrita="full_refresh"` na auditoria automaticamente.

## Regras do código

- `_upsert_incremental` (em `apps/programas/services.py`):
  1. Calcula hash SHA-256 dos `update_fields` (excluindo o `timestamp_field`, se houver).
  2. Deduplica os objetos pela chave natural (`unique_fields`), mantendo o último em caso de duplicata da origem.
  3. Monta `id_destino = "{tabela}:{pk1}:{pk2}..."`.
  4. Consulta hashes existentes em `EtlAuditoriaLinha` (banco `default`).
  5. Filtra apenas o que mudou ou é novo.
  6. Atualiza `timestamp_field` nos registros alterados (se configurado).
  7. Faz `bulk_create(update_conflicts=True, ...)` no `programas_db`.
  8. Grava os novos hashes de volta em `EtlAuditoriaLinha`.

- O comando registra `modo_escrita="upsert"` em `EtlExecucaoTabelaEscrita` para todas as tabelas do domínio programas atualmente.
