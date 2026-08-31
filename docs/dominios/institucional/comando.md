# Comando `etl_institucional`

Arquivo: `apps/institucional/management/commands/etl_institucional.py`

## Argumentos suportados

- `--continuar`

## Comportamento real

1. lê checkpoint se `--continuar`
2. decide `fase_inicial`
3. cria `id_execucao` via `RepositorioAuditoriaPostgres.iniciar_execucao`
4. executa `EtlProfessoresService.executar`
5. registra tabelas lidas e escritas
6. soma `total_alterado`
7. atualiza `token_parada`
8. atualiza checkpoint como `concluido`
9. em erro, salva checkpoint com `ultima_situacao="erro"` e repropaga exceção

## Estratégia de log

As tabelas em `_TABELAS_UPSERT` recebem `modo_escrita="upsert"`; as demais, `full_refresh`.

## Exemplo

```bash
python manage.py etl_institucional
python manage.py etl_institucional --continuar
```
