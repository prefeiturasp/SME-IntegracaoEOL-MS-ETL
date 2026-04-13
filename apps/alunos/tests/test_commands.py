from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.alunos.management.commands.etl_alunos import Command


class EtlAlunosCommandTest(TestCase):
    """Testes para o comando de management etl_alunos."""

    def test_command_setup(self) -> None:
        """Valida configuração básica do comando."""
        cmd = Command()
        self.assertEqual(cmd.dominio, "alunos")
        self.assertEqual(cmd.fase_final, 6)
        self.assertEqual(cmd.get_modo_escrita("aluno"), "upsert")
        self.assertEqual(cmd.get_modo_escrita("unknown"), "full_refresh")

    @patch("apps.alunos.services.EtlAlunosService.executar")
    @patch("apps.core.libs.base_etl_command.RepositorioAuditoriaPostgres")
    def test_command_execution(
        self, _mock_repo: MagicMock, mock_executar: MagicMock
    ) -> None:
        """Valida que o comando invoca o service com fase_inicial correto."""
        mock_executar.return_value = {"fase1": 10}

        out = StringIO()
        call_command("etl_alunos", "--fase", "1", stdout=out)

        self.assertTrue(mock_executar.called)
        mock_executar.assert_called_with(fase_inicial=1)
