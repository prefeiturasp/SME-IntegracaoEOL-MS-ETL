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
6. Retorna `f"ok:{linhas}"`.

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

- `parametros.execucao` guarda o que o comando ETL recebeu de fato:
  `continuar`, `fase`, `fase_inicial`, `fases`, `anos_letivos`,
  `carga_inicial` e `celery`.
- `parametros.disparo` guarda metadados da camada que enfileirou a task, quando
  existirem: `origem`, `prioridade` e `executar_em`.

Esse campo alimenta o dashboard/kanban e evita inferir anos ou fases a partir
do último checkpoint.

Quando uma execução é reenfileirada pelo recovery, `parametros.disparo` recebe:

```json
{
  "origem": "recovery",
  "execucao_origem": "<uuid da primeira execução com erro>",
  "execucao_erro": "<uuid da execução reprocessada>",
  "tentativa": 1,
  "prioridade": 3,
  "continuar": true
}
```

Durante a execução da task, o worker acrescenta metadados do Celery ao mesmo
bloco:

```json
{
  "celery_task_id": "<id da task>",
  "celery_worker": "<hostname do worker>",
  "celery_retries": 0
}
```

O campo `execucao_origem` permite limitar tentativas mesmo quando uma tentativa
de recovery também falha e gera uma nova execução em erro.

---

## Recovery automático

O script `scripts/recuperar_etl.sh` implementa o fluxo recomendado de recovery:

1. Chama `POST /api/v1/execucoes/limpar-orfas/`.
2. Consulta tasks `active`, `reserved` e `scheduled` no Celery.
3. Preserva execuções cujo `celery_task_id` ainda aparece vivo no Celery.
4. Marca como `interrompido` execuções `em_execucao` ou `em_andamento` sem
   task viva no Celery.
5. Chama `POST /api/v1/execucoes/retomar/`.
6. Localiza a última execução de cada domínio.
7. Mantém apenas as que estão em `interrompido`.
8. Reaproveita `fases` e `anos_letivos` gravados em `parametros.execucao`.
9. Força `continuar=true`.
10. Conta tentativas anteriores com base em `parametros.disparo.execucao_origem`.
11. Agenda uma nova `etl.executar_dominio` quando o limite não foi atingido.

Execuções em `erro` não entram no fluxo automático; elas ficam para retry do
Celery ou para o endpoint manual `POST /api/v1/execucoes/reprocessar-erros/`.

O script adiciona timeout e retry HTTP ao acionamento dos endpoints, mas não
executa ETL diretamente.

Payload fixo usado pelo script:

```json
{
  "max_tentativas": 3
}
```

A retomada é sempre feita por checkpoint, portanto `continuar=true` não precisa
ser enviado no body. O recovery usa prioridade `3` e analisa até 25 domínios
por chamada.

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
