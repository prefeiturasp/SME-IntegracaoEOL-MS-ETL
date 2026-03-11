"""Testes dos commands do app escolas."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class ListarEscolasOffsetCommandTestCase(TestCase):
    """Valida comportamento do command listar_escolas_offset."""

    @patch(
        "apps.escolas.management.commands.listar_escolas_offset.ServicoEscolasOffset"
    )
    @patch(
        "apps.escolas.management.commands."
        "listar_escolas_offset.RepositorioAuditoriaPostgres"
    )
    def test_deve_processar_volume_e_atualizar_checkpoint(
        self,
        repositorio_cls_mock: MagicMock,
        servico_cls_mock: MagicMock,
    ) -> None:
        """Executa fluxo de sucesso e valida chamadas principais."""
        id_execucao = uuid4()

        repositorio = MagicMock()
        repositorio.obter_checkpoint_dominio.return_value = None
        repositorio.iniciar_execucao.return_value = id_execucao
        repositorio_cls_mock.return_value = repositorio

        servico = MagicMock()
        servico.TAMANHO_PAGINA_PADRAO = 100
        servico.listar_pagina.side_effect = [
            [
                {"codigo_escola": "000001"},
                {"codigo_escola": "000002"},
            ]
        ]
        servico_cls_mock.return_value = servico

        call_command(
            "listar_escolas_offset",
            "--volume",
            "2",
            "--offset",
            "0",
        )

        servico.listar_pagina.assert_called_once_with(limite=2, offset=0)
        repositorio.registrar_tabela_lida.assert_called_once()
        self.assertEqual(repositorio.atualizar_checkpoint_dominio.call_count, 2)
        repositorio.registrar_tabela_escrita.assert_called_once()
        repositorio.finalizar_execucao.assert_called_once_with(
            id_execucao=id_execucao,
            situacao="sucesso",
        )

    def test_deve_falhar_com_volume_invalido(self) -> None:
        """Valida erro de argumento quando volume e invalido."""
        with self.assertRaises(CommandError):
            call_command("listar_escolas_offset", "--volume", "0")

    def test_deve_falhar_com_offset_negativo(self) -> None:
        """Valida erro de argumento quando offset e negativo."""
        with self.assertRaises(CommandError):
            call_command("listar_escolas_offset", "--offset", "-1")


class TestarContinuidadeEscolasCommandTestCase(TestCase):
    """Valida command de continuidade do dominio escolas."""

    @patch(
        "apps.escolas.management.commands." "testar_continuidade_escolas.call_command"
    )
    def test_deve_chamar_listagem_duas_vezes(
        self, call_command_mock: MagicMock
    ) -> None:
        """Executa command e valida chamadas sequenciais."""
        call_command("testar_continuidade_escolas", "--volume", "25")

        self.assertEqual(call_command_mock.call_count, 2)
        primeira = call_command_mock.call_args_list[0].args
        segunda = call_command_mock.call_args_list[1].args

        self.assertEqual(
            primeira,
            ("listar_escolas_offset", "--volume", "25"),
        )
        self.assertEqual(
            segunda,
            ("listar_escolas_offset", "--volume", "25", "--continuar"),
        )
