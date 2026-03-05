from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

from sme_pedagogico_etl.config.settings import settings

logger = logging.getLogger(__name__)


class OperacaoEscritaNaoPermitida(Exception):
    """Exceção lançada quando uma operação de escrita é detectada."""


def _string_contem_application_intent_readonly(valor: str) -> bool:
    """
    Verifica se a string de conexão contém o indicador de somente leitura.
    Agora exige `ReadOnly=True` (case-insensitive e tolera espaços).
    """
    if not valor or not isinstance(valor, str):
        return False

    # Aceita somente o novo indicador: ReadOnly=True
    return bool(re.search(r"ReadOnly\s*=\s*True", valor, flags=re.I))


def validar_consulta_somente_leitura(sql: str) -> None:
    if not sql or not isinstance(sql, str):
        return

    sem_comentarios = re.sub(r"--.*?$", "", sql, flags=re.M).strip()
    if not sem_comentarios:
        return

    partes = [p.strip() for p in sem_comentarios.split(";") if p.strip()]
    for parte in partes:
        texto = parte.lstrip()
        texto = re.sub(r"^\(+\s*", "", texto).strip()
        if not texto.strip():
            continue

        m = re.match(r"^\s*([A-Za-z]+)", texto, flags=re.I)
        verbo = m.group(1).lower() if m else ""

        proibidos = {
            "insert",
            "update",
            "delete",
            "create",
            "alter",
            "drop",
            "truncate",
            "merge",
            "exec",
            "execute",
            "grant",
            "revoke",
        }

        if verbo in proibidos:
            raise OperacaoEscritaNaoPermitida(
                f"Operação não permitida: '{verbo}' detectado na consulta"
            )

        # SELECT INTO também escreve (SQL Server)
        if verbo == "select" and re.search(r"\binto\b", texto, flags=re.I):
            raise OperacaoEscritaNaoPermitida(
                "Operação não permitida: 'select into' detectado na consulta"
            )


class ConexaoEOL:
    """
    Gerencia conexão com o banco legado EOL/SE1426 em modo somente leitura.

    Regras:
    - Lê a string via settings.EOL_DB (carregada do .env)
    - Exige ReadOnly=True
    - Bloqueia escrita via validação + listener SQLAlchemy
    - Suporta string estilo ODBC
    """

    def __init__(self) -> None:
        valor = settings.EOL_DB

        if not valor:
            raise ValueError("Variável de ambiente 'EOL_DB' não definida")

        if not _string_contem_application_intent_readonly(valor):
            raise ValueError(
                "A string de conexão deve conter 'ReadOnly=True' indicando réplica somente leitura"
            )

        engine_url = valor

        # Detecta formato ODBC (chave=valor;chave=valor;)
        if re.search(r"\w+\s*=\s*[^;]+;", valor) or ("SERVER=" in valor.upper() and ";" in valor):
            odbc = quote_plus(valor)
            engine_url = f"mssql+pyodbc:///?odbc_connect={odbc}"

        self._engine: Engine = create_engine(
            engine_url,
            future=True,
            pool_pre_ping=True,
        )

        event.listen(self._engine, "before_cursor_execute", self._before_cursor_execute)

    def _before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        """Intercepta consultas antes da execução para impedir escrita."""
        try:
            validar_consulta_somente_leitura(statement)
        except OperacaoEscritaNaoPermitida:
            logger.error("Tentativa de escrita bloqueada no EOL: %s", statement)
            raise

    def executar(self, sql: str, params: Optional[Dict[str, Any]] = None) -> list:
        """Executa uma consulta SQL somente leitura."""
        validar_consulta_somente_leitura(sql)

        with self._engine.connect() as conn:
            resultado = conn.execute(text(sql), params or {})
            try:
                return resultado.fetchall()
            except Exception:
                return []

    def healthcheck(self, sql: str = "SELECT 1") -> bool:
        """Verifica conectividade com o banco."""
        try:
            validar_consulta_somente_leitura(sql)
            with self._engine.connect() as conn:
                conn.execute(text(sql))
            return True
        except Exception:
            logger.exception("Healthcheck falhou para EOL")
            raise


def healthcheck_eol() -> bool:
    """Wrapper utilitário que executa o healthcheck do banco EOL."""
    conexao = ConexaoEOL()
    return conexao.healthcheck()