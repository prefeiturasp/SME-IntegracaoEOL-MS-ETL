"""Leitor-produtor de chunks do EOL para tarefas Celery."""

import logging
from typing import Any

from apps.eol_connection.libs.servico_eol import EOLService

from .base_etl_fase import BaseEtlFase
from .task_publisher import TaskPublisher

logger = logging.getLogger(__name__)


class BaseEtlChunk:
    """Lê chunks do EOL e cria grupo de assinaturas Celery."""

    def __init__(
        self,
        task_processamento: Any,
        eol: EOLService | None = None,
        publisher: TaskPublisher | None = None,
    ) -> None:
        self._eol = eol or EOLService()
        self._publisher = publisher or TaskPublisher(task_processamento)

    def criar_grupo(self, fase_meta: BaseEtlFase) -> list[Any]:
        """Lê todos os chunks da fase e retorna lista de assinaturas Celery.

        O throttling é responsabilidade do Celery via ``rate_limit``
        na task de processamento — não bloquear o processo Django.
        """
        tasks = []
        for chunk in self._eol.iter_query(fase_meta.sql):
            if chunk:
                tasks.append(self._publisher.criar_task(chunk, fase_meta))

        logger.info(
            "[%s] Fase %d/%d: %d tasks publicadas.",
            fase_meta.nome,
            fase_meta.numero_fase,
            fase_meta.total_fases,
            len(tasks),
        )
        return tasks
