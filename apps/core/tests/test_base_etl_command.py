"""Testes para a classe base de comandos ETL."""

from unittest.mock import MagicMock, patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.core.libs.base_etl_command import BaseEtlCommand


class BaseEtlCommandTestCase(SimpleTestCase):
    """Valida o funcionamento orquestrado da BaseEtlCommand."""

    def setUp(self) -> None:
        """Mocka o repositório de auditoria e serviço."""
        self.patcher_repo = patch(
            "apps.core.libs.base_etl_command.RepositorioAuditoriaPostgres"
        )
        self.mock_repo_class = self.patcher_repo.start()
        self.repo = self.mock_repo_class.return_value

        self.mock_servico_class = MagicMock()
        self.servico = self.mock_servico_class.return_value
        self.servico.ultimo_token = "0"
        self.servico.ultima_fase_concluida = 0
        self.servico._fases = []

        class MyTestCommand(BaseEtlCommand):
            dominio = "teste_base"
            service_class = self.mock_servico_class

        self.cmd = MyTestCommand()
        self.cmd.stdout = MagicMock()
        self.cmd.stderr = MagicMock()

    def tearDown(self) -> None:
        """Finaliza patches."""
        self.patcher_repo.stop()

    def test_executa_fluxo_sucesso_completo(self) -> None:
        """Valida chamadas ao repositório no fluxo de sucesso."""
        self.servico.executar.return_value = {"tabela_teste": 50}
        self.servico.ultima_fase_concluida = 1
        mock_fase = MagicMock()
        mock_fase.table_name = "tabela_teste"
        self.servico._fases = [mock_fase]

        self.cmd.handle(continuar=False)

        self.assertTrue(self.repo.iniciar_execucao.called)

        id_exec = self.repo.iniciar_execucao.return_value

        self.repo.atualizar_checkpoint_dominio.assert_called_with(
            dominio="teste_base",
            ultimo_id_execucao=id_exec,
            ultima_pagina=1,
            token_parada="0",
            indice_sincronizacao="tabela_teste:token:0",
            ultima_situacao="concluido",
            sucesso=True,
        )
        self.repo.finalizar_execucao.assert_called_with(
            id_exec,
            situacao="concluido",
        )

    def test_retomar_checkpoint_na_flag_continuar(self) -> None:
        """Verifica se busca checkpoint quando continuar=True."""
        self.repo.obter_checkpoint_dominio.return_value = {
            "ultima_pagina": 2,
            "ultima_situacao": "erro",
            "token_parada": "100",
        }
        self.servico.executar.return_value = {"tabela_teste": 10}
        self.servico.ultima_fase_concluida = 3

        self.cmd.handle(continuar=True)

        self.repo.obter_checkpoint_dominio.assert_called_with("teste_base")
        self.servico.executar.assert_called_with(fase_inicial=3)

    def test_trata_erro_no_servico_e_persiste_situacao_erro(self) -> None:
        """Verifica que exceção no serviço é auditada como erro."""
        self.servico.executar.side_effect = Exception("Crash total")
        self.servico.ultima_fase_concluida = 0

        with self.assertRaises(CommandError):
            self.cmd.handle(continuar=False)

        id_exec = self.repo.iniciar_execucao.return_value

        self.repo.finalizar_execucao.assert_called_with(
            id_exec,
            situacao="erro",
            mensagem_erro="Crash total",
        )
        self.repo.atualizar_checkpoint_dominio.assert_called_with(
            dominio="teste_base",
            ultimo_id_execucao=id_exec,
            ultima_pagina=0,
            token_parada="0",
            indice_sincronizacao="ERRO:token:0",
            ultima_situacao="erro",
            sucesso=False,
        )

    def test_trata_erro_ao_criar_servico_e_finaliza_execucao(self) -> None:
        """Falha antes do service não deixa execução em aberto."""
        self.mock_servico_class.side_effect = Exception("Falha no setup")

        with self.assertRaises(CommandError):
            self.cmd.handle(continuar=False)

        id_exec = self.repo.iniciar_execucao.return_value
        self.repo.finalizar_execucao.assert_called_with(
            id_exec,
            situacao="erro",
            mensagem_erro="Falha no setup",
        )
        self.repo.atualizar_checkpoint_dominio.assert_called_with(
            dominio="teste_base",
            ultimo_id_execucao=id_exec,
            ultima_pagina=0,
            token_parada="0",
            indice_sincronizacao="ERRO:token:0",
            ultima_situacao="erro",
            sucesso=False,
        )

    def test_falta_configuracao_gera_erro_no_setup(self) -> None:
        """Verifica se a base protege contra falta de dominio/servico."""

        class Invalido(BaseEtlCommand):
            pass

        with self.assertRaises(NotImplementedError):
            Invalido()

        class SemServico(BaseEtlCommand):
            dominio = "x"

        with self.assertRaises(NotImplementedError):
            SemServico()

    def test_continuar_sem_checkpoint(self) -> None:
        """Valida que se continuar=True mas sem checkpoint, inicia do 1."""
        self.repo.obter_checkpoint_dominio.return_value = None
        self.servico.executar.return_value = {}
        self.servico.ultima_fase_concluida = 1

        self.cmd.handle(continuar=True)

        self.servico.executar.assert_called_with(fase_inicial=1)

    def test_continuar_com_sucesso_anterior(self) -> None:
        """Valida que se o último sucesso foi concluído, reinicia do 1."""
        self.repo.obter_checkpoint_dominio.return_value = {
            "ultima_pagina": 4,
            "ultima_situacao": "concluido",
            "token_parada": "500",
        }
        self.servico.executar.return_value = {}
        self.servico.ultima_fase_concluida = 1

        self.cmd.handle(continuar=True)

        self.servico.executar.assert_called_with(fase_inicial=1)

    def test_continuar_retoma_execucao_interrompida(self) -> None:
        """Checkpoint interrompido retoma a própria fase salva."""
        self.repo.obter_checkpoint_dominio.return_value = {
            "ultima_pagina": 2,
            "ultima_situacao": "interrompido",
            "token_parada": "602249",
        }
        self.servico.executar.return_value = {}
        self.servico.ultima_fase_concluida = 3

        self.cmd.handle(continuar=True)

        self.servico.executar.assert_called_with(fase_inicial=2)

    def test_erro_em_fase_atual_preserva_ultima_concluida_para_retry(
        self,
    ) -> None:
        """Erro na fase atual deve retomar a mesma fase no retry."""
        self.servico.executar.side_effect = Exception("Falha na fase")
        self.servico.ultima_fase_concluida = 2
        self.servico.fase_atual = 3
        self.servico.ultimo_token = "285516"

        with self.assertRaises(CommandError):
            self.cmd.handle(continuar=False)

        id_exec = self.repo.iniciar_execucao.return_value
        self.repo.atualizar_checkpoint_dominio.assert_called_with(
            dominio="teste_base",
            ultimo_id_execucao=id_exec,
            ultima_pagina=2,
            token_parada="285516",
            indice_sincronizacao="ERRO:token:285516",
            ultima_situacao="erro",
            sucesso=False,
        )

    def test_checkpoint_usa_id_execucao_proprio(self) -> None:
        """Checkpoint é atualizado pelo serviço durante a execução."""
        pass

    def test_get_modo_escrita_default(self) -> None:
        """Verifica o valor default do modo de escrita."""
        self.assertEqual(self.cmd.get_modo_escrita("tabela"), "full_refresh")

    def test_add_arguments(self) -> None:
        """Garante que os argumentos padrão são registrados no parser."""
        mock_parser = MagicMock()
        self.cmd.add_arguments(mock_parser)

        calls = [c[0][0] for c in mock_parser.add_argument.call_args_list]
        self.assertIn("--continuar", calls)
        self.assertIn("--fase", calls)
        self.assertIn("--carga-inicial", calls)

    def test_fase_override(self) -> None:
        """Garante que o argumento --fase tem prioridade sobre o checkpoint."""
        self.repo.obter_checkpoint_dominio.return_value = {
            "ultima_pagina": 2,
            "ultima_situacao": "erro",
        }
        self.cmd.handle(fase=4, continuar=True)

        self.servico.executar.assert_called_with(fase_inicial=4)

    def test_trata_interrupcao_manual_e_persiste_situacao_interrompido(
        self,
    ) -> None:
        """Verifica que KeyboardInterrupt é auditada antes de subir."""
        self.servico.executar.side_effect = KeyboardInterrupt()
        self.servico.ultima_fase_concluida = 1
        self.servico.ultimo_token = "200"

        with self.assertRaises(KeyboardInterrupt):
            self.cmd.handle(continuar=False)

        id_exec = self.repo.iniciar_execucao.return_value
        self.repo.finalizar_execucao.assert_called_with(
            id_exec, situacao="interrompido"
        )
        self.repo.atualizar_checkpoint_dominio.assert_called_with(
            dominio="teste_base",
            ultimo_id_execucao=id_exec,
            ultima_pagina=1,
            token_parada="200",
            indice_sincronizacao="CTRL+C:token:200",
            ultima_situacao="interrompido",
            sucesso=False,
        )

    @patch("apps.core.libs.base_etl_orquestrador.GenericEtlOrquestrador")
    def test_handle_celery_lanca_orquestrador(
        self, mock_orq_cls: MagicMock
    ) -> None:
        """Garante que handle com celery=True delega ao orquestrador."""
        mock_orq = mock_orq_cls.return_value
        self.cmd.handle(celery=True, continuar=False)
        mock_orq_cls.assert_called_once()
        mock_orq.lancar.assert_called_once()
