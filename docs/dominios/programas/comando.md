# Comando `etl_programas`

Arquivo: `apps/programas/management/commands/etl_programas.py`

## Argumentos suportados (via `BaseEtlCommand`)

| Flag | Descrição |
|------|-----------|
| `--volume N` | Tamanho do chunk lido do EOL (herdado; o service síncrono do programas não usa paginação por volume) |
| `--offset N` | Offset inicial (idem) |
| `--fase N` | Força início a partir da fase N (1–5). Ignora checkpoint |
| `--continuar` | Lê o checkpoint mais recente; se `ultima_situacao == "erro"`, retoma em `ultima_pagina + 1` |
| `--carga-inicial` | Passa `primeiro_run=True` para o service (usado pela infraestrutura genérica) |

## Comportamento real

1. lê checkpoint se `--continuar`
2. decide `fase_inicial`
3. cria `id_execucao` via `RepositorioAuditoriaPostgres.iniciar_execucao`
4. executa `EtlProgramasService.executar`
5. registra tabelas lidas e escritas
6. soma `total_alterado`
7. atualiza `token_parada`
8. atualiza checkpoint como `concluido`
9. em erro, salva checkpoint com `ultima_situacao="erro"` e repropaga exceção

## Estratégia de log

As tabelas em `_TABELAS_UPSERT` recebem `modo_escrita="upsert"`; as demais, `full_refresh`.

## Exemplo

```bash
python manage.py etl_programas --volume 500
python manage.py etl_programas --volume 500 --continuar
```