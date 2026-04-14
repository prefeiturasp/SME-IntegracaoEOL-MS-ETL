# Orquestração Atual do Projeto

## Caminhos de execução disponíveis

### 1. CLI direto

```bash
python manage.py etl_professores [--volume 500] [--continuar]
```

Execução síncrona direta, sem passar pelo roteador de domínios.

---

### 2. Via roteador de domínios

```bash
python manage.py executar_dominio --dominio professores [--volume 500] [--continuar]
```

Rota padrão usada pela task Celery e pela API.

---

### 3. Via Celery (assíncrono)

```bash
# Imediato
python manage.py agendar_dominio --dominio professores --volume 500

# Agendado
python manage.py agendar_dominio --dominio professores --executar-em "2026-04-02T02:00:00-03:00"

# Via API REST
POST /api/v1/dominios/professores/executar/
```

A task `executar_dominio_task` executa em loop enquanto houver linhas alteradas
(delta de `token_parada >= volume`), com retry automático em falha (`continuar=True`).

---

### 4. Via loop contínuo (container)

```bash
python manage.py executar_dominios_loop --intervalo 300 --volume 200
```

Executa `executar_dominios` em loop. **Nota:** `executar_dominios` roda `sinc_rec_db` e `escola`.
O domínio `professores` deve ser orquestrado separadamente (via Celery ou cron).

---

### 5. Via watch_celery (worker com hot-reload)

```bash
python /scripts/watch_celery.py
```

Inicia o worker Celery com polling watcher (`watchdog.PollingObserver`).
Reinicia o worker automaticamente ao detectar alterações em `/app/apps` ou `/app/config`.
Substitui `watchmedo auto-restart` em ambientes sem inotify (Docker Desktop no macOS/Windows).

O worker escuta `apps.controle_auditoria.libs.celery_app:aplicacao_celery`.

---

## Fluxo de chamadas

```{graphviz}
digraph G {
    rankdir=LR;
    node [shape=box, style="rounded"];

    API  [label="POST /api/v1/\ndominios/professores/executar/"];
    AGE  [label="agendar_dominio"];
    TASK [label="executar_dominio_task\n(Celery)"];
    ROT  [label="executar_dominio\n--dominio professores"];
    CMD  [label="etl_professores"];
    SVC  [label="EtlProfessoresService"];
    REP  [label="RepositorioAuditoriaPostgres"];

    API  -> TASK;
    AGE  -> TASK;
    TASK -> ROT -> CMD -> SVC;
    CMD  -> REP;
}
```

---

## Infraestrutura Celery

| Componente | Arquivo |
|---|---|
| App Celery | `apps/controle_auditoria/libs/celery_app.py` |
| Tasks | `apps/controle_auditoria/libs/tasks.py` |
| Worker com hot-reload | `scripts/watch_celery.py` |

**Configuração:**
- Broker: KeyDB/Redis (`CELERY_BROKER_URL` em settings)
- Fila padrão: `fila_etl_padrao`
- Prioridade: 0–9 (0 = mais urgente)
- `max_retries=5`, `countdown=60s`
