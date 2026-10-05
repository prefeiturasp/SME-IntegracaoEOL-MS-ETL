"""Base para conexões somente-leitura com bancos SQL Server legados."""

import logging
import os
import time
from collections.abc import Iterator
from typing import Any, cast

from django.conf import settings
from django.db import connections

logger = logging.getLogger(__name__)

# Configurações padrão (podem ser sobrescritas por variáveis de ambiente específicas)
_DEFAULT_CHUNK_SIZE = int(os.getenv("EOL_CHUNK_SIZE", "10000"))
_DEFAULT_LOTE_MAXIMO = int(os.getenv("EOL_LOTE_MAXIMO", "0"))
_MAX_RETRY_CONEXAO = int(os.getenv("EOL_MAX_RETRY_CONEXAO", "3"))
_BACKOFF_MAX_SEGUNDOS = int(os.getenv("EOL_BACKOFF_MAX_SEGUNDOS", "30"))

# Marcas de erro de conexão TCP recuperável com reconexão (ex: 10054).
_MARCAS_ERRO_CONEXAO = (
    "08s01",
    "10054",
    "communication link",
    "connection reset",
    "tcp provider",
    "server closed the connection",
)

WRITE_COMMANDS = {"insert", "update", "delete", "merge", "create", "drop"}


def _eh_erro_conexao(exc: Exception) -> bool:
    """Indica se a exceção representa queda de conexão recuperável."""
    mensagem = str(exc).lower()
    return any(marca in mensagem for marca in _MARCAS_ERRO_CONEXAO)


def _eh_tabela_inexistente(exc: Exception) -> bool:
    """Indica se a exceção é de tabela/objeto inexistente na origem."""
    mensagem = str(exc).lower()
    return "no such table" in mensagem or "invalid object name" in mensagem


class ConexaoSomenteLeituraError(Exception):
    """Erro disparado quando alguma operacao de escrita em banco de dados legado."""

    pass


class ReadOnlySQLServerConnectionFactory:
    """Base para criar conexões READ ONLY com bancos legados SQL Server."""

    def __init__(
        self,
        db_alias: str,
        chunk_size: int | None = None,
        lote_maximo: int | None = None,
    ) -> None:
        """Inicializa validando se o banco existe no settings.DATABASES."""
        if db_alias not in settings.DATABASES or not settings.DATABASES[db_alias]:
            raise ValueError(
                f"Banco '{db_alias}' nao configurado em settings.DATABASES"
            )
        self.db_alias = db_alias
        self.chunk_size = chunk_size or _DEFAULT_CHUNK_SIZE
        self.lote_maximo = lote_maximo or _DEFAULT_LOTE_MAXIMO

    def obter_conexao(self) -> Any:
        """Retorna uma conexao utilizando o alias configurado."""
        return connections[self.db_alias]

    def executar_consulta(
        self,
        sql: str,
        parametros: list | dict | None = None,
        chunk_size: int | None = None,
    ) -> list[tuple[Any, ...]]:
        """Executa uma consulta e retorna lista de tuplas com resultados.

        Usa fetchmany em vez de fetchall para evitar que a conexão TCP
        seja resetada pelo SQL Server durante transferências longas.
        """
        parametros = parametros or {}
        chunk_size = chunk_size or self.chunk_size

        try:
            with self.obter_conexao().cursor() as cursor:
                if parametros:
                    params_tuple = (
                        tuple(parametros)
                        if isinstance(parametros, list)
                        else parametros
                    )
                    cursor.execute(sql, params_tuple)
                else:
                    cursor.execute(sql)

                rows: list[tuple[Any, ...]] = []
                while True:
                    lote = cursor.fetchmany(chunk_size)
                    if not lote:
                        break
                    rows.extend(lote)
                    logger.info(
                        "[%s] fetch: %d registros carregados", self.db_alias, len(rows)
                    )
                return cast(list[tuple[Any, ...]], rows)

        except Exception as exc:
            erro_str = str(exc).lower()
            if "no such table" in erro_str or "invalid object name" in erro_str:
                logger.warning("[%s] Tabela não encontrada na origem: %s", self.db_alias, exc)
            else:
                logger.exception("[%s] Erro ao executar consulta", self.db_alias)
            raise

    def iter_consulta(
        self,
        sql: str,
        parametros: list | dict | None = None,
        chunk_size: int | None = None,
    ) -> Iterator[list[tuple[Any, ...]]]:
        """Executa consulta e faz yield de um chunk por vez.

        Permite que o chamador processe cada lote imediatamente, sem
        acumular todos os resultados em memória antes de começar o ETL.

        Quedas transitórias de conexão (ex: TCP 10054) disparam reconexão
        com backoff e a consulta é refeita do início; como a escrita no
        destino é idempotente (upsert), não há duplicação de dados.
        """
        parametros = parametros or {}
        chunk_size = chunk_size or self.chunk_size

        tentativa = 0
        while True:
            try:
                yield from self._gerar_lotes(sql, parametros, chunk_size)
                return
            except Exception as exc:
                if _eh_tabela_inexistente(exc):
                    logger.warning(
                        "[%s] Tabela não encontrada na consulta iterativa:"
                        " %s",
                        self.db_alias,
                        exc,
                    )
                    raise
                excedeu_tentativas = tentativa >= _MAX_RETRY_CONEXAO
                if not _eh_erro_conexao(exc) or excedeu_tentativas:
                    logger.exception(
                        "[%s] Erro ao executar consulta iterativa",
                        self.db_alias,
                    )
                    raise
                tentativa += 1
                espera = min(2**tentativa, _BACKOFF_MAX_SEGUNDOS)
                logger.warning(
                    "[%s] Conexão EOL perdida (%s). Tentativa %d/%d —"
                    " reconectando em %ds e refazendo a consulta.",
                    self.db_alias,
                    exc,
                    tentativa,
                    _MAX_RETRY_CONEXAO,
                    espera,
                )
                connections[self.db_alias].close()
                time.sleep(espera)

    def _gerar_lotes(
        self,
        sql: str,
        parametros: list | dict,
        chunk_size: int,
    ) -> Iterator[list[tuple[Any, ...]]]:
        """Executa a consulta e faz yield dos lotes via fetchmany."""
        with self.obter_conexao().cursor() as cursor:
            if parametros:
                cursor.execute(sql, parametros)
            else:
                cursor.execute(sql)

            iteracao = 0
            total = 0
            while True:
                lote = cursor.fetchmany(chunk_size)
                if not lote:
                    break
                iteracao += 1
                total += len(lote)
                logger.info(
                    "[%s] fetch: lote %d — %d registros acumulados",
                    self.db_alias,
                    iteracao,
                    total,
                )
                yield lote
                if self.lote_maximo and iteracao >= self.lote_maximo:
                    logger.info(
                        "[%s] iter: limite de %d lote(s) atingido"
                        " — interrompendo query",
                        self.db_alias,
                        self.lote_maximo,
                    )
                    break

    def executar_comando(self, sql: str) -> list[tuple[Any, ...]]:
        """Executa comando SQL de leitura (bloqueia escrita)."""
        comando = sql.lower()

        if any(c in comando for c in WRITE_COMMANDS):
            logger.error("[%s] Tentativa de escrita bloqueada", self.db_alias)
            raise ConexaoSomenteLeituraError(
                f"Operacao de escrita nao permitida no banco {self.db_alias}"
            )

        return self.executar_consulta(sql)
