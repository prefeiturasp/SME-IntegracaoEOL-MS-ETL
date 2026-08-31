"""Testes dos modulos de biblioteca do app controle_auditoria."""

import json
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID

from django.test import TestCase

from apps.controle_auditoria.libs.celery_app import aplicacao_celery
from apps.controle_auditoria.libs.dominios import validar_parametros_dominio
from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)
from apps.controle_auditoria.libs.tasks import (
    executar_dominio_task,
    verificar_saude,
)
from apps.controle_auditoria.models import EtlCheckpointDominio


class RepositorioAuditoriaTestCase(TestCase):
    """Valida comportamentos do repositorio de auditoria."""

    def setUp(self) -> None:
        """Configura repositorio de auditoria."""
        self.repositorio = RepositorioAuditoriaPostgres()

    def test_deve_iniciar_e_finalizar_execucao(self) -> None:
        """Cria uma execucao e finaliza com sucesso."""
        id_execucao = self.repositorio.iniciar_execucao("institucional")
        self.assertIsInstance(id_execucao, UUID)

        self.repositorio.finalizar_execucao(id_execucao, "sucesso")
        checkpoint = self.repositorio.obter_checkpoint_dominio("institucional")
        self.assertIsNone(checkpoint)

    def test_deve_registrar_tabela_lida(self) -> None:
        """Registra leitura sem erro no banco de auditoria."""
        id_execucao = self.repositorio.iniciar_execucao("institucional")
        self.repositorio.registrar_tabela_lida(
            id_execucao=id_execucao,
            tabela_origem="dbo.v_cadastro_unidade_educacao",
            numero_pagina=1,
            linhas_lidas=50,
        )

    def test_deve_registrar_tabela_escrita(self) -> None:
        """Registra escrita sem erro no banco de auditoria."""
        id_execucao = self.repositorio.iniciar_execucao("institucional")
        self.repositorio.registrar_tabela_escrita(
            id_execucao=id_execucao,
            tabela_destino="console.saida_validacao_institucional",
            linhas_escritas=10,
            modo_escrita="validacao",
        )

    def test_deve_criar_checkpoint_no_primeiro_upsert(self) -> None:
        """Cria checkpoint quando dominio ainda nao existe."""
        id_execucao = self.repositorio.iniciar_execucao("institucional")
        self.repositorio.atualizar_checkpoint_dominio(
            dominio="institucional",
            ultimo_id_execucao=id_execucao,
            ultima_pagina=1,
            token_parada="100",
            indice_sincronizacao="institucional:token:100",
            ultima_situacao="sucesso",
            sucesso=True,
        )
        salvo = EtlCheckpointDominio.objects.get(dominio="institucional")
        self.assertEqual(salvo.ultima_pagina, 1)
        self.assertEqual(salvo.token_parada, "100")
        self.assertEqual(salvo.ultima_situacao, "sucesso")
        self.assertIsNotNone(salvo.ultimo_sucesso_em)

    def test_deve_atualizar_checkpoint_existente_com_falha(self) -> None:
        """Atualiza checkpoint sem sobrescrever sucesso em caso de falha."""
        id_1 = self.repositorio.iniciar_execucao("institucional")
        self.repositorio.atualizar_checkpoint_dominio(
            dominio="institucional",
            ultimo_id_execucao=id_1,
            ultima_pagina=1,
            token_parada="100",
            indice_sincronizacao="institucional:token:100",
            ultima_situacao="sucesso",
            sucesso=True,
        )
        sucesso_em_anterior = EtlCheckpointDominio.objects.get(
            dominio="institucional"
        ).ultimo_sucesso_em

        id_2 = self.repositorio.iniciar_execucao("institucional")
        self.repositorio.atualizar_checkpoint_dominio(
            dominio="institucional",
            ultimo_id_execucao=id_2,
            ultima_pagina=2,
            token_parada="200",
            indice_sincronizacao="institucional:token:200",
            ultima_situacao="falha",
            sucesso=False,
        )

        atualizado = EtlCheckpointDominio.objects.get(dominio="institucional")
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


class DominiosTestCase(TestCase):
    """Valida regras de parâmetros por domínio."""

    def test_rejeita_ano_letivo_legado(self) -> None:
        """Contrato atual não aceita parâmetro singular de ano letivo."""
        self.assertIsNotNone(
            validar_parametros_dominio("alunos", ano_letivo=2024)
        )

    def test_alunos_aceita_anos_letivos(self) -> None:
        """Domínio alunos aceita lista de anos letivos."""
        self.assertIsNone(
            validar_parametros_dominio(
                "alunos", anos_letivos=[2021, 2022, 2023, 2024, 2025]
            )
        )

    def test_pedagogico_aceita_anos_letivos(self) -> None:
        """Domínio pedagógico aceita lista de anos letivos."""
        self.assertIsNone(
            validar_parametros_dominio("pedagogico", anos_letivos=[2024])
        )

    def test_professores_aceita_anos_letivos(self) -> None:
        """Domínio professores aceita lista de anos letivos."""
        self.assertIsNone(
            validar_parametros_dominio("professores", anos_letivos=[2024])
        )

    def test_programas_aceita_anos_letivos(self) -> None:
        """Domínio programas aceita lista de anos letivos."""
        self.assertIsNone(
            validar_parametros_dominio("programas", anos_letivos=[2024])
        )


class TasksControleAuditoriaTestCase(TestCase):
    """Valida tasks celery do dominio."""

    def test_verificar_saude(self) -> None:
        """Task de saude retorna ok."""
        self.assertEqual(verificar_saude(), "ok")

    def test_executar_dominio_task_com_continuar_possui_max_retries(
        self,
    ) -> None:
        """Task configurada para retry automático em falhas transientes."""
        self.assertEqual(executar_dominio_task.max_retries, 5)

    @patch("apps.controle_auditoria.libs.tasks.call_command")
    @patch("apps.controle_auditoria.libs.tasks.RepositorioAuditoriaPostgres")
    def test_executar_dominio_task_sem_continuar(
        self,
        repositorio_cls_mock: Any,
        call_command_mock: Any,
    ) -> None:
        """Task executa domínio uma vez e contabiliza avanço do token."""
        repositorio = MagicMock()
        repositorio.obter_checkpoint_dominio.side_effect = [
            {"token_parada": "0"},
            {"token_parada": "120"},
        ]
        repositorio_cls_mock.return_value = repositorio

        retorno = executar_dominio_task(dominio="institucional")

        self.assertEqual(retorno, "ok:120")
        self.assertEqual(call_command_mock.call_count, 1)
        primeira_chamada = call_command_mock.call_args_list[0].args
        self.assertEqual(
            primeira_chamada[:3],
            (
                "executar_dominio",
                "--dominio",
                "institucional",
            ),
        )
        self.assertIn("--parametros-disparo", primeira_chamada)
        indice_parametros = primeira_chamada.index("--parametros-disparo")
        parametros = json.loads(primeira_chamada[indice_parametros + 1])
        self.assertIn("celery_task_id", parametros)

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
            dominio="institucional", continuar=True
        )

        self.assertEqual(retorno, "ok:40")
        chamada = call_command_mock.call_args.args
        self.assertEqual(
            chamada[:4],
            (
                "executar_dominio",
                "--dominio",
                "institucional",
                "--continuar",
            ),
        )
        self.assertIn("--parametros-disparo", chamada)

    @patch("apps.controle_auditoria.libs.tasks.call_command")
    def test_executar_dominio_task_rejeita_parametro_sem_suporte(
        self,
        call_command_mock: Any,
    ) -> None:
        """Task rejeita parâmetros incompatíveis com o domínio."""
        retorno = executar_dominio_task(
            dominio="institucional",
            anos_letivos=[2025],
        )

        self.assertIn("erro:", retorno)
        self.assertIn("anos_letivos", retorno)
        call_command_mock.assert_not_called()


class CeleryBrokerResilienciaTestCase(TestCase):
    """Valida que a configuração do Celery tolera falhas no broker."""

    def test_broker_connection_retry_habilitado(self) -> None:
        """Worker reconecta automaticamente ao broker após falha."""
        self.assertTrue(aplicacao_celery.conf.broker_connection_retry)

    def test_broker_connection_retry_on_startup_habilitado(self) -> None:
        """Worker não falha se broker não estiver pronto."""
        self.assertTrue(
            aplicacao_celery.conf.broker_connection_retry_on_startup
        )

    def test_broker_connection_max_retries_configurado(self) -> None:
        """Limite de reconexão evita loop infinito."""
        self.assertEqual(
            aplicacao_celery.conf.broker_connection_max_retries, 10
        )
