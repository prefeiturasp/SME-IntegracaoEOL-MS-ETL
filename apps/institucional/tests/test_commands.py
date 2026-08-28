"""Testes do comando de gerenciamento etl_institucional."""

from unittest.mock import ANY, patch
from uuid import UUID

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

_ID_EXECUCAO = UUID("12345678-1234-5678-1234-567812345678")


class EtlInstitucionalCommandTestCase(TestCase):
    """Testes para o comando etl_institucional."""

    databases = ["default", "eol_db", "institucional_db"]

    def setUp(self) -> None:
        """Mocka dependências externas."""
        self.patcher_repo = patch(
            "apps.core.libs.base_etl_command.RepositorioAuditoriaPostgres"
        )
        self.mock_repo_class = self.patcher_repo.start()
        self.repo = self.mock_repo_class.return_value
        self.repo.iniciar_execucao.return_value = _ID_EXECUCAO

        self.patcher_servico = patch(
            "apps.institucional.management.commands.etl_institucional.Command.service_class"
        )
        self.mock_servico_class = self.patcher_servico.start()
        self.servico = self.mock_servico_class.return_value
        self.servico.executar.return_value = {"dre": 10, "tipo_escola": 5}
        self.servico.ultima_fase_concluida = 5

    def tearDown(self) -> None:
        """Encerra os mocks de repositório e serviço."""
        self.patcher_repo.stop()
        self.patcher_servico.stop()

    def test_execucao_completa_sucesso(self) -> None:
        """Valida fluxo de sucesso sem checkpoint previo."""
        self.repo.obter_checkpoint_dominio.return_value = None

        call_command("etl_institucional")

        self.repo.iniciar_execucao.assert_called_once_with(
            "institucional", parametros=ANY
        )
        self.servico.executar.assert_called_once_with(fase_inicial=1)

        self.repo.finalizar_execucao.assert_called_once_with(
            _ID_EXECUCAO, situacao="concluido"
        )
        self.repo.atualizar_checkpoint_dominio.assert_called_once()

    def test_execucao_com_continuar_retoma_fase_correta(self) -> None:
        """Valida que --continuar retoma da fase seguinte ao erro."""
        self.repo.obter_checkpoint_dominio.return_value = {
            "ultima_situacao": "erro",
            "ultima_pagina": 2,
            "token_parada": "100",
        }

        call_command("etl_institucional", "--continuar")

        self.servico.executar.assert_called_once_with(fase_inicial=3)

    def test_rejeita_volume_invalido(self) -> None:
        """Valida validação básica de parâmetros."""
        call_command("etl_institucional", "--volume", "100")
        self.servico.executar.assert_called()

    def test_tratamento_erro_na_execucao(self) -> None:
        """Valida que erros no serviço são registrados no log de auditoria."""
        self.servico.executar.side_effect = Exception("Erro Fatal")

        with self.assertRaises(CommandError):
            call_command("etl_institucional")

        self.repo.finalizar_execucao.assert_called_once_with(
            _ID_EXECUCAO, situacao="erro", mensagem_erro="Erro Fatal"
        )
        self.repo.atualizar_checkpoint_dominio.assert_called_once()

    def test_execucao_com_continuar_sem_erro_anterior(self) -> None:
        """Valida retomada quando o checkpoint não indica erro parcial."""
        self.repo.obter_checkpoint_dominio.return_value = {
            "ultima_situacao": "concluido",
            "ultima_pagina": 4,
        }

        call_command("etl_institucional", "--continuar")

        self.servico.executar.assert_called_once_with(fase_inicial=1)

    def test_get_modo_escrita(self) -> None:
        """Valida a lógica de modo de escrita para tabelas do domínio."""
        from apps.institucional.management.commands.etl_institucional import (
            Command,
        )

        cmd = Command()
        self.assertEqual(cmd.get_modo_escrita("dre"), "upsert")
        self.assertEqual(cmd.get_modo_escrita("outra_tabela"), "full_refresh")
