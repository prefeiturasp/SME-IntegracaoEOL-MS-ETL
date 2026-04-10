"""Fábrica de conexões especializadas para o banco legado EOL."""

import logging
import os
from typing import Any

from apps.core.libs.connection_readonly import ReadOnlySQLServerConnectionFactory

logger = logging.getLogger(__name__)

_EOL_CHUNK_SIZE = int(os.getenv("EOL_CHUNK_SIZE", "10000"))
# 0 = sem limite (produção). >0 = para após N lotes por query (testes).
_EOL_LOTE_MAXIMO = int(os.getenv("EOL_LOTE_MAXIMO", "0"))


class EOLConnectionFactory(ReadOnlySQLServerConnectionFactory):
    """Cria conexoes READ ONLY com o banco EOL usando o alias do Django."""

    def __init__(self, db_alias: str = "eol_db") -> None:
        """Inicializa validando se o banco existe no settings.DATABASES."""
        super().__init__(
            db_alias=db_alias,
            chunk_size=_EOL_CHUNK_SIZE,
            lote_maximo=_EOL_LOTE_MAXIMO,
        )

    def executar_consulta(
        self,
        sql: str,
        parametros: list | dict | None = None,
        chunk_size: int | None = None,
    ) -> list[tuple[Any, ...]]:
        """Mantém compatibilidade com assinatura do EOLConnectionFactory anterior."""
        chunk_size = chunk_size or _EOL_CHUNK_SIZE
        return super().executar_consulta(sql, parametros, chunk_size)
