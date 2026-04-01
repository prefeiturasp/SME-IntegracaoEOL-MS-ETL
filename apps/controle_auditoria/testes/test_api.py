"""Testes dos endpoints e autenticacao da API de controle_auditoria."""

import os
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from django.test import Client, TestCase, override_settings
from django.utils import timezone
from django.utils.timezone import localtime
from rest_framework.test import APIClient

from apps.controle_auditoria.api.authentication import ApiKeyAuthentication
from apps.controle_auditoria.models import (
    EtlCheckpointDominio,
    EtlExecucao,
    EtlExecucaoTabelaEscrita,
    EtlExecucaoTabelaLida,
)


class ApiKeyAuthenticationTestCase(TestCase):
    """Valida autenticação por API key."""

    def setUp(self) -> None:
        """Configura autenticação."""
        self.authentication = ApiKeyAuthentication()

    @override_settings(API_KEY="")
    def test_deve_falhar_sem_api_key_configurada(self) -> None:
        """Falha quando API key esperada não está configurada."""
        request = type("Request", (), {"headers": {}})()
        with self.assertRaisesMessage(Exception, "API key nao configurada"):
            self.authentication.authenticate(request)

    @override_settings(API_KEY="segredo")
    def test_deve_retornar_none_sem_header(self) -> None:
        """Sem header de chave, autenticação retorna None."""
        request = type("Request", (), {"headers": {}})()
        self.assertIsNone(self.authentication.authenticate(request))

    @override_settings(API_KEY="segredo")
    def test_deve_falhar_com_header_invalido(self) -> None:
        """Com chave inválida, autenticação falha."""
        request = type(
            "Request",
            (),
            {"headers": {"X-API-Key": "invalida"}},
        )()
        with self.assertRaisesMessage(Exception, "API key invalida"):
            self.authentication.authenticate(request)

    @override_settings(API_KEY="segredo")
    def test_deve_autenticar_com_header_valido(self) -> None:
        """Com chave válida, autenticação retorna usuário autenticado."""
        request = type(
            "Request",
            (),
            {"headers": {"X-API-Key": "segredo"}},
        )()
        resultado = self.authentication.authenticate(request)
        assert resultado is not None

        usuario, _ = resultado
        self.assertTrue(usuario.is_authenticated)


@override_settings(API_KEY="segredo")
class ViewsApiControleAuditoriaTestCase(TestCase):
    """Valida endpoints DRF de checkpoints, execuções e disparo."""

    def setUp(self) -> None:
        """Configura client e headers de autenticação."""
        self.client = APIClient()
        self.headers = {"HTTP_X_API_KEY": "segredo"}

    def test_deve_listar_checkpoints(self) -> None:
        """Retorna lista de checkpoints."""
        EtlCheckpointDominio.objects.create(
            dominio="escola",
            ultimo_id_execucao=uuid4(),
            ultima_pagina=2,
            token_parada="200",
            indice_sincronizacao="escola:offset:200",
            ultima_situacao="sucesso",
        )

        resposta = self.client.get("/api/v1/checkpoints/", **self.headers)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 1)

    def test_deve_listar_execucoes(self) -> None:
        """Retorna execuções mais recentes."""
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="escola",
            situacao="sucesso",
            iniciado_em=timezone.now(),
        )

        resposta = self.client.get("/api/v1/execucoes/", **self.headers)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 1)

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_enfileirar_execucao_imediata(self, tarefa_mock: Any) -> None:
        """POST sem data agenda em execução imediata (apply_async sem eta)."""
        tarefa_mock.apply_async.return_value = type("Result", (), {"id": "task-1"})()
        resposta = self.client.post(
            "/api/v1/dominios/escola/executar/",
            data={"volume": 10, "offset": 1, "continuar": True},
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 202)
        self.assertEqual(resposta.json()["task_id"], "task-1")
        tarefa_mock.apply_async.assert_called_once_with(
            kwargs={"dominio": "escola", "volume": 10, "offset": 1, "continuar": True},
            priority=5,
        )

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_agendar_execucao_com_data_hora(self, tarefa_mock: Any) -> None:
        """POST com executar_em usa apply_async com eta."""
        tarefa_mock.apply_async.return_value = type(
            "Result",
            (),
            {"id": "task-2"},
        )()
        resposta = self.client.post(
            "/api/v1/dominios/escola/executar/",
            data={
                "volume": 20,
                "offset": 2,
                "continuar": False,
                "executar_em": "2026-03-10T23:00:00-03:00",
            },
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 202)
        self.assertEqual(resposta.json()["task_id"], "task-2")
        self.assertTrue(tarefa_mock.apply_async.called)

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_deve_rejeitar_data_hora_invalida(self, tarefa_mock: Any) -> None:
        """Retorna 400 quando executar_em está inválido."""
        resposta = self.client.post(
            "/api/v1/dominios/escola/executar/",
            data={"executar_em": "nao-e-data"},
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("erro", resposta.json())
        tarefa_mock.apply_async.assert_not_called()

    def test_docs_e_schema_devem_ser_publicos(self) -> None:
        """Swagger e schema devem responder sem autenticação."""
        schema = self.client.get("/api/v1/schema/")
        docs = self.client.get("/api/v1/docs/")
        self.assertEqual(schema.status_code, 200)
        self.assertEqual(docs.status_code, 200)

    def test_endpoints_protegidos_sem_api_key(self) -> None:
        """Sem API key, endpoints da API devem negar acesso."""
        resposta = self.client.get("/api/v1/checkpoints/")
        self.assertEqual(resposta.status_code, 403)

    def test_deve_retornar_detalhe_de_execucao_com_tabelas(self) -> None:
        """Retorna execução com tabelas lidas e escritas aninhadas."""
        id_exec = uuid4()
        EtlExecucao.objects.create(
            id_execucao=id_exec,
            dominio="escola",
            situacao="sucesso",
            iniciado_em=timezone.now(),
        )
        EtlExecucaoTabelaLida.objects.create(
            id_execucao=id_exec,
            tabela_origem="dbo.v_cadastro",
            numero_pagina=1,
            linhas_lidas=100,
        )
        EtlExecucaoTabelaEscrita.objects.create(
            id_execucao=id_exec,
            tabela_destino="escolas",
            linhas_escritas=100,
            modo_escrita="upsert",
        )

        resposta = self.client.get(f"/api/v1/execucoes/{id_exec}/", **self.headers)
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(dados["id_execucao"], str(id_exec))
        self.assertEqual(len(dados["tabelas_lidas"]), 1)
        self.assertEqual(len(dados["tabelas_escritas"]), 1)
        self.assertEqual(dados["tabelas_lidas"][0]["tabela_origem"], "dbo.v_cadastro")
        self.assertEqual(dados["tabelas_escritas"][0]["tabela_destino"], "escolas")

    def test_deve_retornar_404_para_execucao_inexistente(self) -> None:
        """Retorna 404 quando id_execucao não existe."""
        resposta = self.client.get(f"/api/v1/execucoes/{uuid4()}/", **self.headers)
        self.assertEqual(resposta.status_code, 404)
        self.assertIn("erro", resposta.json())

    def test_deve_listar_tabelas_lidas(self) -> None:
        """Retorna registros de tabelas lidas."""
        EtlExecucaoTabelaLida.objects.create(
            id_execucao=uuid4(),
            tabela_origem="dbo.v_cadastro",
            numero_pagina=1,
            linhas_lidas=50,
        )

        resposta = self.client.get("/api/v1/execucoes/tabelas-lidas/", **self.headers)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 1)

    def test_deve_listar_tabelas_escritas(self) -> None:
        """Retorna registros de tabelas escritas."""
        EtlExecucaoTabelaEscrita.objects.create(
            id_execucao=uuid4(),
            tabela_destino="escolas",
            linhas_escritas=50,
            modo_escrita="upsert",
        )

        resposta = self.client.get(
            "/api/v1/execucoes/tabelas-escritas/", **self.headers
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 1)


class MonitoramentoViewsTestCase(TestCase):
    """Valida endpoints públicos de monitoramento."""

    def setUp(self) -> None:
        """Cria execuções de teste."""
        self.client = APIClient()
        self.id_exec_a = uuid4()
        self.id_exec_b = uuid4()
        EtlExecucao.objects.create(
            id_execucao=self.id_exec_a,
            dominio="escola",
            situacao="sucesso",
            iniciado_em=timezone.now(),
        )
        EtlExecucao.objects.create(
            id_execucao=self.id_exec_b,
            dominio="sinc_rec_db",
            situacao="erro",
            iniciado_em=timezone.now(),
        )

    def test_monitoramento_deve_listar_execucoes_sem_auth(self) -> None:
        """Endpoint de monitoramento retorna execuções sem autenticação."""
        resposta = self.client.get("/api/v1/monitoramento/execucoes/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 2)

    def test_monitoramento_deve_filtrar_por_dominio(self) -> None:
        """Filtro por dominio retorna apenas execuções do domínio."""
        resposta = self.client.get("/api/v1/monitoramento/execucoes/?dominio=escola")
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["dominio"], "escola")

    def test_monitoramento_deve_filtrar_por_situacao(self) -> None:
        """Filtro por situacao retorna apenas execuções com aquela situação."""
        resposta = self.client.get("/api/v1/monitoramento/execucoes/?situacao=erro")
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["situacao"], "erro")

    def test_monitoramento_deve_filtrar_por_data_inicio(self) -> None:
        """Filtro por data_inicio retorna execuções a partir daquela data."""
        hoje = localtime(timezone.now()).date().isoformat()
        resposta = self.client.get(
            f"/api/v1/monitoramento/execucoes/?data_inicio={hoje}"
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 2)

    def test_monitoramento_deve_filtrar_por_data_fim(self) -> None:
        """Filtro por data_fim retorna execuções até aquela data."""
        hoje = timezone.now().date().isoformat()
        resposta = self.client.get(f"/api/v1/monitoramento/execucoes/?data_fim={hoje}")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 2)

    def test_monitoramento_deve_retornar_resumo_por_dominio(self) -> None:
        """Resumo retorna a última execução de cada domínio."""
        resposta = self.client.get("/api/v1/monitoramento/resumo/")
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        dominios = [d["dominio"] for d in dados]
        self.assertIn("escola", dominios)
        self.assertIn("sinc_rec_db", dominios)

    def test_monitoramento_resumo_retorna_apenas_ultima_por_dominio(self) -> None:
        """Resumo retorna somente 1 entrada por domínio."""
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="escola",
            situacao="erro",
            iniciado_em=timezone.now(),
        )
        resposta = self.client.get("/api/v1/monitoramento/resumo/")
        self.assertEqual(resposta.status_code, 200)
        dominios = [d["dominio"] for d in resposta.json()]
        self.assertEqual(dominios.count("escola"), 1)


class DashboardViewTestCase(TestCase):
    """Valida o dashboard público."""

    def setUp(self) -> None:
        """Cria execuções para o dashboard."""
        self.client = Client()
        EtlExecucao.objects.create(
            id_execucao=uuid4(),
            dominio="escola",
            situacao="sucesso",
            iniciado_em=timezone.now(),
        )

    def test_dashboard_deve_responder_sem_auth(self) -> None:
        """Dashboard retorna 200 sem autenticação."""
        resposta = self.client.get("/dashboard/")
        self.assertEqual(resposta.status_code, 200)

    def test_dashboard_deve_responder_com_filtro_dominio(self) -> None:
        """Dashboard com filtro de domínio retorna 200."""
        resposta = self.client.get("/dashboard/?dominio=escola")
        self.assertEqual(resposta.status_code, 200)

    def test_dashboard_deve_responder_com_filtro_situacao(self) -> None:
        """Dashboard com filtro de situação retorna 200."""
        resposta = self.client.get("/dashboard/?situacao=sucesso")
        self.assertEqual(resposta.status_code, 200)

    def test_dashboard_deve_responder_com_todos_os_filtros(self) -> None:
        """Dashboard com todos os filtros combinados retorna 200."""
        hoje = timezone.now().date().isoformat()
        resposta = self.client.get(
            f"/dashboard/?dominio=escola&situacao=sucesso"
            f"&data_inicio={hoje}&data_fim={hoje}"
        )
        self.assertEqual(resposta.status_code, 200)

    def test_dashboard_sem_execucoes(self) -> None:
        """Dashboard responde 200 mesmo sem execuções registradas."""
        EtlExecucao.objects.all().delete()
        resposta = self.client.get("/dashboard/")
        self.assertEqual(resposta.status_code, 200)


class HealthSincRecViewTestCase(TestCase):
    """Testes para endpoints do HealthSincRecView."""

    def setUp(self) -> None:
        """Prepara cliente API para testes."""
        self.client = APIClient()

    def test_health_banco_ok(self) -> None:
        """Retorna 200 quando banco esta acessivel."""
        response = self.client.get("/api/v1/sinc_rec/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    @patch("apps.controle_auditoria.api.views.connections")
    def test_health_banco_erro(self, connections_mock: Any) -> None:
        """Retorna 503 quando banco lança excecao."""
        connections_mock.__getitem__.return_value.cursor.side_effect = Exception()

        response = self.client.get("/api/v1/sinc_rec/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unhealthy")
