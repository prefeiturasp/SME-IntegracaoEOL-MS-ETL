# Comando `etl_pedagogico`

Arquivo: `apps/pedagogico/management/commands/etl_pedagogico.py`

Herda de `BaseEtlCommand`. Toda a lógica de argumentos, checkpoint e auditoria está no base.

## Argumentos suportados

Herdados de `BaseEtlCommand`:

- `--volume` — tamanho do batch de leitura
- `--offset` — offset inicial
- `--continuar` — retoma a partir do último checkpoint salvo
- `--primeiro-run` — sinaliza primeiro run (sem filtro incremental)
- `--particao` / `--total-particoes` — processamento particionado

## Comportamento

1. Lê checkpoint se `--continuar`
2. Decide `fase_inicial`
3. Cria `id_execucao` via `RepositorioAuditoriaPostgres.iniciar_execucao`
4. Instancia `EtlPedagogicoService` e chama `executar(fase_inicial)`
5. Registra tabelas lidas e escritas em `EtlExecucaoTabelaEscrita`
6. Atualiza `token_parada`
7. Salva checkpoint como `concluido`
8. Em erro: salva checkpoint com `ultima_situacao="erro"` e repropaga exceção

## Modo de escrita

Todas as 7 tabelas do domínio estão em `_TABELAS_UPSERT` — `get_modo_escrita` retorna `"upsert"` para todas.

## Exemplos

```bash
python manage.py etl_pedagogico
python manage.py etl_pedagogico --continuar
python manage.py etl_pedagogico --primeiro-run
python manage.py etl_pedagogico --particao 0 --total-particoes 4
```
