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
- Até 100 execuções filtradas.
- Últimas 10 execuções com detalhes de tabelas escritas.

### `KanbanView`

Suporta filtro: `dominio`.

Exibe por domínio:
- Coluna **Leitura EOL** — tabelas lidas e contagem.
- Coluna **Hash Control** — contagem de `EtlAuditoriaLinha` por tabela.
- Coluna **Escrita (Upsert)** — tabelas escritas e modo.
- Coluna **Checkpoint** — token acumulado, fase, último sucesso.

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

Retorna `404` se o UUID não existir.

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
| `volume` | int | `100` | Tamanho da página de leitura |
| `offset` | int | `0` | Offset inicial |
| `continuar` | bool | `false` | Retomar da fase do último checkpoint |
| `executar_em` | str | `null` | Data/hora ISO 8601 para agendamento |
| `prioridade` | int | `5` | Prioridade Celery (0 = mais urgente, 9 = menos urgente) |

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
