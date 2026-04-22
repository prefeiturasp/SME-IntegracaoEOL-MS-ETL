"""Configuracao do Celery com broker KeyDB/Redis."""

import os

from celery import Celery


def create_celery_app() -> Celery:
    """Cria e configura a instância do Celery."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    app = Celery("sme_sgp_ms_etl")

    app.config_from_object("django.conf:settings", namespace="CELERY")

    app.conf.update(
        task_default_queue="fila_etl_padrao",
        imports=(
            "apps.controle_auditoria.libs.tasks",
            "apps.core.tasks",
        ),
        broker_connection_retry=True,
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=10,
        task_queue_max_priority=9,
        task_default_priority=5,
        broker_transport_options={"priority_steps": list(range(10))},
    )

    return app


aplicacao_celery: Celery = create_celery_app()
