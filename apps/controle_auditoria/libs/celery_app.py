"""Configuracao do Celery com broker KeyDB/Redis."""

from celery import Celery
from django.conf import settings

aplicacao_celery = Celery("sme_sgp_ms_etl", broker=settings.URL_KEYDB)
aplicacao_celery.conf.update(
    task_default_queue="fila_etl_padrao",
    imports=("apps.controle_auditoria.libs.tasks",),
)
