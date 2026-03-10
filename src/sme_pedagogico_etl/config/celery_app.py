"""Configuração da instância Celery com KeyDB como broker e backend."""

from __future__ import annotations

from celery import Celery

from sme_pedagogico_etl.config.settings import settings

celery_app = Celery("sme_pedagogico_etl")

celery_app.conf.update(
    # Broker e backend — KeyDB
    broker_url=settings.keydb_broker_url,
    result_backend=settings.keydb_result_backend,

    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    timezone="America/Sao_Paulo",
    enable_utc=True,

    # Confiabilidade: tarefa só é removida da fila após confirmação de execução
    task_acks_late=True,
    # Evita que workers acumulem tarefas antes de processá-las
    worker_prefetch_multiplier=1,

    # Rastreabilidade: registra o estado STARTED além de SUCCESS/FAILURE
    task_track_started=True,

    # TODO criar/definir pasta de tasks final
    # Módulos onde as tasks estão definidas
    include=["sme_pedagogico_etl.worker.tasks"],
)
