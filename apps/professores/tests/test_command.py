"""Testes do management command etl_professores."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.controle_auditoria.models import EtlCheckpointDominio, EtlExecucao

_RESULTADO_MOCK = {
    "dre": 10,
    "tipo_escola": 5,
    "cargo": 16,
    "professor": 200,
    "cargo_base_servidor": 350,
    "atribuicao_aula": 1500,
}


class EtlProfessoresCommandTest(TestCase):
    """Testes de integração do management command etl_professores."""

    databases = ["default", "professores_db"]

    def _executar(self, args=None) -> None:  # type: ignore[no-untyped-def]
        """Executa o management command etl_professores com os argumentos fornecidos."""
        from django.core.management import call_command

        call_command("etl_professores", *(args or []))

    @patch("apps.professores.management.commands.etl_professores.EtlProfessoresService")
    def test_cria_execucao_e_finaliza_com_sucesso(
        self, mock_servico: MagicMock
    ) -> None:
        """Verifica que o command cria uma execução e a finaliza com sucesso."""
        mock_servico.return_value.executar.return_value = _RESULTADO_MOCK
        mock_servico.return_value.ultima_fase_concluida = 4

        self._executar()

        execucao = EtlExecucao.objects.get(dominio="professores")
        self.assertEqual(execucao.situacao, "concluido")
        self.assertIsNotNone(execucao.finalizado_em)

    @patch("apps.professores.management.commands.etl_professores.EtlProfessoresService")
    def test_cria_checkpoint_apos_sucesso(self, mock_servico: MagicMock) -> None:
        """Verifica que o command cria um checkpoint após execução bem-sucedida."""
        mock_servico.return_value.executar.return_value = _RESULTADO_MOCK
        mock_servico.return_value.ultima_fase_concluida = 4

        self._executar()

        checkpoint = EtlCheckpointDominio.objects.get(dominio="professores")
        self.assertEqual(checkpoint.ultima_situacao, "concluido")
        self.assertEqual(checkpoint.ultima_pagina, 4)
        total = sum(_RESULTADO_MOCK.values())
        self.assertEqual(checkpoint.token_parada, str(total))

    @patch("apps.professores.management.commands.etl_professores.EtlProfessoresService")
    def test_token_acumula_entre_execucoes(self, mock_servico: MagicMock) -> None:
        """Verifica que o token de parada acumula entre execuções consecutivas."""
        mock_servico.return_value.executar.return_value = {"professor": 100}
        mock_servico.return_value.ultima_fase_concluida = 4

        self._executar()
        self._executar(["--continuar"])

        checkpoint = EtlCheckpointDominio.objects.get(dominio="professores")
        self.assertEqual(checkpoint.token_parada, "200")

    @patch("apps.professores.management.commands.etl_professores.EtlProfessoresService")
    def test_erro_persiste_checkpoint_com_situacao_erro(
        self, mock_servico: MagicMock
    ) -> None:
        """Verifica que em caso de erro o checkpoint é persistido com situacao erro."""
        mock_servico.return_value.executar.side_effect = RuntimeError("conexão falhou")
        mock_servico.return_value.ultima_fase_concluida = 1

        with self.assertRaises(RuntimeError):
            self._executar()

        execucao = EtlExecucao.objects.get(dominio="professores")
        self.assertEqual(execucao.situacao, "erro")
        self.assertIn("conexão falhou", execucao.mensagem_erro)

        checkpoint = EtlCheckpointDominio.objects.get(dominio="professores")
        self.assertEqual(checkpoint.ultima_situacao, "erro")
        self.assertEqual(checkpoint.ultima_pagina, 1)

    @patch("apps.professores.management.commands.etl_professores.EtlProfessoresService")
    def test_continuar_apos_erro_retoma_fase_seguinte(
        self, mock_servico: MagicMock
    ) -> None:
        """Ao usar --continuar após erro, retoma a execução da fase seguinte."""
        # Simula erro na fase 2
        mock_servico.return_value.executar.side_effect = RuntimeError("erro fase 2")
        mock_servico.return_value.ultima_fase_concluida = 1
        with self.assertRaises(RuntimeError):
            self._executar()

        # Retoma: deve iniciar da fase 2
        mock_servico.return_value.executar.side_effect = None
        mock_servico.return_value.executar.return_value = {"professor": 50}
        mock_servico.return_value.ultima_fase_concluida = 4
        self._executar(["--continuar"])

        _, kwargs = mock_servico.return_value.executar.call_args
        self.assertEqual(kwargs.get("fase_inicial", 1), 2)

    @patch("apps.professores.management.commands.etl_professores.EtlProfessoresService")
    def test_continuar_apos_sucesso_reinicia_da_fase_1(
        self, mock_servico: MagicMock
    ) -> None:
        """Ao usar --continuar após sucesso, reinicia a execução da fase 1."""
        mock_servico.return_value.executar.return_value = _RESULTADO_MOCK
        mock_servico.return_value.ultima_fase_concluida = 4

        self._executar()
        self._executar(["--continuar"])

        _, kwargs = mock_servico.return_value.executar.call_args
        self.assertEqual(kwargs.get("fase_inicial", 1), 1)
