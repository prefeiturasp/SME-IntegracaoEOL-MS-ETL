"""Testes para a classe base de comandos ETL."""

from unittest.mock import MagicMock, patch

from django.core.management.base import CommandError
from django.test import TestCase

from apps.core.libs.base_etl_command import BaseEtlCommand


class BaseEtlCommandTestCase(TestCase):
    """Valida o funcionamento orquestrado da BaseEtlCommand."""

    def setUp(self):
        """Mocka o repositório de auditoria e serviço."""
        self.patcher_repo = patch("apps.core.libs.base_etl_command.RepositorioAuditoriaPostgres")
        self.mock_repo_class = self.patcher_repo.start()
        self.repo = self.mock_repo_class.return_value
        
        # Mock do serviço local por teste
        self.mock_servico_class = MagicMock()
        self.servico = self.mock_servico_class.return_value
        
        class MyTestCommand(BaseEtlCommand):
            dominio = "teste_base"
            service_class = self.mock_servico_class

        self.cmd = MyTestCommand()
        self.cmd.stdout = MagicMock()
        self.cmd.stderr = MagicMock()

    def tearDown(self):
        """Finaliza patches."""
        self.patcher_repo.stop()

    def test_executa_fluxo_sucesso_completo(self):
        """Valida que todos os métodos do repositório são chamados corretamente."""
        self.servico.executar.return_value = {"tabela_teste": 50}
        self.servico.ultima_fase_concluida = 1

        self.cmd.handle(volume=100, offset=0, continuar=False)

        # Verificações
        self.assertTrue(self.repo.iniciar_execucao.called)
        
        id_exec = self.repo.iniciar_execucao.return_value
        
        self.repo.finalizar_execucao.assert_called_with(
            id_exec,
            situacao="concluido",
        )
        self.repo.atualizar_checkpoint_dominio.assert_called()
        self.repo.registrar_tabela_escrita.assert_called_with(
            id_execucao=id_exec,
            tabela_destino="tabela_teste",
            linhas_escritas=50,
            modo_escrita="full_refresh",
        )

    def test_retomar_checkpoint_na_flag_continuar(self):
        """Verifica se busca checkpoint quando continuar=True."""
        self.repo.obter_checkpoint_dominio.return_value = {
            "ultima_pagina": 2,
            "ultima_situacao": "erro",
            "token_parada": "100",
        }
        self.servico.executar.return_value = {"tabela_teste": 10}
        self.servico.ultima_fase_concluida = 3

        self.cmd.handle(volume=100, offset=0, continuar=True)

        self.repo.obter_checkpoint_dominio.assert_called_with("teste_base")
        self.servico.executar.assert_called_with(fase_inicial=3)

    def test_trata_erro_no_servico_e_persiste_situacao_erro(self):
        """Verifica que exceção no serviço é auditada como erro."""
        self.servico.executar.side_effect = Exception("Crash total")
        self.servico.ultima_fase_concluida = 0

        with self.assertRaises(CommandError):
            self.cmd.handle(volume=100, offset=0, continuar=False)

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
            indice_sincronizacao=None,
            ultima_situacao="erro",
            sucesso=False,
        )

    def test_falta_configuracao_gera_erro_no_setup(self):
        """Verifica se a base protege contra falta de dominio/servico."""
        class Invalido(BaseEtlCommand):
            pass

        with self.assertRaises(NotImplementedError):
            Invalido()
            
        class SemServico(BaseEtlCommand):
            dominio = "x"
            
        with self.assertRaises(NotImplementedError):
            SemServico()

    def test_continuar_sem_checkpoint(self):
        """Valida que se continuar=True mas sem checkpoint, inicia do 1."""
        self.repo.obter_checkpoint_dominio.return_value = None
        self.servico.executar.return_value = {}
        self.servico.ultima_fase_concluida = 1
        
        self.cmd.handle(volume=100, offset=0, continuar=True)
        
        self.servico.executar.assert_called_with(fase_inicial=1)

    def test_continuar_com_sucesso_anterior(self):
        """Valida que se o último sucesso foi concluído, reinicia do 1."""
        self.repo.obter_checkpoint_dominio.return_value = {
            "ultima_pagina": 4,
            "ultima_situacao": "concluido",
            "token_parada": "500",
        }
        self.servico.executar.return_value = {}
        self.servico.ultima_fase_concluida = 1
        
        self.cmd.handle(volume=100, offset=0, continuar=True)
        
        self.servico.executar.assert_called_with(fase_inicial=1)

    def test_get_modo_escrita_default(self):
        """Verifica o valor default do modo de escrita."""
        self.assertEqual(self.cmd.get_modo_escrita("tabela"), "full_refresh")

    def test_add_arguments(self):
        """Garante que os argumentos padrão são registrados no parser."""
        mock_parser = MagicMock()
        self.cmd.add_arguments(mock_parser)
        
        # Verifica se add_argument foi chamado para cada opção
        calls = [c[0][0] for c in mock_parser.add_argument.call_args_list]
        self.assertIn("--volume", calls)
        self.assertIn("--offset", calls)
        self.assertIn("--continuar", calls)
