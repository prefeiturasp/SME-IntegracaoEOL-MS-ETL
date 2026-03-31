# API de Auditoria

O app `controle_auditoria` expõe endpoints DRF para monitoramento, auditoria e execução de domínios ETL.

## Rotas

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

## Detalhes por endpoint

### `GET checkpoints/`

Retorna todos os `EtlCheckpointDominio` ordenados por domínio.

Campos retornados: `dominio`, `ultimo_id_execucao`, `ultima_pagina`, `token_parada`, `ultima_situacao`, `ultimo_sucesso_em`, `atualizado_em`.

---

### `GET execucoes/`

Retorna as 50 execuções ETL mais recentes, ordenadas por `iniciado_em` decrescente.

---

### `GET execucoes/<id_execucao>/`

Retorna uma execução identificada pelo UUID `id_execucao`, com as listas de `tabelas_lidas` e `tabelas_escritas` aninhadas.

Retorna `404` se o UUID não existir.

---

### `GET execucoes/tabelas-lidas/` e `GET execucoes/tabelas-escritas/`

Retornam os 50 registros mais recentes de `EtlExecucaoTabelaLida` e `EtlExecucaoTabelaEscrita`, respectivamente.

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
| `prioridade` | int | `5` | Prioridade Celery (0 = mais urgente) |

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

Endpoint público. Retorna a execução mais recente de cada domínio ETL, útil para visualizar rapidamente o estado atual de cada pipeline.

---

### `GET sinc_rec/health/`

Endpoint público. Verifica se a variável `URL_BANCO_AUDITORIA` está configurada e se o banco `default` responde com `SELECT 1`.

Retorna `200` com `{"status": "healthy"}` ou `503` com `{"status": "unhealthy"}`.
