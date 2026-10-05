"""Testes para a factory de conexões read-only."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.core.libs.connection_readonly import (
    ConexaoSomenteLeituraError,
    ReadOnlySQLServerConnectionFactory,
)


class TestConnectionFactory(TestCase):
    """Testes unitários para ReadOnlySQLServerConnectionFactory."""

    @patch("django.conf.settings.DATABASES")
    def test_executar_consulta_converte_lista_em_tupla(
        self, mock_databases: MagicMock
    ) -> None:
        """Valida que parâmetros em lista são convertidos para tupla para o driver."""
        mock_databases.__contains__.return_value = True
        mock_databases.__getitem__.return_value = {"NAME": "fake"}

        factory = ReadOnlySQLServerConnectionFactory(db_alias="fake_db")

        with patch(
            "apps.core.libs.connection_readonly.connections"
        ) as mock_connections:
            mock_cursor = mock_connections[
                "fake_db"
            ].cursor.return_value.__enter__.return_value
            mock_cursor.fetchmany.return_value = []  # Termina o loop de fetch

            sql = "SELECT * FROM table WHERE id IN (%s, %s)"
            parametros = [1, 2]

            factory.executar_consulta(sql, parametros=parametros)

            # O execute deve ter sido chamado com a TUPLA (1, 2)
            mock_cursor.execute.assert_called_once_with(sql, (1, 2))

    @patch("django.conf.settings.DATABASES")
    def test_bloqueio_escrita_triggers_error(self, mock_databases: MagicMock) -> None:
        """Garante que comandos de escrita disparam ConexaoSomenteLeituraError."""
        mock_databases.__contains__.return_value = True
        mock_databases.__getitem__.return_value = {"NAME": "fake"}

        factory = ReadOnlySQLServerConnectionFactory(db_alias="fake_db")

        comandos_proibidos = [
            "INSERT INTO table VALUES (1)",
            "UPDATE table SET x=1",
            "DELETE FROM table",
            "DROP TABLE x",
        ]

        for sql in comandos_proibidos:
            with self.subTest(sql=sql), self.assertRaises(ConexaoSomenteLeituraError):
                factory.executar_comando(sql)

    @patch("django.conf.settings.DATABASES")
    def test_fetch_many_acumula_resultados(self, mock_databases: MagicMock) -> None:
        """Valida que o loop de fetchmany funciona corretamente."""
        mock_databases.__contains__.return_value = True
        mock_databases.__getitem__.return_value = {"NAME": "fake"}

        factory = ReadOnlySQLServerConnectionFactory(db_alias="fake_db", chunk_size=2)

        with patch(
            "apps.core.libs.connection_readonly.connections"
        ) as mock_connections:
            mock_cursor = mock_connections[
                "fake_db"
            ].cursor.return_value.__enter__.return_value
            # Simula dois lotes de dados
            mock_cursor.fetchmany.side_effect = [[(1,), (2,)], [(3,)], []]

            resultados = factory.executar_consulta("SELECT col FROM table")

            self.assertEqual(len(resultados), 3)
            self.assertEqual(resultados, [(1,), (2,), (3,)])

    @patch("django.conf.settings.DATABASES")
    def test_iter_consulta_com_parametros(self, mock_databases: MagicMock) -> None:
        """Valida se iter_consulta passa os parâmetros para o cursor."""
        mock_databases.__contains__.return_value = True
        mock_databases.__getitem__.return_value = {"NAME": "fake"}

        factory = ReadOnlySQLServerConnectionFactory(db_alias="fake_db")

        with patch(
            "apps.core.libs.connection_readonly.connections"
        ) as mock_connections:
            mock_cursor = mock_connections[
                "fake_db"
            ].cursor.return_value.__enter__.return_value
            mock_cursor.fetchmany.return_value = []

            sql = "SELECT * FROM table WHERE id = %s"
            parametros = {"id": 1}

            # Força o consumo do generator
            list(factory.iter_consulta(sql, parametros=parametros))

            mock_cursor.execute.assert_called_once_with(sql, parametros)

    @patch("django.conf.settings.DATABASES")
    def test_iter_consulta_limite_lote_maximo(self, mock_databases: MagicMock) -> None:
        """Garante que a iteração para ao atingir lote_maximo."""
        mock_databases.__contains__.return_value = True
        mock_databases.__getitem__.return_value = {"NAME": "fake"}

        # Limite de 1 lote
        factory = ReadOnlySQLServerConnectionFactory(
            db_alias="fake_db", chunk_size=1, lote_maximo=1
        )

        with patch(
            "apps.core.libs.connection_readonly.connections"
        ) as mock_connections:
            mock_cursor = mock_connections[
                "fake_db"
            ].cursor.return_value.__enter__.return_value
            # Simula que haveria mais dados se continuasse
            mock_cursor.fetchmany.return_value = [(1,)]

            # Consome o generator
            list(factory.iter_consulta("SELECT * FROM table"))

            # Verifica que fetchmany foi chamado apenas UMA vez
            # (além do stop que nem chegou a acontecer)
            # Na verdade, se o break ocorre após o yield, ele não deve fazer o
            # próximo cycle.
            self.assertEqual(mock_cursor.fetchmany.call_count, 1)

    @patch("django.conf.settings.DATABASES")
    def test_error_handling_em_executar_e_iter_consulta(
        self, mock_databases: MagicMock
    ) -> None:
        """Garante que exceções no banco são logadas e re-lançadas."""
        mock_databases.__contains__.return_value = True
        mock_databases.__getitem__.return_value = {"NAME": "fake"}

        factory = ReadOnlySQLServerConnectionFactory(db_alias="fake_db")

        with patch(
            "apps.core.libs.connection_readonly.connections"
        ) as mock_connections:
            mock_cursor = mock_connections[
                "fake_db"
            ].cursor.return_value.__enter__.return_value
            mock_cursor.execute.side_effect = RuntimeError("Database error")

            # Teste em executar_consulta
            with self.assertRaises(RuntimeError):
                factory.executar_consulta("SELECT 1")

            # Teste em iter_consulta
            with self.assertRaises(RuntimeError):
                list(factory.iter_consulta("SELECT 1"))

    @patch("django.conf.settings.DATABASES")
    def test_init_invalid_db_alias(self, mock_databases: MagicMock) -> None:
        """Garante que erro é lançado se o alias do banco não existe."""
        mock_databases.__contains__.return_value = False

        with self.assertRaises(ValueError):
            ReadOnlySQLServerConnectionFactory(db_alias="non_existent")

    @patch("django.conf.settings.DATABASES")
    def test_executar_comando_sucesso(self, mock_databases: MagicMock) -> None:
        """Garante que executar_comando chama executar_consulta para SELECTs."""
        mock_databases.__contains__.return_value = True
        mock_databases.__getitem__.return_value = {"NAME": "fake"}

        factory = ReadOnlySQLServerConnectionFactory(db_alias="fake_db")

        with patch.object(factory, "executar_consulta") as mock_executar_consulta:
            mock_executar_consulta.return_value = [(1,)]
            sql = "SELECT * FROM table"
            resultado = factory.executar_comando(sql)

            mock_executar_consulta.assert_called_once_with(sql)
            self.assertEqual(resultado, [(1,)])

    @patch("django.conf.settings.DATABASES")
    def test_executar_consulta_sem_parametros(self, mock_databases: MagicMock) -> None:
        """Valida execução de consulta sem parâmetros (cobertura do else)."""
        mock_databases.__contains__.return_value = True
        mock_databases.__getitem__.return_value = {"NAME": "fake"}

        factory = ReadOnlySQLServerConnectionFactory(db_alias="fake_db")

        with patch(
            "apps.core.libs.connection_readonly.connections"
        ) as mock_connections:
            mock_cursor = mock_connections[
                "fake_db"
            ].cursor.return_value.__enter__.return_value
            mock_cursor.fetchmany.return_value = []

            sql = "SELECT 1"
            factory.executar_consulta(sql)

            mock_cursor.execute.assert_called_once_with(sql)

    @patch("django.conf.settings.DATABASES")
    def test_error_tabela_nao_encontrada_consulta_e_iter(self, mock_databases: MagicMock) -> None:
        """(Tabela não encontrada)."""
        mock_databases.__contains__.return_value = True
        mock_databases.__getitem__.return_value = {"NAME": "fake"}
        factory = ReadOnlySQLServerConnectionFactory(db_alias="fake_db")
        
        with patch("apps.core.libs.connection_readonly.connections") as mock_connections:
            mock_cursor = mock_connections["fake_db"].cursor.return_value.__enter__.return_value
            # Caso 1: executar_consulta
            mock_cursor.execute.side_effect = RuntimeError("no such table: XYZ")
            with self.assertRaises(RuntimeError):
                factory.executar_consulta("SELECT 1")
            
            # Caso 2: iter_consulta
            mock_cursor.execute.side_effect = RuntimeError("invalid object name: 'ZYX'")
            with self.assertRaises(RuntimeError):
                list(factory.iter_consulta("SELECT 1"))

    @patch("apps.core.libs.connection_readonly.time.sleep")
    @patch("django.conf.settings.DATABASES")
    def test_iter_consulta_reconecta_apos_queda_de_conexao(
        self, mock_databases: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Reconecta e refaz a consulta após erro de conexão TCP 10054."""
        mock_databases.__contains__.return_value = True
        mock_databases.__getitem__.return_value = {"NAME": "fake"}
        factory = ReadOnlySQLServerConnectionFactory(db_alias="fake_db")

        with patch(
            "apps.core.libs.connection_readonly.connections"
        ) as mock_connections:
            mock_cursor = mock_connections[
                "fake_db"
            ].cursor.return_value.__enter__.return_value
            mock_cursor.fetchmany.side_effect = [
                RuntimeError("[08S01] TCP Provider: error 0x2746 (10054)"),
                [(1,)],
                [],
            ]

            chunks = list(factory.iter_consulta("SELECT 1", chunk_size=1))

            self.assertEqual(chunks, [[(1,)]])
            mock_connections["fake_db"].close.assert_called_once()
            mock_sleep.assert_called_once()

    @patch("apps.core.libs.connection_readonly.time.sleep")
    @patch("django.conf.settings.DATABASES")
    def test_iter_consulta_desiste_apos_maximo_de_tentativas(
        self, mock_databases: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Propaga o erro de conexão após esgotar as tentativas."""
        mock_databases.__contains__.return_value = True
        mock_databases.__getitem__.return_value = {"NAME": "fake"}
        factory = ReadOnlySQLServerConnectionFactory(db_alias="fake_db")

        with patch(
            "apps.core.libs.connection_readonly.connections"
        ) as mock_connections:
            mock_cursor = mock_connections[
                "fake_db"
            ].cursor.return_value.__enter__.return_value
            mock_cursor.fetchmany.side_effect = RuntimeError(
                "[08S01] connection reset (10054)"
            )

            with self.assertRaises(RuntimeError):
                list(factory.iter_consulta("SELECT 1"))
