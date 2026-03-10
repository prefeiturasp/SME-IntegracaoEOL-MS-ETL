"""Views DRF para controle e auditoria."""

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.controle_auditoria.api.serializers import (
    EtlCheckpointDominioSerializer,
    EtlExecucaoSerializer,
)
from apps.controle_auditoria.libs.tasks import executar_dominio_task
from apps.controle_auditoria.models import EtlCheckpointDominio, EtlExecucao


class CheckpointsView(APIView):
    """Lista checkpoints por dominio."""

    def get(self, request):
        queryset = EtlCheckpointDominio.objects.all().order_by("dominio")
        serializer = EtlCheckpointDominioSerializer(queryset, many=True)
        return Response(serializer.data)


class ExecucoesView(APIView):
    """Lista execucoes recentes do ETL."""

    def get(self, request):
        queryset = EtlExecucao.objects.all().order_by("-iniciado_em")[:50]
        serializer = EtlExecucaoSerializer(queryset, many=True)
        return Response(serializer.data)


class ExecutarDominioView(APIView):
    """Registra execucao de dominio na fila Celery."""

    def post(self, request, dominio: str):
        volume = int(request.data.get("volume", 100))
        offset = int(request.data.get("offset", 0))
        valor_continuar = request.data.get("continuar", False)
        continuar = str(valor_continuar).lower() in {"1", "true", "sim"}
        executar_em = request.data.get("executar_em")

        kwargs_tarefa = {
            "dominio": dominio,
            "volume": volume,
            "offset": offset,
            "continuar": continuar,
        }
        agendado_para = None
        if executar_em:
            data_hora = parse_datetime(str(executar_em))
            if data_hora is None:
                return Response(
                    {"erro": "formato invalido para executar_em"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if timezone.is_naive(data_hora):
                data_hora = timezone.make_aware(
                    data_hora,
                    timezone.get_current_timezone(),
                )
            agendado_para = data_hora.isoformat()
            resultado = executar_dominio_task.apply_async(
                kwargs=kwargs_tarefa,
                eta=data_hora,
            )
        else:
            resultado = executar_dominio_task.delay(**kwargs_tarefa)

        return Response(
            {
                "mensagem": "execucao registrada na fila",
                "dominio": dominio,
                "volume": volume,
                "offset": offset,
                "continuar": continuar,
                "task_id": resultado.id,
                "agendado_para": agendado_para,
            },
            status=status.HTTP_202_ACCEPTED,
        )
