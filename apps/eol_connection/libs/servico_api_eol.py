"""Serviço de leitura do banco Postgres da API EOL."""

from collections.abc import Iterator
from typing import Any

from django.conf import settings
from django.db import connections


class ApiEOLService:
    """Serviço de acesso ao banco Postgres da API EOL."""

    def __init__(self, db_alias: str = "api_eol_db") -> None:
        """Inicializa o serviço com o alias de conexão da API EOL."""
        self.db_alias = db_alias

    def iter_query(self, sql: str) -> Iterator[list[tuple[Any, ...]]]:
        """Faz yield de um chunk por vez para processamento incremental."""
        chunk_size = getattr(settings, "EOL_CHUNK_SIZE", 50_000)
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql)
            while True:
                rows = cursor.fetchmany(chunk_size)
                if not rows:
                    break
                yield list(rows)
