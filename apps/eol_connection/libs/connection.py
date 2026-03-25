"""Conexoes e helpers para acessar o banco EOL em modo somente-leitura."""

import logging
from typing import Any, cast

from django.conf import settings
from django.db import connections

from .exceptions import ConexaoSomenteLeituraError

logger = logging.getLogger(__name__)

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
        self, sql: str, parametros: dict | None = None
    ) -> list[tuple[Any, ...]]:
        """Executa uma consulta e retorna lista de tuplas com resultados."""
        parametros = parametros or {}

        try:
            with self.obter_conexao().cursor() as cursor:
                if parametros:
                    cursor.execute(sql, parametros)
                else:
                    cursor.execute(sql)

                return cast(list[tuple[Any, ...]], cursor.fetchall())

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
