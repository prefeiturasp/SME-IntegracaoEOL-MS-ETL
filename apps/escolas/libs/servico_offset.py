"""Servico de consulta paginada de escolas."""

from apps.escolas.libs.cliente_legado import ClienteLegadoEscolas
from apps.escolas.models import ConsultaEscolasLog


class ServicoEscolasOffset:
    """Orquestra leitura paginada de escolas e log local."""

    TAMANHO_PAGINA_PADRAO = 100

    def __init__(self) -> None:
        self._cliente_legado = ClienteLegadoEscolas()

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
            lote = self._cliente_legado.listar_por_offset(
                limite=limite,
                offset=offset_atual,
            )
            if not lote:
                break

            ConsultaEscolasLog.objects.create(
                offset_inicial=offset_atual,
                limite=limite,
                total_retorno=len(lote),
            )
            registros.extend(lote)
            offset_atual += len(lote)
            restante -= len(lote)

            if len(lote) < limite:
                break

        return registros
