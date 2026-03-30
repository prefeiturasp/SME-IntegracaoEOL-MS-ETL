# Tasks Celery

Arquivo: `apps/controle_auditoria/libs/tasks.py`

## Tasks implementadas

### `verificar_saude`
Task mínima para validar worker e broker.

### `executar_dominio_task`
Parâmetros:
- `dominio`
- `volume`
- `offset`
- `continuar`

## Comportamento

1. lê checkpoint antes
2. chama `call_command("executar_dominio", ...)`
3. lê checkpoint depois
4. calcula `linhas = token_depois - token_antes`
5. se `linhas < volume`, encerra
6. em exceção, faz retry com `continuar=True`

## Observação

O código atual possui `max_retries=5` e `countdown=60`.
