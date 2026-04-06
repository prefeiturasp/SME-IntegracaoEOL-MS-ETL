"""Repositório para acesso ao banco CORE_SSO_DB."""

import logging
from typing import Any

from apps.core.libs.connection_readonly import ReadOnlySQLServerConnectionFactory

logger = logging.getLogger(__name__)

SQL_OBTER_CODIGO_UE_INTEGRACAO = """
SELECT DISTINCT
    uad_codigo [CodigoUe]
  , uad_nome [NomeUE]
  , uad_codigoIntegracao [CodigoIntegracao]
FROM SYS_UnidadeAdministrativa
WHERE uad_codigo IN @codigoUes;
"""


class RepositorioCoreSSO:
    """Repositório para realizar consultas no banco legado CORE_SSO."""

    def __init__(
        self, factory: ReadOnlySQLServerConnectionFactory | None = None
    ) -> None:
        """Inicializa validando se o banco existe no settings.DATABASES."""
        self.factory = factory or ReadOnlySQLServerConnectionFactory(
            db_alias="core_sso_db"
        )

    def obter_codigos_integracao_ues(
        self, codigo_ues: list[str]
    ) -> list[tuple[Any, ...]]:
        """Busca os códigos de integração para uma lista de códigos de UE."""
        if not codigo_ues:
            return []

        resultados: list[tuple[Any, ...]] = []
        lote_tamanho = 1000  # Limite seguro para SQL Server

        for i in range(0, len(codigo_ues), lote_tamanho):
            lote_atual = codigo_ues[i : i + lote_tamanho]
            placeholders = ", ".join(["%s"] * len(lote_atual))
            sql = SQL_OBTER_CODIGO_UE_INTEGRACAO.replace(
                "@codigoUes", f"({placeholders})"
            )

            # Realiza a consulta para o lote atual e acumula
            rows = self.factory.executar_consulta(sql, parametros=list(lote_atual))
            resultados.extend(rows)

        return resultados
