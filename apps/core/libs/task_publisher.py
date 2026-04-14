"""Publicador de tasks Celery para chunks do pipeline ETL."""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from .base_etl_fase import BaseEtlFase


class EtlJsonEncoder(json.JSONEncoder):
    """Encoder JSON para tipos Python comuns em dados do SQL Server."""

    def default(self, obj: Any) -> Any:
        """Converte tipos não-serializáveis para representação JSON-safe."""
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


def serializar_chunk(chunk: list[tuple]) -> list[list]:
    """Converte chunk de tuplas para lista de listas JSON-serializável.

    Converte objetos date/datetime para ISO string de forma eficiente,
    evitando o overhead de dump/load via JSON que consome muita RAM.
    """
    from datetime import date, datetime
    from decimal import Decimal

    return [
        [
            (val.isoformat() if isinstance(val, (date, datetime))
             else str(val) if isinstance(val, Decimal)
             else val)
            for val in row
        ]
        for row in chunk
    ]


class TaskPublisher:
    """Cria assinaturas de tasks Celery para chunks do EOL.

    Parametrizável para aceitar diferentes tasks de processamento.
    """

    def __init__(self, processar_task: Any) -> None:
        """Inicializa com a assinatura da task de processamento."""
        self._processar_task = processar_task

    def criar_task(
        self,
        chunk: list[tuple],
        fase_meta: BaseEtlFase,
    ) -> Any:
        """Retorna assinatura Celery para processar o chunk no worker."""
        chunk_serializavel = serializar_chunk(chunk)
        task = self._processar_task.s(
            chunk_serializavel, fase_meta.to_dict()
        )
        del chunk_serializavel
        return task
