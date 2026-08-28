# API de Auditoria

O app `controle_auditoria` expõe endpoints DRF para monitoramento, auditoria e execução de domínios ETL.

Autenticação: `X-API-Key` via `ApiKeyAuthentication` (header `X-API-Key`).
Usa `secrets.compare_digest()` para proteção contra timing attacks.

---

## Rotas REST (`api/v1/`)

Registradas em `apps/controle_auditoria/api/urls.py` e incluídas via `config/urls.py`.

| Método | Rota | View | Auth | Descrição |
|---|---|---|---|---|
| `GET` | `checkpoints/` | `CheckpointsView` | sim | Lista checkpoints por domínio |
| `GET` | `execucoes/` | `ExecucoesView` | sim | 50 execuções mais recentes |
| `POST` | `execucoes/limpar-orfas/` | `LimparOrfasView` | sim | Marca execuções órfãs como interrompidas |
| `POST` | `execucoes/reprocessar-erros/` | `ReprocessarErrosView` | sim | Reprocessa últimas execuções com erro |
| `GET` | `execucoes/<id_execucao>/` | `ExecucaoDetalheView` | sim | Detalhe com tabelas lidas e escritas |
| `GET` | `execucoes/tabelas-lidas/` | `ExecucoesTabelaLidaView` | sim | 50 registros de leitura mais recentes |
| `GET` | `execucoes/tabelas-escritas/` | `ExecucoesTabelaEscritaView` | sim | 50 registros de escrita mais recentes |
| `POST` | `dominios/<dominio>/executar/` | `ExecutarDominioView` | sim | Dispara execução via Celery |
| `GET` | `monitoramento/execucoes/` | `MonitoramentoExecucoesView` | não | Execuções com filtros (público) |
| `GET` | `monitoramento/resumo/` | `MonitoramentoResumoView` | não | Última execução por domínio (público) |
| `GET` | `sinc_rec/health/` | `HealthSincRecView` | não | Healthcheck do banco de auditoria |

---

## Rotas de Dashboard (HTML)

Registradas diretamente em `config/urls.py`. Renderizam templates HTML.

| Método | Rota | View | Auth | Descrição |
|---|---|---|---|---|
| `GET` | `/dashboard/` | `DashboardView` | não | Dashboard com resumo por domínio e execuções recentes |
| `GET` | `/dashboard/kanban/` | `KanbanView` | não | Kanban com estágios de leitura, hash, escrita e checkpoint |

### `DashboardView`

Suporta filtros via query string: `dominio`, `data_inicio`, `data_fim`, `situacao`.

Exibe:
- Última execução por domínio com `total_processado` (via `token_parada`).
- Escopo usado no disparo quando disponível: anos letivos, fases, volume,
  offset, flag de retomada e prioridade.
- Até 100 execuções filtradas.
- Últimas 10 execuções com detalhes de tabelas escritas.

### `KanbanView`

Suporta filtro: `dominio`.

Exibe por domínio:
- Coluna **Leitura EOL** — tabelas lidas e contagem.
- Coluna **Hash Control** — contagem de `EtlAuditoriaLinha` por tabela.
- Coluna **Escrita (Upsert)** — tabelas escritas e modo.
- Coluna **Checkpoint** — token acumulado, escopo da execução, fase em
  andamento ou ponto de falha, último sucesso.
- Tabela **Tempo por fase** — fases ordenadas pela maior duração, com linhas
  lidas, gravadas, taxa por minuto e etapa atual.

---

## Detalhes por endpoint REST

### `GET checkpoints/`

Retorna todos os `EtlCheckpointDominio` ordenados por domínio.

Campos: `dominio`, `ultimo_id_execucao`, `ultima_pagina`, `token_parada`,
`ultima_situacao`, `ultimo_sucesso_em`, `atualizado_em`.

---

### `GET execucoes/`

Retorna as 50 execuções ETL mais recentes, ordenadas por `iniciado_em` decrescente.

---

### `GET execucoes/<id_execucao>/`

Retorna uma execução identificada pelo UUID `id_execucao`, com `tabelas_lidas` e
`tabelas_escritas` aninhadas.

O campo `parametros` registra o escopo usado no disparo:

```json
{
  "execucao": {
    "volume": 100,
    "offset": 0,
    "continuar": true,
    "fase": 0,
    "fase_inicial": 1,
    "fases": ["aluno"],
    "anos_letivos": [2026],
    "carga_inicial": false,
    "celery": false
  },
  "disparo": {
    "origem": "api",
    "prioridade": 5,
    "executar_em": null
  }
}
```

Retorna `404` se o UUID não existir.

---

### `POST execucoes/limpar-orfas/`

Marca como `interrompido` execuções que continuam em `em_execucao` ou
`em_andamento`, mas não têm task viva no Celery.

Critério:

- se `parametros.disparo.celery_task_id` ainda aparece em
  `active`, `reserved` ou `scheduled` no Celery, a execução é preservada;
- se não houver `celery_task_id`, a execução é considerada órfã;
- se houver `celery_task_id`, mas ele não aparecer no Celery, marca como
  `interrompido`;
- o `celery_task_id` é gravado no disparo da API e reaproveitado pelo worker;
- se o estado dos workers Celery não puder ser consultado, retorna `503` e não
  altera nenhuma execução.

O body é vazio:

```json
{}
```

Retorna `200` com a quantidade analisada, interrompida, preservada e a lista
de itens analisados. Quando uma execução é preservada, o campo `motivo` indica
`task_celery_viva`. Quando é interrompida, o campo `motivo` indica
`sem_task_id` ou `task_celery_ausente`.

---

### `POST execucoes/reprocessar-erros/`

Busca a última execução de cada domínio quando ela está em `erro` ou
`interrompido` e agenda uma nova task com `continuar=true`, reaproveitando os
parâmetros gravados em `parametros.execucao`.

Por segurança, erros antigos não são reprocessados se o domínio já tiver uma
execução mais recente em andamento ou concluída.

**Body JSON:**

| Campo | Tipo | Padrão | Descrição |
|---|---|---|---|
| `max_tentativas` | int | `3` | Máximo de reprocessamentos automáticos por execução raiz |

Exemplo:

```json
{
  "max_tentativas": 3
}
```

Retorna `202`:

```json
{
  "total_analisado": 1,
  "total_reprocessado": 1,
  "itens": [
    {
      "dominio": "programas",
      "id_execucao": "585358e1-8233-49c2-b224-06085d8bc501",
      "status": "reprocessado",
      "task_id": "task-recovery",
      "tentativa": 1,
      "fases": null,
      "anos_letivos": [2026],
      "volume": 500
    }
  ]
}
```

Quando o limite de tentativas é atingido, o item volta como `ignorado` e nenhuma
task é enfileirada para aquela execução.

---

### `GET execucoes/tabelas-lidas/` e `GET execucoes/tabelas-escritas/`

Retornam os 50 registros mais recentes de `EtlExecucaoTabelaLida` e
`EtlExecucaoTabelaEscrita`, respectivamente.

---

### `POST dominios/<dominio>/executar/`

Agenda ou executa imediatamente a sincronização de um domínio.

**Body JSON:**

| Campo | Tipo | Padrão | Descrição |
|---|---|---|---|
| `volume` | int | `100` | Quantidade de registros processados por lote. Valores maiores reduzem a quantidade de ciclos, mas aumentam memória e duração de cada tentativa |
| `offset` | int | `0` | Posição inicial da leitura. Normalmente fica `0`; use apenas para iniciar de um ponto específico |
| `continuar` | bool | `false` | Quando `true`, retoma pelo checkpoint do domínio. Quando `false`, começa conforme o `offset` informado |
| `executar_em` | str | `null` | Data/hora ISO 8601 para agendamento |
| `prioridade` | int | `5` | Prioridade da task no Celery/Redis. `0` = mais urgente, `9` = menos urgente |
| `fases` | array[str] | `null` | Lista opcional de fases a executar. Quando omitido, executa todas as fases do domínio |
| `anos_letivos` | array[int] | `null` | Lista opcional de anos letivos a processar, somente para domínios/fases que aceitam esse filtro |

Retorna `202` com `{"task_id": "<uuid>"}`.

Retorna `400` se `executar_em` for inválido.

---

### `GET monitoramento/execucoes/`

Endpoint público (sem autenticação). Suporta filtros via query string:

- `dominio` — nome do domínio ETL
- `data_inicio` — formato `YYYY-MM-DD`
- `data_fim` — formato `YYYY-MM-DD`
- `situacao` — ex: `concluido`, `erro`, `em_andamento`

Retorna até 100 execuções ordenadas por `iniciado_em` decrescente.

---

### `GET monitoramento/resumo/`

Endpoint público. Retorna a execução mais recente de cada domínio ETL.

---

### `GET sinc_rec/health/`

Endpoint público. Verifica se o banco `default` responde com `SELECT 1`.

Retorna `200` com `{"status": "healthy"}` ou `503` com `{"status": "unhealthy"}`.

---

## Script `recuperar_etl.sh`

O script `scripts/recuperar_etl.sh` pode rodar em cron separado do disparo
diário. Ele executa duas chamadas:

1. `POST /api/v1/execucoes/limpar-orfas/` com body `{}`.
2. `POST /api/v1/execucoes/reprocessar-erros/` com:

```json
{
  "max_tentativas": 3
}
```

O recovery sempre usa `continuar=true`, prioridade `3`, limite interno de 25
domínios por chamada e o volume original registrado na execução com erro.

O `curl` usa timeout de conexão de 10 segundos, timeout total de 60 segundos
e até 3 tentativas HTTP com intervalo de 5 segundos.

Exemplo de cron a cada 30 minutos:

```cron
*/30 * * * * cd /app && ./scripts/recuperar_etl.sh >> /var/log/etl_recovery.log 2>&1
```
