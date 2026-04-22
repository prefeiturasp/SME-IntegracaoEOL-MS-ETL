# Tasks Celery

Arquivo: `apps/controle_auditoria/libs/tasks.py`

Broker: KeyDB/Redis. Fila padrão: `fila_etl_padrao` (prioridade 0–9).

---

## `verificar_saude`

Task mínima para validar worker e broker. Retorna `"ok"`.

```
name="etl.verificacao_saude"
```

---

## `executar_dominio_task`

```
name="etl.executar_dominio"
bind=True
max_retries=5
```

**Parâmetros:**

| Nome | Tipo | Padrão | Descrição |
|---|---|---|---|
| `dominio` | str | obrigatório | Nome do domínio ETL |
| `volume` | int | `100` | Tamanho do lote por ciclo |
| `offset` | int | `0` | Deslocamento inicial |
| `continuar` | bool | `False` | Retomada por checkpoint |

**Fluxo do loop interno:**

1. Lê `EtlCheckpointDominio(dominio)` → extrai `token_antes`.
2. Monta argumentos para `executar_dominio`; adiciona `--continuar` se `continuar_execucao=True`.
3. Chama `call_command("executar_dominio", --dominio <dominio>, ...)`.
4. Lê checkpoint novamente → extrai `token_depois`.
5. `linhas = max(token_depois − token_antes, 0)`.
6. Se `linhas < volume` → encerra o loop (não há mais trabalho no lote atual).
7. Caso contrário: define `continuar_execucao = True` e repete.
8. Retorna `f"ok:{total_linhas_processadas}"`.

**Em exceção (retry):**

- Chama `self.retry(exc=erro, countdown=60, kwargs={..., "continuar": True})`.
- Máximo de 5 tentativas. Após esgotar, a task falha definitivamente.
- `continuar=True` garante retomada da fase seguinte no checkpoint.

**Observação sobre `token_parada`:**

O `token_parada` do `EtlCheckpointDominio` acumula o total de linhas
*efetivamente alteradas* entre todas as execuções. O delta entre leituras
antes/depois de cada chamada a `executar_dominio` é o sinal de progresso
que o loop usa para decidir se continua ou para.
