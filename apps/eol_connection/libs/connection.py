"""Conexoes e helpers para acessar o banco EOL em modo somente-leitura."""

import logging
import os
from collections.abc import Iterator
from typing import Any, cast

from django.conf import settings
from django.db import connections

from .exceptions import ConexaoSomenteLeituraError

logger = logging.getLogger(__name__)

_EOL_CHUNK_SIZE = int(os.getenv("EOL_CHUNK_SIZE", "300"))
# 0 = sem limite (produção). >0 = para após N lotes por query (testes).
_EOL_LOTE_MAXIMO = int(os.getenv("EOL_LOTE_MAXIMO", "0"))

WRITE_COMMANDS = {"insert", "update", "delete", "merge", "create", "drop"}


class EOLConnectionFactory:
    """Cria conexoes READ ONLY com o banco EOL usando o alias do Django."""

    def __init__(self, db_alias: str = "eol_db") -> None:
        """Inicializa validando se o banco existe no settings.DATABASES."""
        if db_alias not in settings.DATABASES or not settings.DATABASES[db_alias]:
            raise ValueError(
                f"Banco '{db_alias}' nao configurado em settings.DATABASES"
            )
        self.db_alias = db_alias

    def obter_conexao(self) -> Any:
        """Retorna uma conexao utilizando o alias configurado."""
        return connections[self.db_alias]

    def executar_consulta(
        self,
        sql: str,
        parametros: list | dict | None = None,
        chunk_size: int = _EOL_CHUNK_SIZE,
    ) -> list[tuple[Any, ...]]:
        """Executa uma consulta e retorna lista de tuplas com resultados.

        Usa fetchmany em vez de fetchall para evitar que a conexão TCP
        seja resetada pelo SQL Server durante transferências longas.
        """
        parametros = parametros or {}

        try:
            with self.obter_conexao().cursor() as cursor:
                if parametros:
                    cursor.execute(sql, parametros)
                else:
                    cursor.execute(sql)

                rows: list[tuple[Any, ...]] = []
                while True:
                    lote = cursor.fetchmany(chunk_size)
                    if not lote:
                        break
                    rows.extend(lote)
                    logger.info("EOL fetch: %d registros carregados", len(rows))
                return cast(list[tuple[Any, ...]], rows)

        except Exception:
            logger.exception("Erro ao executar consulta no EOL")
            raise

    def iter_consulta(
        self,
        sql: str,
        parametros: list | dict | None = None,
        chunk_size: int = _EOL_CHUNK_SIZE,
    ) -> Iterator[list[tuple[Any, ...]]]:
        """Executa consulta e faz yield de um chunk por vez.

        Permite que o chamador processe cada lote imediatamente, sem
        acumular todos os resultados em memória antes de começar o ETL.
        """
        parametros = parametros or {}
        total = 0

        try:
            with self.obter_conexao().cursor() as cursor:
                if parametros:
                    cursor.execute(sql, parametros)
                else:
                    cursor.execute(sql)

                iteracao = 0
                while True:
                    lote = cursor.fetchmany(chunk_size)
                    if not lote:
                        break
                    iteracao += 1
                    total += len(lote)
                    logger.info(
                        "EOL fetch: lote %d — %d registros acumulados",
                        iteracao,
                        total,
                    )
                    yield lote
                    if _EOL_LOTE_MAXIMO and iteracao >= _EOL_LOTE_MAXIMO:
                        logger.info(
                            "EOL iter: limite de %d lote(s) atingido"
                            " — interrompendo query",
                            _EOL_LOTE_MAXIMO,
                        )
                        break

        except Exception:
            logger.exception("Erro ao executar consulta no EOL")
            raise

    def executar_comando(self, sql: str) -> list[tuple[Any, ...]]:
        """Executa comando SQL de leitura (bloqueia escrita)."""
        comando = sql.lower()

        if any(c in comando for c in WRITE_COMMANDS):
            logger.error("Tentativa de escrita bloqueada no EOL")
            raise ConexaoSomenteLeituraError(
                "Operacao de escrita nao permitida no banco EOL"
            )

        return self.executar_consulta(sql)
