"""Testes de integração do motor de escrita de auditoria no Postgres."""

from unittest.mock import MagicMock, patch

from django.db import connections
from django.test import TransactionTestCase

from apps.core.libs.base_etl_service import PostgresUpsertEngine


class PostgresUpsertEngineTest(TransactionTestCase):
    """Testes do PostgresUpsertEngine."""

    def setUp(self) -> None:
        self.engine = PostgresUpsertEngine()
        self.table_name = "etl_auditoria_linha_teste"
        with connections["default"].cursor() as cursor:
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {self.table_name} ("
                "id_destino text PRIMARY KEY, "
                "hash_controle text, "
                "atualizado_em timestamp)"
            )

    def tearDown(self) -> None:
        with connections["default"].cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")

    def test_upsert_bulk_vazio_nao_faz_nada(self) -> None:
        result = self.engine._upsert_bulk_full(self.table_name, [], "batch-1")
        self.assertEqual(result, 0)

    def test_upsert_bulk_sucesso(self) -> None:
        rows = [("1", "hash1"), ("2", "hash2")]
        result = self.engine._upsert_bulk_full(self.table_name, rows, "batch-2")
        self.assertEqual(result, 2)

        # Verifica persistência
        with connections["default"].cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            self.assertEqual(cursor.fetchone()[0], 2)

    def test_upsert_bulk_update_on_conflict(self) -> None:
        # Primeiro insert
        self.engine._upsert_bulk_full(self.table_name, [("1", "old")], "batch-3")

        # Update via conflict
        rows = [("1", "new"), ("2", "hash2")]
        result = self.engine._upsert_bulk_full(self.table_name, rows, "batch-4")

        # No Postgres, o rowcount do ON CONFLICT UPDATE costuma ser 1 por linha afetada
        self.assertGreaterEqual(result, 1)

        with connections["default"].cursor() as cursor:
            cursor.execute(
                f"SELECT hash_controle FROM {self.table_name} WHERE id_destino = '1'"
            )
            self.assertEqual(cursor.fetchone()[0], "new")

    @patch("apps.core.libs.base_etl_service.connections")
    def test_upsert_bulk_fallback_copy_from(self, mock_connections: MagicMock) -> None:
        """Testa o fallback para copy_from caso raw_cursor não tenha .copy()."""
        mock_cursor = MagicMock()
        # Simula objeto cursor que NÃO possui o método .copy (estilo psycopg2 antigo)
        del mock_cursor.cursor.copy
        mock_connections.__getitem__.return_value.cursor.return_value.__enter__.return_value = (
            mock_cursor
        )

        rows = [("3", "hash3")]
        # Não falhando já é um sucesso do teste de cobertura do branch 'else'
        self.engine._upsert_bulk_full(self.table_name, rows, "batch-5")
        self.assertTrue(mock_cursor.cursor.copy_from.called)
