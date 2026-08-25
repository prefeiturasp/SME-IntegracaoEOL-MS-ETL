from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.pedagogico.management.commands.etl_pedagogico import Command


class EtlPedagogicoCommandTest(TestCase):
    """Testes para o comando de management etl_pedagogico."""

    def test_command_setup(self) -> None:
        """Valida configuração básica do comando."""
        cmd = Command()
        self.assertEqual(cmd.dominio, "pedagogico")
        self.assertEqual(cmd.fase_final, 15)
        self.assertEqual(
            cmd.get_modo_escrita("componente_curricular"), "upsert"
        )
        self.assertEqual(
            cmd.get_modo_escrita("agrupamento_atribuicao_territorio_saber"),
            "full_refresh",
        )
        self.assertEqual(cmd.get_modo_escrita("unknown"), "full_refresh")

    @patch("apps.pedagogico.services.EtlPedagogicoService.executar")
    @patch("apps.core.libs.base_etl_command.RepositorioAuditoriaPostgres")
    def test_command_execution(
        self, _mock_repo: MagicMock, mock_executar: MagicMock
    ) -> None:
        """Valida que o comando invoca o service com fase_inicial correto."""
        mock_executar.return_value = {"fase1": 10}

        out = StringIO()
        call_command("etl_pedagogico", "--fase", "1", stdout=out)

        self.assertTrue(mock_executar.called)
        mock_executar.assert_called_with(fase_inicial=1)
