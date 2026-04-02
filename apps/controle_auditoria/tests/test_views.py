"""Testes das views da API de controle_auditoria."""

import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from apps.controle_auditoria.models import (
    EtlCheckpointDominio,
    EtlExecucao,
)

_API_KEY = "chave-teste-123"
_AUTH_HEADER = {"HTTP_X_API_KEY": _API_KEY}


def _setup_api_key(settings) -> None:  # type: ignore[no-untyped-def]
    settings.API_KEY = _API_KEY
    settings.API_KEY_HEADER = "X-API-Key"


class AutenticacaoTest(TestCase):
    """Testes de autenticação via API key nas views."""

    def test_sem_chave_retorna_403(self) -> None:
        """Verifica que requisição sem API key retorna 403."""
        url = reverse("checkpoints")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_chave_errada_retorna_403(self) -> None:
        """Verifica que requisição com API key incorreta retorna 403."""
        url = reverse("checkpoints")
        resp = self.client.get(url, HTTP_X_API_KEY="chave-errada")
        self.assertEqual(resp.status_code, 403)


class CheckpointsViewTest(TestCase):
    """Testes da view de listagem de checkpoints."""

    def setUp(self) -> None:
        """Configura a API key nas settings para os testes."""
        from django.conf import settings

        _setup_api_key(settings)

    def test_lista_vazia(self) -> None:
        """Verifica que a listagem retorna lista vazia quando não há checkpoints."""
        url = reverse("checkpoints")
        resp = self.client.get(url, **_AUTH_HEADER)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_lista_checkpoints_existentes(self) -> None:
        """Verifica que a listagem retorna os checkpoints existentes."""
        EtlCheckpointDominio.objects.create(
            dominio="professores",
            ultima_situacao="concluido",
        )
        url = reverse("checkpoints")
        resp = self.client.get(url, **_AUTH_HEADER)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["dominio"], "professores")


class ExecucoesViewTest(TestCase):
    """Testes da view de listagem de execuções."""

    def setUp(self) -> None:
        """Configura a API key nas settings para os testes."""
        from django.conf import settings

        _setup_api_key(settings)

    def test_lista_vazia(self) -> None:
        """Verifica que a listagem retorna lista vazia quando não há execuções."""
        url = reverse("execucoes")
        resp = self.client.get(url, **_AUTH_HEADER)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_lista_execucoes_ordenadas_por_data(self) -> None:
        """Verifica que as execuções são retornadas ordenadas pela data mais recente."""
        from django.utils import timezone

        EtlExecucao.objects.create(
            id_execucao=uuid.uuid4(),
            dominio="professores",
            situacao="concluido",
            iniciado_em=timezone.now(),
        )
        t2 = EtlExecucao.objects.create(
            id_execucao=uuid.uuid4(),
            dominio="institucional",
            situacao="erro",
            iniciado_em=timezone.now(),
        )
        url = reverse("execucoes")
        resp = self.client.get(url, **_AUTH_HEADER)
        self.assertEqual(resp.status_code, 200)
        ids_retornados = [e["id_execucao"] for e in resp.json()]
        # mais recente primeiro
        self.assertEqual(ids_retornados[0], str(t2.id_execucao))


class ExecutarDominioViewTest(TestCase):
    """Testes da view de disparo de execução de domínio."""

    def setUp(self) -> None:
        """Configura a API key nas settings para os testes."""
        from django.conf import settings

        _setup_api_key(settings)

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_dispara_task_e_retorna_202(self, mock_task: MagicMock) -> None:
        """Verifica que a view dispara a task e retorna 202 com o task_id."""
        task_mock = MagicMock()
        task_mock.id = "uuid-fake-123"
        mock_task.apply_async.return_value = task_mock

        url = reverse("executar-dominio", kwargs={"dominio": "professores"})
        resp = self.client.post(
            url,
            data={"volume": 200, "continuar": False},
            content_type="application/json",
            **_AUTH_HEADER,
        )
        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.json()["task_id"], "uuid-fake-123")
        mock_task.apply_async.assert_called_once()

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_prioridade_e_passada_ao_apply_async(self, mock_task: MagicMock) -> None:
        """Verifica que a prioridade informada é repassada ao apply_async."""
        task_mock = MagicMock()
        task_mock.id = "uuid-fake-456"
        mock_task.apply_async.return_value = task_mock

        url = reverse("executar-dominio", kwargs={"dominio": "professores"})
        resp = self.client.post(
            url,
            data={"prioridade": 2},
            content_type="application/json",
            **_AUTH_HEADER,
        )
        self.assertEqual(resp.status_code, 202)
        _, kwargs = mock_task.apply_async.call_args
        self.assertEqual(kwargs["priority"], 2)

    @patch("apps.controle_auditoria.api.views.executar_dominio_task")
    def test_data_invalida_retorna_400(self, mock_task: MagicMock) -> None:
        """Verifica que dados inválidos no payload retornam 400 sem disparar a task."""
        url = reverse("executar-dominio", kwargs={"dominio": "professores"})
        resp = self.client.post(
            url,
            data={"executar_em": "data-invalida"},
            content_type="application/json",
            **_AUTH_HEADER,
        )
        self.assertEqual(resp.status_code, 400)
        mock_task.apply_async.assert_not_called()


class MonitoramentoPublicoTest(TestCase):
    """Endpoints públicos não exigem autenticação."""

    def test_monitoramento_execucoes_sem_auth(self) -> None:
        """Endpoint de monitoramento de execuções sem autenticação."""
        url = reverse("monitoramento-execucoes")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_monitoramento_resumo_sem_auth(self) -> None:
        """Endpoint de resumo de monitoramento sem autenticação."""
        url = reverse("monitoramento-resumo")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_filtro_por_dominio(self) -> None:
        """Filtro por domínio retorna apenas execuções do domínio informado."""
        from django.utils import timezone

        EtlExecucao.objects.create(
            id_execucao=uuid.uuid4(),
            dominio="professores",
            situacao="concluido",
            iniciado_em=timezone.now(),
        )
        EtlExecucao.objects.create(
            id_execucao=uuid.uuid4(),
            dominio="institucional",
            situacao="concluido",
            iniciado_em=timezone.now(),
        )
        url = reverse("monitoramento-execucoes")
        resp = self.client.get(url, {"dominio": "professores"})
        self.assertEqual(resp.status_code, 200)
        dominios = [e["dominio"] for e in resp.json()]
        self.assertTrue(all(d == "professores" for d in dominios))
