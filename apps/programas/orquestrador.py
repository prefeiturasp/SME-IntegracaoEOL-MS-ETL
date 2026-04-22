"""Orquestrador assíncrono para o domínio PROGRAMAS_DB."""

from typing import Any

from apps.core.libs.base_etl_orquestrador import GenericEtlOrquestrador
from apps.core.tasks import finalizar_fase, processar_chunk
from apps.programas.services import EtlProgramasService

processar_chunk_programas = processar_chunk
finalizar_fase_programas = finalizar_fase


class EtlProgramasOrquestrador(GenericEtlOrquestrador):
    """Orquestrador assíncrono para Programas utilizando Core genérico."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("dominio", "programas")
        kwargs.setdefault("service_class", EtlProgramasService)
        super().__init__(**kwargs)
