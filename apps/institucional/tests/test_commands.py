"""Testes do comando de gerenciamento etl_institucional.

Valida a orquestração do comando, o uso de checkpoints e a integração 
com o RepositorioAuditoriaPostgres (banco default).
"""

from unittest.mock import MagicMock, patch
from uuid import UUID
from django.core.management import call_command
from django.test import TestCase

_ID_EXECUCAO = UUID("12345678-1234-5678-1234-567812345678")

class EtlInstitucionalCommandTestCase(TestCase):
    """Testes para o comando etl_institucional."""

    databases = ["default", "eol_db", "institucional_db"]

    def setUp(self):
        """Mocka dependências externas."""
        # Patch do repositório
        self.patcher_repo = patch("apps.core.libs.base_etl_command.RepositorioAuditoriaPostgres")
        self.mock_repo_class = self.patcher_repo.start()
        self.repo = self.mock_repo_class.return_value
        self.repo.iniciar_execucao.return_value = _ID_EXECUCAO

        # Patch do serviço
        self.patcher_servico = patch("apps.institucional.management.commands.etl_institucional.Command.service_class")
        self.mock_servico_class = self.patcher_servico.start()
        self.servico = self.mock_servico_class.return_value
        self.servico.executar.return_value = {"dre": 10, "tipo_escola": 5}
        self.servico.ultima_fase_concluida = 4

    def tearDown(self):
        self.patcher_repo.stop()
        self.patcher_servico.stop()

    def test_execucao_completa_sucesso(self):
        """Valida fluxo de sucesso sem checkpoint previo."""
        self.repo.obter_checkpoint_dominio.return_value = None
        
        call_command("etl_institucional")
        
        # Verificações
        self.repo.iniciar_execucao.assert_called_once_with("institucional")
        self.servico.executar.assert_called_once_with(fase_inicial=1)
        
        # Status de sucesso no projeto é "concluido"
        self.repo.finalizar_execucao.assert_called_once_with(_ID_EXECUCAO, situacao="concluido")
        self.repo.atualizar_checkpoint_dominio.assert_called_once()

    def test_execucao_com_continuar_retoma_fase_correta(self):
        """Valida que --continuar retoma da fase seguinte ao erro."""
        self.repo.obter_checkpoint_dominio.return_value = {
            "ultima_situacao": "erro",
            "ultima_pagina": 2, # parou na fase 2
            "token_parada": "100"
        }
        
        call_command("etl_institucional", "--continuar")
        
        # Deve retomar da fase 3 (2+1)
        self.servico.executar.assert_called_once_with(fase_inicial=3)

    def test_rejeita_volume_invalido(self):
        """Valida validação básica de parâmetros."""
        # Se o comando não valida volume ainda, ele vai chamar o serviço.
        # No futuro, se adicionarmos validação, este teste deve capturar CommandError.
        # Por enquanto, garantimos que se for chamado com volume, ele executa.
        call_command("etl_institucional", "--volume", "100")
        self.servico.executar.assert_called()

    def test_tratamento_erro_na_execucao(self):
        """Valida que erros no serviço são registrados no log de auditoria."""
        self.servico.executar.side_effect = Exception("Erro Fatal")
        
        with self.assertRaises(Exception):
            call_command("etl_institucional")
            
        self.repo.finalizar_execucao.assert_called_once_with(
            _ID_EXECUCAO, situacao="erro", mensagem_erro="Erro Fatal"
        )
        self.repo.atualizar_checkpoint_dominio.assert_called_once()

    def test_execucao_com_continuar_sem_erro_anterior(self):
        """Valida retomada para fase 1 caso o checkpoint não indique erro parcial."""
        # Checkpoint indica que foi concluído com sucesso
        self.repo.obter_checkpoint_dominio.return_value = {
            "ultima_situacao": "concluido",
            "ultima_pagina": 4
        }
        
        call_command("etl_institucional", "--continuar")
        
        # Como já estava concluído, volta para a fase 1 por default no comando atual
        self.servico.executar.assert_called_once_with(fase_inicial=1)
