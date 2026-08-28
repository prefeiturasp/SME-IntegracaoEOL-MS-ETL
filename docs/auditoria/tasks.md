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
| `fases` | list[str] | `None` | Fases específicas do domínio |
| `anos_letivos` | list[int] | `None` | Anos letivos usados como recorte |
| `parametros_disparo` | dict | `None` | Metadados do disparo, como origem, prioridade e agendamento |

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

O `token_parada` do `EtlCheckpointDominio` registra o ponto salvo pelo ETL,
normalmente derivado do total de linhas lidas na fase atual. O delta entre
leituras antes/depois de cada chamada a `executar_dominio` é o sinal que o
loop usa para decidir se continua ou para.

---

## Parâmetros da execução

Cada nova linha de `EtlExecucao` grava o campo JSON `parametros`.

- `parametros.execucao` guarda o que o comando ETL recebeu de fato: `volume`,
  `offset`, `continuar`, `fase`, `fase_inicial`, `fases`, `anos_letivos`,
  `carga_inicial` e `celery`.
- `parametros.disparo` guarda metadados da camada que enfileirou a task, quando
  existirem: `origem`, `prioridade` e `executar_em`.

Esse campo alimenta o dashboard/kanban e evita inferir anos ou fases a partir
do último checkpoint.

---

## Progresso operacional

A tabela `etl_progresso_execucao` registra o ponto atual de uma execução em
andamento. Ela não substitui o checkpoint: o objetivo é alimentar dashboard e
kanban com uma visão viva da fase/chunk atual.

O ETL grava no máximo uma linha por execução/fase e atualiza essa linha com
throttle. O intervalo padrão é controlado por:

```env
ETL_PROGRESS_INTERVAL_SECONDS=15
```

Campos principais:

| Campo | Uso |
|---|---|
| `fase_numero` / `total_fases` | Posição da fase no pipeline |
| `fase_nome` | Nome da fase atual |
| `etapa` | Estado operacional: `fase_iniciada`, `processando_chunk`, `fase_concluida` ou `erro` |
| `chunk_atual` | Número do chunk já processado na fase |
| `linhas_lidas` | Total lido até o momento na fase |
| `linhas_escritas` | Total escrito até o momento na fase |
| `linhas_ignoradas` | Total ignorado por hash igual até o momento |
