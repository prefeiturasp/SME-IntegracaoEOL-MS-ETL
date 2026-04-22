"""Testes da API de programas."""

import os
from typing import Any
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient


class HealthProgramasViewTestCase(TestCase):
    """Testes para endpoints do HealthProgramasView."""

    def setUp(self) -> None:
        """Prepara cliente API para testes."""
        self.client = APIClient()

    @patch.dict(os.environ, {}, clear=True)
    def test_health_sem_variavel(self) -> None:
        """Sem URL_BANCO_PROGRAMAS deve retornar unhealthy."""
        response = self.client.get("/api/v1/programas/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unhealthy")

    @patch.dict(os.environ, {"URL_BANCO_PROGRAMAS": "postgres://teste"})
    def test_health_banco_ok(self) -> None:
        """Banco respondendo retorna healthy."""
        response = self.client.get("/api/v1/programas/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    @patch.dict(os.environ, {"URL_BANCO_PROGRAMAS": "postgres://teste"})
    @patch("apps.programas.api.views.connections")
    def test_health_banco_erro(self, connections_mock: Any) -> None:
        """Erro no banco retorna unhealthy."""
        connections_mock.__getitem__.return_value.cursor.side_effect = (
            Exception()
        )

        response = self.client.get("/api/v1/programas/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unhealthy")
