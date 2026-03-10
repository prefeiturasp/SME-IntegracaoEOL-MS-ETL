"""Testes dos commands do app controle_auditoria."""

from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class ExecutarDominioCommandTestCase(TestCase):
    """Valida o roteamento do command executar_dominio."""

    @patch("apps.controle_auditoria.management.commands.executar_dominio.call_command")
    def test_deve_executar_dominio_escola(self, call_command_mock) -> None:
        """Encaminha para listar_escolas_offset com argumentos."""
        call_command(
            "executar_dominio",
            "--dominio",
            "escola",
            "--volume",
            "200",
            "--offset",
            "100",
            "--continuar",
        )
        call_command_mock.assert_called_once_with(
            "listar_escolas_offset",
            "--volume",
            "200",
            "--offset",
            "100",
            "--continuar",
        )

    @patch(
        "apps.controle_auditoria.management.commands."
        "executar_dominio.exibir_validacao_sinc_rec_db"
    )
    def test_deve_executar_dominio_sinc_rec_db(
        self,
        validacao_mock,
    ) -> None:
        """Executa validacao do dominio de controle."""
        call_command("executar_dominio", "--dominio", "sinc_rec_db")
        validacao_mock.assert_called_once_with()

    def test_deve_falhar_com_dominio_invalido(self) -> None:
        """Retorna erro quando dominio nao e reconhecido."""
        with self.assertRaises(CommandError):
            call_command("executar_dominio", "--dominio", "invalido")
