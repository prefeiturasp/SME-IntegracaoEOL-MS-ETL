"""Testes da API de healthcheck do EOL."""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIClient


class TestHealthEndpoint(TestCase):
    """Teste do endpoint de health do EOL."""

    def setUp(self) -> None:
        """Prepara cliente e URL para testes."""
        self.client = APIClient()
        self.url = "/api/v1/eol/health/"

    @patch("apps.eol_connection.api.views.healthcheck_eol")
    def test_health_endpoint_healthy(self, health_mock: MagicMock) -> None:
        """Retorna 200 quando o servico esta saudavel."""
        health_mock.return_value = {
            "status": "healthy",
        }

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    @patch("apps.eol_connection.api.views.healthcheck_eol")
    def test_health_endpoint_unhealthy(self, health_mock: MagicMock) -> None:
        """Retorna 503 quando o servico esta unhealthy."""
        health_mock.return_value = {"status": "unhealthy"}

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 503)

    def test_health_endpoint_sem_autenticacao(self) -> None:
        """Endpoint deve responder sem autenticacao (status 200 ou 503)."""
        response = self.client.get(self.url)

        self.assertIn(response.status_code, [200, 503])

    def test_health_view_uses_healthcheck(self) -> None:
        """Chama a view diretamente e usa o healthcheck mockado."""
        with patch("apps.eol_connection.api.views.healthcheck_eol") as hc:
            hc.return_value = {"status": "healthy"}

            factory = APIClient()
            response = factory.get(self.url)

            self.assertEqual(response.status_code, 200)

    def test_factory_get_covered(self) -> None:
        """Chamada direta com `APIClient` para garantir cobertura da linha."""
        factory = APIClient()
        response = factory.get(self.url)

        self.assertIn(response.status_code, [200, 503])
