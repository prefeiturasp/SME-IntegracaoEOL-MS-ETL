# Estratégia por Tabela

## Incremental (upsert por hash)

**Todas as 8 fases do domínio `programas` usam `modo_escrita="upsert"`.** Não há
tabelas com carga `full_refresh` hoje.

A escrita é feita por `bulk_create(update_conflicts=True, ...)` com controle de
hash SHA-256 por linha, encapsulado em `BaseEtlService._upsert_incremental` —
herdado pelo `EtlProgramasService`.

Tabelas em modo upsert:

- `tipo_programa`
- `componente_curricular_programa`
- `turma_programa`
- `turma_programa_componente_curricular`
- `matricula_turma_programa`
- `matricula_turma_programa_historico`
- `aluno_pap_ano_letivo`
- `aluno_pap_ano_letivo_historico`

## Full Refresh (não usado atualmente)

`BaseEtlCommand` suporta `modo_escrita="full_refresh"`, e o `etl_programas.Command.get_modo_escrita()` retorna `"full_refresh"` para qualquer tabela **fora** do set `_TABELAS_UPSERT`. Hoje todas as tabelas do domínio estão em `_TABELAS_UPSERT`, então nenhuma cai nesse caminho.

Se, no futuro, uma fase nova for adicionada e precisar de carga destrutiva (ex.: tabela pequena sem chave natural estável), basta não incluí-la em `_TABELAS_UPSERT` — o comando passará a registrar `modo_escrita="full_refresh"` na auditoria automaticamente.

## Regras do código

- `_upsert_incremental` (em `apps/core/libs/base_etl_service.py`, herdado pelo
  `EtlProgramasService`):
  1. Calcula hash SHA-256 dos `update_fields` declarados no `PhaseConfig`
     (excluindo o `timestamp_field`, se houver).
  2. Deduplica os objetos pela chave natural (`unique_fields`), mantendo o
     último em caso de duplicata da origem.
  3. Monta `id_destino = "{tabela}:{pk1}:{pk2}..."`.
  4. Consulta hashes existentes em `EtlAuditoriaLinha` (banco `default`).
  5. Filtra apenas o que mudou ou é novo.
  6. Atualiza `timestamp_field` (`atualizado_em`) nos registros alterados,
     quando o modelo possui o campo.
  7. Faz `bulk_create(update_conflicts=True, ...)` no `programas_db`.
  8. Grava os novos hashes de volta em `EtlAuditoriaLinha`.

- O comando registra `modo_escrita="upsert"` em `EtlExecucaoTabelaEscrita` para
  todas as tabelas do domínio.
