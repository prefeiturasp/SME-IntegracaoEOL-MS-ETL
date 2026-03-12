"""Servico de alto nivel para operacoes de leitura no EOL."""

from typing import Any

from .connection import EOLConnectionFactory


class EOLService:
    """Servico de acesso ao banco EOL."""

    def __init__(self, connection: EOLConnectionFactory | None = None) -> None:
        """Inicializa o servico com uma conexao (ou fabrica padrao)."""
        self.connection = connection or EOLConnectionFactory()

    def executar_query(
        self, sql: str, parametros: dict | None = None
    ) -> list[tuple[Any, ...]]:
        """Executa uma query de leitura e retorna os resultados."""
        return self.connection.executar_consulta(sql, parametros)

    def validar_conectividade(self) -> bool:
        """Valida se o EOL responde a uma consulta simples."""
        resultado = self.connection.executar_consulta("SELECT 1")
        return bool(resultado)
