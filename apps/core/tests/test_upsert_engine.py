"""Testes de integração do motor de escrita de auditoria no Postgres."""


from django.db import connections
from django.test import TransactionTestCase
from psycopg import sql

from apps.core.libs.base_etl_service import PostgresUpsertEngine


class PostgresUpsertEngineTest(TransactionTestCase):
    """Testes do PostgresUpsertEngine."""

    def setUp(self) -> None:
        self.engine = PostgresUpsertEngine()
        self.table_name = "etl_auditoria_linha_teste"
        with connections["default"].cursor() as cursor:
            query = sql.SQL(
                "CREATE TABLE IF NOT EXISTS {} ("
                "id_destino text PRIMARY KEY, "
                "hash_controle text, "
                "atualizado_em timestamp)"
            ).format(sql.Identifier(self.table_name))
            cursor.execute(query)

    def tearDown(self) -> None:
        with connections["default"].cursor() as cursor:
            query = sql.SQL("DROP TABLE IF EXISTS {}").format(
                sql.Identifier(self.table_name)
            )
            cursor.execute(query)

    def test_upsert_bulk_vazio_nao_faz_nada(self) -> None:
        result = self.engine.upsert_bulk(self.table_name, [], "batch-1")
        self.assertEqual(result, 0)

    def test_upsert_bulk_sucesso(self) -> None:
        rows = [("1", "hash1"), ("2", "hash2")]
        result = self.engine.upsert_bulk(self.table_name, rows, "batch-2")
        self.assertEqual(result, 2)

        # Verifica persistência
        with connections["default"].cursor() as cursor:
            query = sql.SQL("SELECT COUNT(*) FROM {}").format(
                sql.Identifier(self.table_name)
            )
            cursor.execute(query)
            self.assertEqual(cursor.fetchone()[0], 2)

    def test_upsert_bulk_update_on_conflict(self) -> None:
        # Primeiro insert
        self.engine.upsert_bulk(self.table_name, [("1", "old")], "batch-3")

        # Update via conflict
        rows = [("1", "new"), ("2", "hash2")]
        result = self.engine.upsert_bulk(self.table_name, rows, "batch-4")

        # ON CONFLICT UPDATE: rowcount costuma ser 1 por linha afetada
        self.assertGreaterEqual(result, 1)

        with connections["default"].cursor() as cursor:
            query = sql.SQL(
                "SELECT hash_controle FROM {} WHERE id_destino = %s"
            ).format(sql.Identifier(self.table_name))
            cursor.execute(query, ("1",))
            self.assertEqual(cursor.fetchone()[0], "new")

