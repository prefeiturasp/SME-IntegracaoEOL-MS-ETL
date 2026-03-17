"""Conexoes e helpers para acessar o banco EOL em modo somente-leitura."""

import logging
import os
from typing import Any, cast
from urllib.parse import parse_qs, unquote_plus, urlparse

from .exceptions import ConexaoSomenteLeituraError

logger = logging.getLogger(__name__)

WRITE_COMMANDS = {"insert", "update", "delete", "merge", "create", "drop"}


class EOLConnectionFactory:
    """Cria conexoes READ ONLY com o banco EOL."""

    def __init__(self, dsn: str | None = None, driver: Any = None):
        """Inicializa DSN opcional e driver (para testes)."""
        self.dsn = dsn or os.getenv("EOL_DB")

        if not self.dsn:
            raise ValueError("Variavel de ambiente EOL_DB nao configurada")

        if "ReadOnly=True" not in self.dsn:
            raise ValueError("A conexao EOL_DB deve conter ReadOnly=True")

        if driver is None:
            import pyodbc

            driver = pyodbc

        self.driver: Any = driver
        self.conn_str = self._build_connection_string(self.dsn)

    def _build_connection_string(self, dsn: str) -> str:
        """Constroi connection string para pyodbc a partir do DSN."""
        if not dsn.startswith("mssql+pyodbc://"):
            return dsn

        parsed = urlparse(dsn)

        username = unquote_plus(parsed.username or "")
        password = unquote_plus(parsed.password or "")
        host = parsed.hostname or ""
        database = parsed.path.lstrip("/")

        query = parse_qs(parsed.query)
        driver = query.get("driver", [""])[0].replace("+", " ")

        parts = []

        if driver:
            parts.append(f"DRIVER={{{driver}}}")

        if host:
            parts.append(f"SERVER={host}")

        if database:
            parts.append(f"DATABASE={database}")

        if username:
            parts.append(f"UID={username}")

        if password:
            parts.append(f"PWD={password}")

        return ";".join(parts)

    def obter_conexao(self) -> Any:
        """Retorna uma conexao utilizando o driver configurado."""
        return self.driver.connect(self.conn_str)

    def executar_consulta(
        self, sql: str, parametros: dict | None = None
    ) -> list[tuple[Any, ...]]:
        """Executa uma consulta e retorna lista de tuplas com resultados."""
        parametros = parametros or {}

        try:
            with self.obter_conexao() as conn:
                cursor = conn.cursor()

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
