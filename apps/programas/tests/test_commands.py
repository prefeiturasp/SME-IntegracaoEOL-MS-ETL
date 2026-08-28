"""Testes do comando de gerenciamento etl_programas."""

from unittest.mock import patch
from uuid import UUID

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

_ID_EXECUCAO = UUID("12345678-1234-5678-1234-567812345678")


class EtlProgramasCommandTestCase(TestCase):
    """Valida o fluxo do comando etl_programas e a integração com auditoria."""

    databases = ["default", "eol_db", "programas_db"]

    def setUp(self) -> None:
        """Prepara mocks de auditoria e service usados nos cenários."""
        self.patcher_repo = patch(
            "apps.core.libs.base_etl_command.RepositorioAuditoriaPostgres"
        )
        self.mock_repo_class = self.patcher_repo.start()
        self.repo = self.mock_repo_class.return_value
        self.repo.iniciar_execucao.return_value = _ID_EXECUCAO

        self.patcher_servico = patch(
            "apps.programas.management.commands.etl_programas.Command.service_class"
        )
        self.mock_servico_class = self.patcher_servico.start()
        self.servico = self.mock_servico_class.return_value
        self.servico.executar.return_value = {
            "tipo_programa": 5,
            "componente_curricular_programa": 10,
            "turma_programa": 100,
            "turma_programa_componente_curricular": 150,
            "matricula_turma_programa": 500,
        }
        self.servico.ultima_fase_concluida = 5
        self.servico.ultimo_token = None

    def tearDown(self) -> None:
        """Desliga os patchers iniciados em setUp."""
        self.patcher_repo.stop()
        self.patcher_servico.stop()

    def test_execucao_completa_sucesso(self) -> None:
        """Valida fluxo de sucesso sem checkpoint prévio."""
        self.repo.obter_checkpoint_dominio.return_value = None

        call_command("etl_programas")

        self.repo.iniciar_execucao.assert_called_once_with("programas")
        self.servico.executar.assert_called_once_with(fase_inicial=1)
        self.repo.finalizar_execucao.assert_called_once_with(
            _ID_EXECUCAO, situacao="concluido"
        )
        self.repo.atualizar_checkpoint_dominio.assert_called_once()

    def test_execucao_com_continuar_retoma_fase_correta(self) -> None:
        """Valida que --continuar retoma da fase seguinte ao erro."""
        self.repo.obter_checkpoint_dominio.return_value = {
            "ultima_situacao": "erro",
            "ultima_pagina": 3,
            "token_parada": "100",
        }

        call_command("etl_programas", "--continuar")

        self.servico.executar.assert_called_once_with(fase_inicial=4)

    def test_execucao_com_volume(self) -> None:
        """Comando aceita --volume e executa normalmente."""
        call_command("etl_programas", "--volume", "100")
        self.servico.executar.assert_called()

    def test_extra_service_kwargs_com_anos_letivos(self) -> None:
        """Valida repasse de anos_letivos para o service."""
        from apps.programas.management.commands.etl_programas import Command

        cmd = Command()
        self.assertEqual(
            cmd._extra_service_kwargs(anos_letivos=[2025, 2026]),
            {"anos_letivos": [2025, 2026]},
        )
        self.assertEqual(cmd._extra_service_kwargs(anos_letivos=None), {})

    def test_tratamento_erro_na_execucao(self) -> None:
        """Valida que erros no serviço são registrados no log de auditoria."""
        self.servico.executar.side_effect = Exception("Erro Fatal")

        with self.assertRaises(CommandError):
            call_command("etl_programas")

        self.repo.finalizar_execucao.assert_called_once_with(
            _ID_EXECUCAO, situacao="erro", mensagem_erro="Erro Fatal"
        )
        self.repo.atualizar_checkpoint_dominio.assert_called_once()

    def test_execucao_com_continuar_sem_erro_anterior(self) -> None:
        """Valida retomada para fase 1 sem erro parcial."""
        self.repo.obter_checkpoint_dominio.return_value = {
            "ultima_situacao": "concluido",
            "ultima_pagina": 5,
        }

        call_command("etl_programas", "--continuar")

        self.servico.executar.assert_called_once_with(fase_inicial=1)
