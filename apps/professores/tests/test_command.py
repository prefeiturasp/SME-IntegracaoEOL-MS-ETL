"""Testes do management command etl_professores."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.controle_auditoria.models import EtlCheckpointDominio, EtlExecucao
from apps.professores.management.commands.etl_professores import (
    _TABELAS_UPSERT,
    Command,
)
from apps.professores.services import _ORDEM_TABELAS

_RESULTADO_MOCK = {
    "unidade_educacional": 10,
    "turma_escola": 5,
    "professor": 200,
    "cargo_base_servidor": 350,
    "atribuicao_aula": 1500,
    "funcionario_unidade_educacional": 20,
}


class EtlProfessoresCommandTest(TestCase):
    """Testes de integração do management command etl_professores."""

    databases = ["default", "professores_db"]

    def _executar(self, args=None) -> None:  # type: ignore[no-untyped-def]
        """Executa o command etl_professores com os argumentos fornecidos."""
        from django.core.management import call_command

        call_command("etl_professores", *(args or []))

    @patch(
        "apps.professores.management.commands.etl_professores.EtlProfessoresService"
    )
    def test_cria_execucao_e_finaliza_com_sucesso(
        self, mock_servico: MagicMock
    ) -> None:
        """Verifica que o command cria e finaliza execução com sucesso."""
        mock_servico.return_value.executar.return_value = _RESULTADO_MOCK
        mock_servico.return_value.ultima_fase_concluida = 4

        self._executar()

        execucao = EtlExecucao.objects.get(dominio="professores")
        self.assertEqual(execucao.situacao, "concluido")
        self.assertIsNotNone(execucao.finalizado_em)

    @patch(
        "apps.professores.management.commands.etl_professores.EtlProfessoresService"
    )
    def test_cria_checkpoint_apos_sucesso(
        self, mock_servico: MagicMock
    ) -> None:
        """Verifica que o command cria checkpoint após exec bem-sucedida."""
        mock_servico.return_value.executar.return_value = _RESULTADO_MOCK
        mock_servico.return_value.ultima_fase_concluida = 4

        self._executar()

        checkpoint = EtlCheckpointDominio.objects.get(dominio="professores")
        self.assertEqual(checkpoint.ultima_situacao, "concluido")
        self.assertEqual(checkpoint.ultima_pagina, 4)
        total = sum(_RESULTADO_MOCK.values())
        self.assertEqual(checkpoint.token_parada, str(total))

    @patch(
        "apps.professores.management.commands.etl_professores.EtlProfessoresService"
    )
    def test_token_acumula_entre_execucoes(
        self, mock_servico: MagicMock
    ) -> None:
        """Token de parada acumula entre execuções consecutivas."""
        mock_servico.return_value.executar.return_value = {"professor": 100}
        mock_servico.return_value.ultima_fase_concluida = 4

        self._executar()
        self._executar(["--continuar"])

        checkpoint = EtlCheckpointDominio.objects.get(dominio="professores")
        self.assertEqual(checkpoint.token_parada, "200")

    @patch(
        "apps.professores.management.commands.etl_professores.EtlProfessoresService"
    )
    def test_erro_persiste_checkpoint_com_situacao_erro(
        self, mock_servico: MagicMock
    ) -> None:
        """Checkpoint é persistido com situacao erro após falha."""
        mock_servico.return_value.executar.side_effect = RuntimeError(
            "conexão falhou"
        )
        mock_servico.return_value.ultima_fase_concluida = 1

        with self.assertRaises(RuntimeError):
            self._executar()

        execucao = EtlExecucao.objects.get(dominio="professores")
        self.assertEqual(execucao.situacao, "erro")
        self.assertIn("conexão falhou", execucao.mensagem_erro)

        checkpoint = EtlCheckpointDominio.objects.get(dominio="professores")
        self.assertEqual(checkpoint.ultima_situacao, "erro")
        self.assertEqual(checkpoint.ultima_pagina, 1)

    @patch(
        "apps.professores.management.commands.etl_professores.EtlProfessoresService"
    )
    def test_continuar_apos_erro_retoma_fase_seguinte(
        self, mock_servico: MagicMock
    ) -> None:
        """Ao usar --continuar, retoma execução da fase seguinte após erro."""
        mock_servico.return_value.executar.side_effect = RuntimeError(
            "erro fase 2"
        )
        mock_servico.return_value.ultima_fase_concluida = 1
        with self.assertRaises(RuntimeError):
            self._executar()

        mock_servico.return_value.executar.side_effect = None
        mock_servico.return_value.executar.return_value = {"professor": 50}
        mock_servico.return_value.ultima_fase_concluida = 4
        self._executar(["--continuar"])

        _, kwargs = mock_servico.return_value.executar.call_args
        self.assertEqual(kwargs.get("fase_inicial", 1), 2)

    @patch(
        "apps.professores.management.commands.etl_professores.EtlProfessoresService"
    )
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

    @patch(
        "apps.professores.management.commands.etl_professores.EtlProfessoresService"
    )
    def test_callbacks_salvam_checkpoint_parcial(
        self, mock_servico: MagicMock
    ) -> None:
        """Callbacks de lote e tabela persistem indice parcial."""

        def executar_com_callbacks(**kwargs: object) -> dict[str, int]:
            kwargs["on_lote"]("professor", 2)  # type: ignore[index,operator]
            kwargs["on_tabela_concluida"]("professor", 10)  # type: ignore[index,operator]
            return {"professor": 10}

        mock_servico.return_value.executar.side_effect = executar_com_callbacks
        mock_servico.return_value.ultima_fase_concluida = 1

        self._executar()

        checkpoint = EtlCheckpointDominio.objects.get(dominio="professores")
        self.assertEqual(checkpoint.ultima_situacao, "concluido")
        self.assertIsNone(checkpoint.indice_sincronizacao)

    def test_obter_contexto_sem_checkpoint_reinicia(self) -> None:
        """Sem checkpoint, --continuar inicia do zero."""
        repositorio = MagicMock()
        repositorio.obter_checkpoint_dominio.return_value = None

        contexto = Command()._obter_contexto_retomada(True, repositorio)

        self.assertEqual(contexto, (1, None, 0, 0))

    def test_calcular_pulo_sem_indice_reinicia_fase(self) -> None:
        """Indice vazio retoma a fase sem pular tabela."""
        pular_ate, lote_inicial = Command()._calcular_pulo_e_lote("", 2)

        self.assertIsNone(pular_ate)
        self.assertEqual(lote_inicial, 0)

    def test_calcular_pulo_por_tabela_concluida(self) -> None:
        """Indice de tabela concluida pula ate essa tabela."""
        pular_ate, lote_inicial = Command()._calcular_pulo_e_lote(
            "professor", 2
        )

        self.assertEqual(pular_ate, "professor")
        self.assertEqual(lote_inicial, 0)

    def test_calcular_pulo_por_lote_de_upsert(self) -> None:
        """Indice tabela:lote retoma no lote salvo para tabela upsert."""
        pular_ate, lote_inicial = Command()._calcular_pulo_e_lote(
            "professor:3", 1
        )

        self.assertIsNone(pular_ate)
        self.assertEqual(lote_inicial, 3)

    def test_calcular_pulo_por_lote_full_refresh_ignora_lote(self) -> None:
        """Tabelas full-refresh retomam pelo inicio da tabela."""
        pular_ate, lote_inicial = Command()._calcular_pulo_e_lote(
            "lotacao_servidor:4", 3
        )

        self.assertEqual(pular_ate, "contrato_externo")
        self.assertEqual(lote_inicial, 0)

    def test_funcionario_na_ordem_e_upsert(self) -> None:
        """Funcionario participa da ordem de carga e usa upsert."""
        self.assertIn("funcionario_unidade_educacional", _ORDEM_TABELAS)
        self.assertIn(
            "funcionario_unidade_educacional", _TABELAS_UPSERT
        )
