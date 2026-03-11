"""Testes dos modulos de biblioteca do app controle_auditoria."""

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID

from django.test import TestCase

from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)
from apps.controle_auditoria.libs.tasks import executar_dominio_task, verificar_saude
from apps.controle_auditoria.models import EtlCheckpointDominio


class RepositorioAuditoriaTestCase(TestCase):
    """Valida comportamentos do repositorio de auditoria."""

    def setUp(self) -> None:
        """Configura repositorio de auditoria."""
        self.repositorio = RepositorioAuditoriaPostgres()

    def test_deve_iniciar_e_finalizar_execucao(self) -> None:
        """Cria uma execucao e finaliza com sucesso."""
        id_execucao = self.repositorio.iniciar_execucao("escola")
        self.assertIsInstance(id_execucao, UUID)

        self.repositorio.finalizar_execucao(id_execucao, "sucesso")
        checkpoint = self.repositorio.obter_checkpoint_dominio("escola")
        self.assertIsNone(checkpoint)

    def test_deve_registrar_tabela_lida(self) -> None:
        """Registra leitura sem erro no banco de auditoria."""
        id_execucao = self.repositorio.iniciar_execucao("escola")
        self.repositorio.registrar_tabela_lida(
            id_execucao=id_execucao,
            tabela_origem="dbo.v_cadastro_unidade_educacao",
            numero_pagina=1,
            linhas_lidas=50,
        )

    def test_deve_registrar_tabela_escrita(self) -> None:
        """Registra escrita sem erro no banco de auditoria."""
        id_execucao = self.repositorio.iniciar_execucao("escola")
        self.repositorio.registrar_tabela_escrita(
            id_execucao=id_execucao,
            tabela_destino="console.saida_validacao_escolas",
            linhas_escritas=10,
            modo_escrita="validacao",
        )

    def test_deve_criar_checkpoint_no_primeiro_upsert(self) -> None:
        """Cria checkpoint quando dominio ainda nao existe."""
        id_execucao = self.repositorio.iniciar_execucao("escola")
        self.repositorio.atualizar_checkpoint_dominio(
            dominio="escola",
            ultimo_id_execucao=id_execucao,
            ultima_pagina=1,
            token_parada="100",
            indice_sincronizacao="escola:offset:100",
            ultima_situacao="sucesso",
            sucesso=True,
        )
        salvo = EtlCheckpointDominio.objects.get(dominio="escola")
        self.assertEqual(salvo.ultima_pagina, 1)
        self.assertEqual(salvo.token_parada, "100")
        self.assertEqual(salvo.ultima_situacao, "sucesso")
        self.assertIsNotNone(salvo.ultimo_sucesso_em)

    def test_deve_atualizar_checkpoint_existente_com_falha(self) -> None:
        """Atualiza checkpoint sem sobrescrever sucesso em caso de falha."""
        id_1 = self.repositorio.iniciar_execucao("escola")
        self.repositorio.atualizar_checkpoint_dominio(
            dominio="escola",
            ultimo_id_execucao=id_1,
            ultima_pagina=1,
            token_parada="100",
            indice_sincronizacao="escola:offset:100",
            ultima_situacao="sucesso",
            sucesso=True,
        )
        sucesso_em_anterior = EtlCheckpointDominio.objects.get(
            dominio="escola"
        ).ultimo_sucesso_em

        id_2 = self.repositorio.iniciar_execucao("escola")
        self.repositorio.atualizar_checkpoint_dominio(
            dominio="escola",
            ultimo_id_execucao=id_2,
            ultima_pagina=2,
            token_parada="200",
            indice_sincronizacao="escola:offset:200",
            ultima_situacao="falha",
            sucesso=False,
        )

        atualizado = EtlCheckpointDominio.objects.get(dominio="escola")
        self.assertEqual(atualizado.ultima_pagina, 2)
        self.assertEqual(atualizado.token_parada, "200")
        self.assertEqual(atualizado.ultima_situacao, "falha")
        self.assertEqual(atualizado.ultimo_sucesso_em, sucesso_em_anterior)


class ServicoSincRecDbTestCase(TestCase):
    """Valida servico de verificacao de tabelas esperadas."""

    @patch("apps.controle_auditoria.libs.servico_sinc_rec_db.connection")
    @patch("builtins.print")
    def test_deve_exibir_tabelas_intersecao(
        self, print_mock: Any, connection_mock: Any
    ) -> None:
        """Imprime somente tabelas esperadas encontradas."""
        connection_mock.introspection.table_names.return_value = [
            "etl_execucao",
            "etl_execucao_tabela_lida",
            "tabela_ignorada",
        ]
        from apps.controle_auditoria.libs.servico_sinc_rec_db import (
            exibir_validacao_sinc_rec_db,
        )

        exibir_validacao_sinc_rec_db()
        self.assertGreaterEqual(print_mock.call_count, 3)


class TasksControleAuditoriaTestCase(TestCase):
    """Valida tasks celery do dominio."""

    def test_verificar_saude(self) -> None:
        """Task de saude retorna ok."""
        self.assertEqual(verificar_saude(), "ok")

    @patch("apps.controle_auditoria.libs.tasks.call_command")
    @patch("apps.controle_auditoria.libs.tasks.RepositorioAuditoriaPostgres")
    def test_executar_dominio_task_sem_continuar(
        self,
        repositorio_cls_mock: Any,
        call_command_mock: Any,
    ) -> None:
        """Task executa até o final e força continuidade após primeira página."""
        repositorio = MagicMock()
        repositorio.obter_checkpoint_dominio.side_effect = [
            {"token_parada": "0"},
            {"token_parada": "120"},
            {"token_parada": "120"},
            {"token_parada": "150"},
        ]
        repositorio_cls_mock.return_value = repositorio

        retorno = executar_dominio_task(
            dominio="escola",
            volume=120,
            offset=10,
            continuar=False,
        )

        self.assertEqual(retorno, "ok:150")
        self.assertEqual(call_command_mock.call_count, 2)
        self.assertEqual(
            call_command_mock.call_args_list[0].args,
            (
                "executar_dominio",
                "--dominio",
                "escola",
                "--volume",
                "120",
                "--offset",
                "10",
            ),
        )
        self.assertEqual(
            call_command_mock.call_args_list[1].args,
            (
                "executar_dominio",
                "--dominio",
                "escola",
                "--volume",
                "120",
                "--offset",
                "10",
                "--continuar",
            ),
        )

    @patch("apps.controle_auditoria.libs.tasks.call_command")
    @patch("apps.controle_auditoria.libs.tasks.RepositorioAuditoriaPostgres")
    def test_executar_dominio_task_com_continuar(
        self,
        repositorio_cls_mock: Any,
        call_command_mock: Any,
    ) -> None:
        """Task respeita flag continuar na primeira chamada."""
        repositorio = MagicMock()
        repositorio.obter_checkpoint_dominio.side_effect = [
            {"token_parada": "10"},
            {"token_parada": "50"},
        ]
        repositorio_cls_mock.return_value = repositorio

        retorno = executar_dominio_task(
            dominio="escola",
            volume=90,
            offset=0,
            continuar=True,
        )

        self.assertEqual(retorno, "ok:40")
        call_command_mock.assert_called_once_with(
            "executar_dominio",
            "--dominio",
            "escola",
            "--volume",
            "90",
            "--offset",
            "0",
            "--continuar",
        )
