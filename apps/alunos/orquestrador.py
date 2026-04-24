"""Orquestrador do domínio Alunos."""

from typing import Any

from apps.alunos.services import EtlAlunosService
from apps.core.libs.base_etl_orquestrador import GenericEtlOrquestrador
from apps.core.tasks import finalizar_fase, processar_chunk

processar_chunk_alunos = processar_chunk
finalizar_fase_alunos = finalizar_fase


class EtlAlunosOrquestrador(GenericEtlOrquestrador):
    """Orquestrador assíncrono para Alunos utilizando Core genérico."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("dominio", "alunos")
        kwargs.setdefault("service_class", EtlAlunosService)
        super().__init__(**kwargs)
