"""Testes unitarios das bibliotecas de eol_connection."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.eol_connection.libs.connection import EOLConnectionFactory
from apps.eol_connection.libs.exceptions import ConexaoSomenteLeituraError
from apps.eol_connection.libs.healthcheck import healthcheck_eol
from apps.eol_connection.libs.servico_eol import EOLService
from config.settings import _parse_eol_db


class TestParseUrlDb(TestCase):
    """Testes para a funcao _parse_eol_db."""

    def test_parse_url_vazia(self) -> None:
        """Retorna dict vazio para URL vazia."""
        self.assertEqual(_parse_eol_db(""), {})

    def test_parse_url_valida(self) -> None:
        """Extrai corretamente os campos de uma URL MSSQL valida."""
        url = (
            "mssql+pyodbc://user:pass@10.0.0.1:1433/db"
            "?driver=ODBC+Driver+18+for+SQL+Server"
            "&TrustServerCertificate=yes"
        )
        config = _parse_eol_db(url)
        self.assertEqual(config["ENGINE"], "mssql")
        self.assertEqual(config["NAME"], "db")
        self.assertEqual(config["USER"], "user")
        self.assertEqual(config["PASSWORD"], "pass")
        self.assertEqual(config["HOST"], "10.0.0.1")
        self.assertEqual(config["PORT"], "1433")
        self.assertEqual(  # type: ignore[index]
            config["OPTIONS"]["driver"], "ODBC Driver 18 for SQL Server"
        )
        self.assertEqual(  # type: ignore[index]
            config["OPTIONS"]["TrustServerCertificate"], "yes"
        )
        self.assertEqual(config["OPTIONS"]["Encrypt"], False)  # type: ignore


class TestConnectionFactory(TestCase):
    """Testes para `EOLConnectionFactory`."""

    def test_banco_nao_configurado(self) -> None:
        """Erro quando banco nao esta configurado no settings.DATABASES."""
        with override_settings(DATABASES={}), self.assertRaises(ValueError):
            EOLConnectionFactory(db_alias="eol_db")

    @override_settings(DATABASES={"eol_db": {"ENGINE": "mssql"}})
    @patch("apps.eol_connection.libs.connection.connections")
    def test_obter_conexao(self, mock_connections: MagicMock) -> None:
        """Obter conexao retorna a conexao do Django."""
        mock_conn = MagicMock()
        mock_connections.__getitem__.return_value = mock_conn

        factory = EOLConnectionFactory(db_alias="eol_db")
        conn = factory.obter_conexao()

        self.assertEqual(conn, mock_conn)
        mock_connections.__getitem__.assert_called_with("eol_db")

    @override_settings(DATABASES={"eol_db": {"ENGINE": "mssql"}})
    @patch("apps.eol_connection.libs.connection.connections")
    def test_executar_consulta(self, mock_connections: MagicMock) -> None:
        """Executa consulta e retorna resultados."""
        mock_cursor = MagicMock()
        mock_cursor.fetchmany.side_effect = [[("ok",)], []]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connections.__getitem__.return_value = mock_conn

        factory = EOLConnectionFactory(db_alias="eol_db")
        result = factory.executar_consulta("SELECT 1")

        self.assertEqual(result, [("ok",)])
        mock_cursor.execute.assert_called_with("SELECT 1")

    @override_settings(DATABASES={"eol_db": {"ENGINE": "mssql"}})
    @patch("apps.eol_connection.libs.connection.connections")
    def test_executar_consulta_com_parametros(
        self, mock_connections: MagicMock
    ) -> None:
        """Executa consulta com parametros nomeados."""
        mock_cursor = MagicMock()
        mock_cursor.fetchmany.side_effect = [[(1,)], []]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connections.__getitem__.return_value = mock_conn

        factory = EOLConnectionFactory(db_alias="eol_db")
        result = factory.executar_consulta(
            "SELECT * FROM tabela WHERE id=:id", {"id": 1}
        )

        self.assertEqual(result, [(1,)])
        mock_cursor.execute.assert_called_with(
            "SELECT * FROM tabela WHERE id=:id", {"id": 1}
        )

    @override_settings(DATABASES={"eol_db": {"ENGINE": "mssql"}})
    @patch("apps.eol_connection.libs.connection.connections")
    def test_executar_comando_select(self, mock_connections: MagicMock) -> None:
        """Executa comando de leitura (SELECT)."""
        mock_cursor = MagicMock()
        mock_cursor.fetchmany.side_effect = [[(1,)], []]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connections.__getitem__.return_value = mock_conn

        factory = EOLConnectionFactory(db_alias="eol_db")
        result = factory.executar_comando("SELECT 1")

        self.assertEqual(result, [(1,)])

    @override_settings(DATABASES={"eol_db": {"ENGINE": "mssql"}})
    def test_bloqueio_escrita(self) -> None:
        """Tentativas de escrita devem gerar ConexaoSomenteLeituraError."""
        factory = EOLConnectionFactory(db_alias="eol_db")

        with self.assertRaises(ConexaoSomenteLeituraError):
            factory.executar_comando("INSERT INTO tabela VALUES (1)")

    @override_settings(DATABASES={"eol_db": {"ENGINE": "mssql"}})
    @patch("apps.eol_connection.libs.connection.connections")
    def test_executar_consulta_exception(self, mock_connections: MagicMock) -> None:
        """Ao ocorrer erro no driver, a exception e propagada."""
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = RuntimeError("erro banco")
        mock_connections.__getitem__.return_value = mock_conn

        factory = EOLConnectionFactory(db_alias="eol_db")

        with self.assertRaises(RuntimeError):
            factory.executar_consulta("SELECT 1")

    @override_settings(DATABASES={"eol_db": {"ENGINE": "mssql"}})
    @patch("apps.eol_connection.libs.connection.connections")
    def test_iter_consulta(self, mock_connections: MagicMock) -> None:
        """Iter consulta faz yield de chunks e registra logs."""
        mock_cursor = MagicMock()
        # Simula 2 chunks de 1 registro e depois vazio
        mock_cursor.fetchmany.side_effect = [[(1,)], [(2,)], []]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connections.__getitem__.return_value = mock_conn

        factory = EOLConnectionFactory(db_alias="eol_db")
        chunks = list(factory.iter_consulta("SELECT 1", chunk_size=1))

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], [(1,)])
        self.assertEqual(chunks[1], [(2,)])

    @override_settings(DATABASES={"eol_db": {"ENGINE": "mssql"}})
    @patch("apps.eol_connection.libs.connection.connections")
    def test_iter_consulta_exception(self, mock_connections: MagicMock) -> None:
        """Exceções no meio da iteração são propagadas."""
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = RuntimeError("falha no meio")
        mock_connections.__getitem__.return_value = mock_conn

        factory = EOLConnectionFactory(db_alias="eol_db")
        with self.assertRaises(RuntimeError):
            list(factory.iter_consulta("SELECT 1"))


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
