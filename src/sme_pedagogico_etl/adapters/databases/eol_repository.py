from __future__ import annotations

from typing import Any, Dict, Optional

from sme_pedagogico_etl.adapters.databases.conexao_eol import ConexaoEOL


class EOLRepository:
    """Repository de leitura do legado EOL."""

    def __init__(self, conexao: Optional[ConexaoEOL] = None) -> None:
        self._conexao = conexao or ConexaoEOL()

    def executar_consulta(self, sql: str, params: Optional[Dict[str, Any]] = None) -> list:
        return self._conexao.executar(sql, params=params)