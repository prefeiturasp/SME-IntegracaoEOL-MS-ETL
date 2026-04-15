"""Orquestrador assíncrono para o domínio INSTITUCIONAL_DB."""

from typing import Any

from apps.core.libs.base_etl_orquestrador import GenericEtlOrquestrador
from apps.core.tasks import finalizar_fase, processar_chunk
from apps.institucional.services import EtlInstitucionalService

processar_chunk_institucional = processar_chunk
finalizar_fase_institucional = finalizar_fase


class EtlInstitucionalOrquestrador(GenericEtlOrquestrador):
    """Orquestrador assíncrono para Institucional utilizando Core genérico."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("dominio", "institucional")
        kwargs.setdefault("service_class", EtlInstitucionalService)
        super().__init__(**kwargs)
