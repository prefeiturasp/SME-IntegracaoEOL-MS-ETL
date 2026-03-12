"""Testes unitarios das bibliotecas de eol_connection."""

import os
from collections.abc import Sequence
from typing import Any
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.eol_connection.libs.connection import EOLConnectionFactory
from apps.eol_connection.libs.exceptions import ConexaoSomenteLeituraError
from apps.eol_connection.libs.healthcheck import healthcheck_eol
from apps.eol_connection.libs.servico_eol import EOLService


class FakeDriver:
    """Driver fake para simular conexoes em testes."""

    def __init__(self, rows: Sequence[tuple[Any, ...]] | None = None) -> None:
        """Inicializa o driver fake com rows que serao retornadas."""
        self.rows = rows or [(1,)]

    def connect(self, conn_str: str) -> Any:
        """Simula `connect`, retornando um contexto com `cursor()`."""
        rows = self.rows

        class Conn:
            def __enter__(self) -> "Conn":
                return self

            def __exit__(self, *args: Any) -> None:
                pass

            def cursor(self) -> Any:

                class Cursor:
                    def execute(self, *args: Any, **kwargs: Any) -> None:
                        pass

                    def fetchall(self) -> list[tuple[Any, ...]]:
                        return list(rows)

                return Cursor()

        return Conn()


class TestConnectionFactory(TestCase):
    """Testes para `EOLConnectionFactory`."""

    def setUp(self) -> None:
        """Configura variavel de ambiente EOL_DB usada pelos testes."""
        os.environ["EOL_DB"] = (
            "mssql+pyodbc://user:pass@localhost/db?"
            "driver=ODBC+Driver+17+for+SQL+Server&ReadOnly=True"
        )

    def test_executar_consulta_exception(self) -> None:
        """Ao ocorrer erro no driver, a exception e propagada."""
        import os

        os.environ["EOL_DB"] = (
            "mssql+pyodbc://user:pass@localhost/db?"
            "driver=ODBC+Driver+17+for+SQL+Server&ReadOnly=True"
        )

        class DriverErro:
            def connect(self, conn_str: str) -> Any:

                class Conn:
                    def __enter__(self) -> "Conn":
                        return self

                    def __exit__(self, *args: Any) -> None:
                        pass

                    def cursor(self) -> Any:
                        raise RuntimeError("erro banco")

                return Conn()

        from apps.eol_connection.libs.connection import EOLConnectionFactory

        factory = EOLConnectionFactory(driver=DriverErro())

        with self.assertRaises(RuntimeError):
            factory.executar_consulta("SELECT 1")

    def test_build_connection_string_odbc(self) -> None:
        """Builda corretamente connection string quando ODBC ja fornecido."""
        os.environ["EOL_DB"] = "Driver=ODBC Driver 17;ReadOnly=True"

        factory = EOLConnectionFactory(driver=FakeDriver())

        self.assertEqual(factory.conn_str, "Driver=ODBC Driver 17;ReadOnly=True")

    def test_pyodbc_import_error(self) -> None:
        """Erro e levantado quando modulo pyodbc nao esta disponivel."""
        os.environ["EOL_DB"] = (
            "mssql+pyodbc://user:pass@localhost/db?"
            "driver=ODBC+Driver+17+for+SQL+Server&ReadOnly=True"
        )

        with patch.dict("sys.modules", {"pyodbc": None}):

            from apps.eol_connection.libs.connection import EOLConnectionFactory

            with self.assertRaises(ModuleNotFoundError):
                EOLConnectionFactory()

    def test_import_pyodbc_quando_driver_none(self) -> None:
        """Quando driver fake presente, obter_conexao deve propagar erro."""
        os.environ["EOL_DB"] = (
            "mssql+pyodbc://user:pass@localhost/db?"
            "driver=ODBC+Driver+17+for+SQL+Server&ReadOnly=True"
        )

        class FakePyodbc:
            def connect(self, conn_str: str) -> Any:
                raise RuntimeError("nao deveria conectar")

        import sys
        from typing import cast as _cast

        sys.modules["pyodbc"] = _cast(Any, FakePyodbc())

        from apps.eol_connection.libs.connection import EOLConnectionFactory

        factory = EOLConnectionFactory()

        with self.assertRaises(RuntimeError):
            factory.obter_conexao()

    def test_build_connection_string(self) -> None:
        """Constroi connection string a partir do DSN mssql+pyodbc."""
        factory = EOLConnectionFactory(driver=FakeDriver())

        self.assertIn("SERVER=localhost", factory.conn_str)
        self.assertIn("DATABASE=db", factory.conn_str)

    def test_env_nao_configurada(self) -> None:
        """Erro quando EOL_DB nao esta configurada."""
        os.environ.pop("EOL_DB", None)

        with self.assertRaises(ValueError):
            EOLConnectionFactory(driver=FakeDriver())

    def test_sem_readonly(self) -> None:
        """Erro quando DSN nao contem ReadOnly=True."""
        os.environ["EOL_DB"] = "Driver=ODBC"

        with self.assertRaises(ValueError):
            EOLConnectionFactory(driver=FakeDriver())

    def test_executar_consulta(self) -> None:
        """Executa consulta e retorna resultados."""
        factory = EOLConnectionFactory(driver=FakeDriver(rows=[("ok",)]))

        result = factory.executar_consulta("SELECT 1")

        self.assertEqual(result, [("ok",)])

    def test_executar_consulta_com_parametros(self) -> None:
        """Executa consulta com parametros nomeados."""
        factory = EOLConnectionFactory(driver=FakeDriver(rows=[(1,)]))

        result = factory.executar_consulta(
            "SELECT * FROM tabela WHERE id=:id", {"id": 1}
        )

        self.assertEqual(result, [(1,)])

    def test_executar_comando_select(self) -> None:
        """Executa comando de leitura (SELECT)."""
        factory = EOLConnectionFactory(driver=FakeDriver(rows=[(1,)]))

        result = factory.executar_comando("SELECT 1")

        self.assertEqual(result, [(1,)])

    def test_bloqueio_escrita(self) -> None:
        """Tentativas de escrita devem gerar ConexaoSomenteLeituraError."""
        factory = EOLConnectionFactory(driver=FakeDriver())

        with self.assertRaises(ConexaoSomenteLeituraError):
            factory.executar_comando("INSERT INTO tabela VALUES (1)")


class TestEOLService(TestCase):
    """Testes do servico EOL de alto nivel."""

    def test_executar_query(self) -> None:
        """Executar query delega para a conexao."""
        conn = MagicMock()
        conn.executar_consulta.return_value = ["ok"]

        service = EOLService(conn)

        result = service.executar_query("SELECT 1")

        self.assertEqual(result, ["ok"])

    def test_validar_conectividade_true(self) -> None:
        """validar_conectividade retorna True quando ha resultados."""
        conn = MagicMock()
        conn.executar_consulta.return_value = [1]

        service = EOLService(conn)

        self.assertTrue(service.validar_conectividade())

    def test_validar_conectividade_false(self) -> None:
        """validar_conectividade retorna False quando vazio."""
        conn = MagicMock()
        conn.executar_consulta.return_value = []

        service = EOLService(conn)

        self.assertFalse(service.validar_conectividade())


class TestHealthcheckLib(TestCase):
    """Testes para o helper de healthcheck."""

    @patch("apps.eol_connection.libs.healthcheck.EOLService")
    def test_healthcheck_ok(self, mock_service: MagicMock) -> None:
        """Retorna healthy quando valida conectividade."""
        instance = mock_service.return_value
        instance.validar_conectividade.return_value = True

        result = healthcheck_eol()

        self.assertEqual(result["status"], "healthy")

    @patch("apps.eol_connection.libs.healthcheck.EOLService")
    def test_healthcheck_erro(self, mock_service: MagicMock) -> None:
        """Retorna unhealthy quando valida_conectividade False."""
        instance = mock_service.return_value
        instance.validar_conectividade.return_value = False

        result = healthcheck_eol()

        self.assertEqual(result["status"], "unhealthy")

    @patch("apps.eol_connection.libs.healthcheck.EOLService")
    def test_healthcheck_exception(self, mock_service: MagicMock) -> None:
        """Excecoes sao tratadas como unhealthy."""
        instance = mock_service.return_value
        instance.validar_conectividade.side_effect = RuntimeError("falha")

        result = healthcheck_eol()

        self.assertEqual(result["status"], "unhealthy")
