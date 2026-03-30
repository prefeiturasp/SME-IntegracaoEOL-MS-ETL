"""Configuracao do Celery com broker KeyDB/Redis."""

from celery import Celery
from django.conf import settings

aplicacao_celery = Celery("sme_sgp_ms_etl", broker=settings.URL_KEYDB)
aplicacao_celery.conf.update(
    task_default_queue="fila_etl_padrao",
    imports=("apps.controle_auditoria.libs.tasks",),
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    # Suporte a prioridade: domínios são processados sequencialmente pelo worker
    # (--concurrency=1). Prioridade 0 = mais urgente, 9 = menos urgente.
    task_queue_max_priority=9,
    task_default_priority=5,
    broker_transport_options={"priority_steps": list(range(10))},
)
