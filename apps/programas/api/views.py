"""Views da API de Programas."""

import os

from django.db import connections
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.serializers import HealthStatusSerializer


class HealthProgramasView(APIView):
    """Verifica a saúde do domínio Programas."""

    serializer_class = HealthStatusSerializer

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        resultado = self._check_database()

        status_http = 200 if resultado["status"] == "healthy" else 503
        serializer = HealthStatusSerializer(resultado)
        return Response(serializer.data, status=status_http)

    def _check_database(self) -> dict[str, str]:
        """Verifica se o banco PROGRAMAS_DB responde a um SELECT 1."""
        if not os.getenv("URL_BANCO_PROGRAMAS"):
            return {"status": "unhealthy"}

        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            return {"status": "healthy"}

        except Exception:
            return {"status": "unhealthy"}
