"""Views DRF para controle e auditoria de execuções ETL."""

import os

from django.db import connections
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.controle_auditoria.api.serializers import (
    EtlCheckpointDominioSerializer,
    EtlExecucaoSerializer,
    HealthStatusSerializer,
)
from apps.controle_auditoria.libs.tasks import executar_dominio_task
from apps.controle_auditoria.models import EtlCheckpointDominio, EtlExecucao


class CheckpointsView(APIView):
    """Endpoint para listagem de checkpoints de execução ETL por domínio."""

    def get(self, request: Request) -> Response:
        """Retorna a lista de checkpoints registrados para cada domínio."""
        queryset = EtlCheckpointDominio.objects.all().order_by("dominio")

        serializer = EtlCheckpointDominioSerializer(queryset, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class ExecucoesView(APIView):
    """Lista execucoes recentes do ETL."""

    def get(self, request: Request) -> Response:
        """Retorna execuções mais recentes."""
        queryset = EtlExecucao.objects.all().order_by("-iniciado_em")[:50]
        serializer = EtlExecucaoSerializer(queryset, many=True)
        return Response(serializer.data)


class ExecutarDominioView(APIView):
    """Dispara execução de domínio ETL."""

    def post(self, request: Request, dominio: str) -> Response:
        """POST sem data agenda em execução imediata (delay)."""
        volume = request.data.get("volume", 100)
        offset = request.data.get("offset", 0)
        continuar = request.data.get("continuar", False)
        executar_em = request.data.get("executar_em")

        if executar_em:
            eta = parse_datetime(executar_em)
            if eta is None:
                return Response({"erro": "data inválida"}, status=400)

            resultado = executar_dominio_task.apply_async(
                kwargs={
                    "dominio": dominio,
                    "volume": volume,
                    "offset": offset,
                    "continuar": continuar,
                },
                eta=eta,
            )
        else:
            resultado = executar_dominio_task.delay(
                dominio=dominio,
                volume=volume,
                offset=offset,
                continuar=continuar,
            )

        return Response({"task_id": resultado.id}, status=202)


class HealthSincRecView(APIView):
    """Health do dominio SincRec."""

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        """Retorna o status de saude do dominio SincRec."""
        resultado = self._check_database()

        status_http = 200 if resultado["status"] == "healthy" else 503
        serializer = HealthStatusSerializer(resultado)
        return Response(serializer.data, status=status_http)

    def _check_database(self) -> dict[str, str]:
        if not os.getenv("URL_BANCO_AUDITORIA"):
            return {"status": "unhealthy"}

        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            return {"status": "healthy"}

        except Exception:
            return {"status": "unhealthy"}
