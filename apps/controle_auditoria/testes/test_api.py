"""Testes dos endpoints e autenticacao da API de controle_auditoria."""

from typing import Any
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.controle_auditoria.api.authentication import ApiKeyAuthentication
from apps.controle_auditoria.models import EtlCheckpointDominio, EtlExecucao


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
        """POST sem data agenda em execução imediata (delay)."""
        tarefa_mock.delay.return_value = type("Result", (), {"id": "task-1"})()
        resposta = self.client.post(
            "/api/v1/dominios/escola/executar/",
            data={"volume": 10, "offset": 1, "continuar": True},
            format="json",
            **self.headers,
        )
        self.assertEqual(resposta.status_code, 202)
        self.assertEqual(resposta.json()["task_id"], "task-1")
        tarefa_mock.delay.assert_called_once_with(
            dominio="escola",
            volume=10,
            offset=1,
            continuar=True,
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
        tarefa_mock.delay.assert_not_called()

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
