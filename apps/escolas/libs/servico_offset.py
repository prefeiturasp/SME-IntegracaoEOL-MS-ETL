"""Servico de consulta paginada de escolas."""

from apps.escolas.libs.cliente_legado import ClienteLegadoEscolas
from apps.escolas.models import ConsultaEscolasLog


class ServicoEscolasOffset:
    """Orquestra leitura paginada de escolas e log local."""

    TAMANHO_PAGINA_PADRAO = 100

    def __init__(self) -> None:
        """Inicia o servico de consulta de escolas."""
        self._cliente_legado = ClienteLegadoEscolas()

    def listar_pagina(
        self,
        limite: int,
        offset: int,
    ) -> list[dict[str, object]]:
        """Lê uma página única e registra log local da consulta."""
        lote = self._cliente_legado.listar_por_offset(
            limite=limite,
            offset=offset,
        )
        if lote:
            ConsultaEscolasLog.objects.create(
                offset_inicial=offset,
                limite=limite,
                total_retorno=len(lote),
            )
        return lote

    def listar_volume(
        self,
        volume: int,
        offset_inicial: int,
    ) -> list[dict[str, object]]:
        """Retorna volume de escolas em blocos de 100."""
        registros: list[dict[str, object]] = []
        offset_atual = offset_inicial
        restante = volume

        while restante > 0:
            limite = min(self.TAMANHO_PAGINA_PADRAO, restante)
            lote = self.listar_pagina(
                limite=limite,
                offset=offset_atual,
            )
            if not lote:
                break
            registros.extend(lote)
            offset_atual += len(lote)
            restante -= len(lote)

            if len(lote) < limite:
                break

        return registros
