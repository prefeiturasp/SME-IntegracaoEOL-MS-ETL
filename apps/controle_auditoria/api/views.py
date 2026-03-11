"""Views DRF para controle e auditoria de execuções ETL."""

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.controle_auditoria.api.serializers import (
    EtlCheckpointDominioSerializer,
    EtlExecucaoSerializer,
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
    """Endpoint para disparar execução manual de um domínio ETL."""

    def post(self, request: Request) -> Response:
        """Executa um domínio ETL manualmente via task assíncrona."""
        dominio: str | None = request.data.get("dominio")

        if not dominio:
            return Response(
                {"erro": "Parametro 'dominio' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        executar_dominio_task.delay(dominio)

        return Response(
            {"mensagem": f"Execução do domínio '{dominio}' iniciada."},
            status=status.HTTP_202_ACCEPTED,
        )
