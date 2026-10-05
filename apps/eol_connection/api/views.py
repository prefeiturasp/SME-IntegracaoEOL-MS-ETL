"""Views da API de `eol_connection`."""

from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.serializers import HealthStatusSerializer
from apps.eol_connection.libs.healthcheck import healthcheck_eol


class HealthCheckEOLView(APIView):
    """Healthcheck do servico EOL."""

    serializer_class = HealthStatusSerializer

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        """Retorna o status de saude do servico EOL."""
        resultado = healthcheck_eol()

        serializer = HealthStatusSerializer(resultado)

        status_http = 200
        if resultado.get("status") == "unhealthy":
            status_http = 503

        return Response(serializer.data, status=status_http)
