"""Orquestrador assíncrono para o domínio PEDAGOGICO_DB."""

from typing import Any

from apps.core.libs.base_etl_orquestrador import GenericEtlOrquestrador
from apps.core.tasks import finalizar_fase, processar_chunk
from apps.pedagogico.services import EtlPedagogicoService

processar_chunk_pedagogico = processar_chunk
finalizar_fase_pedagogico = finalizar_fase


class EtlPedagogicoOrquestrador(GenericEtlOrquestrador):
    """Orquestrador assíncrono para Pedagógico utilizando Core genérico."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("dominio", "pedagogico")
        kwargs.setdefault("service_class", EtlPedagogicoService)
        super().__init__(**kwargs)
