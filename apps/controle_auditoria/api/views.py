"""Views DRF para controle e auditoria de execuções ETL."""

import os

from django.db import connections
from django.db.models import OuterRef, QuerySet, Subquery
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.dateparse import parse_datetime
from django.views import View
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.controle_auditoria.api.serializers import (
    EtlCheckpointDominioSerializer,
    EtlExecucaoDetalheSerializer,
    EtlExecucaoSerializer,
    EtlExecucaoTabelaEscritaSerializer,
    EtlExecucaoTabelaLidaSerializer,
    HealthStatusSerializer,
)
from apps.controle_auditoria.libs.tasks import executar_dominio_task
from apps.controle_auditoria.models import (
    EtlAuditoriaLinha,
    EtlCheckpointDominio,
    EtlExecucao,
    EtlExecucaoTabelaEscrita,
    EtlExecucaoTabelaLida,
)

_LIMITE_EXECUCOES_RECENTES = 50
_LIMITE_MONITORAMENTO = 100


def _qs_ultima_execucao_por_dominio() -> QuerySet:
    """Retorna queryset com a última execução de cada domínio."""
    return EtlExecucao.objects.filter(
        iniciado_em=Subquery(
            EtlExecucao.objects.filter(dominio=OuterRef("dominio"))
            .order_by("-iniciado_em")
            .values("iniciado_em")[:1]
        )
    ).order_by("dominio")


def _aplicar_filtros_execucao(
    qs: QuerySet,
    dominio: str,
    data_inicio: str,
    data_fim: str,
    situacao: str,
) -> QuerySet:
    """Aplica filtros opcionais a um queryset de EtlExecucao."""
    if dominio:
        qs = qs.filter(dominio=dominio)
    if data_inicio:
        qs = qs.filter(iniciado_em__date__gte=data_inicio)
    if data_fim:
        qs = qs.filter(iniciado_em__date__lte=data_fim)
    if situacao:
        qs = qs.filter(situacao=situacao)
    return qs


@extend_schema(tags=["Checkpoints"])
class CheckpointsView(APIView):
    """Endpoint para listagem de checkpoints de execução ETL por domínio."""

    @extend_schema(
        summary="Lista checkpoints por domínio",
        description=(
            "Retorna o estado atual de cada domínio ETL: última execução, "
            "última página processada, token de parada e situação."
        ),
        responses={200: EtlCheckpointDominioSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Retorna a lista de checkpoints registrados para cada domínio."""
        queryset = EtlCheckpointDominio.objects.all().order_by("dominio")
        serializer = EtlCheckpointDominioSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Execuções"])
class ExecucoesView(APIView):
    """Lista execucoes recentes do ETL."""

    @extend_schema(
        summary="Lista execuções recentes",
        description=(
            "Retorna as 50 execuções ETL mais recentes ordenadas por data de início."
        ),
        responses={200: EtlExecucaoSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Retorna execuções mais recentes."""
        queryset = EtlExecucao.objects.all().order_by("-iniciado_em")[
            :_LIMITE_EXECUCOES_RECENTES
        ]
        serializer = EtlExecucaoSerializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Execuções"])
class ExecucaoDetalheView(APIView):
    """Detalhe de uma execução com tabelas lidas e escritas relacionadas."""

    @extend_schema(
        summary="Detalhe de execução com tabelas relacionadas",
        description=(
            "Retorna os dados de uma execução ETL identificada pelo "
            "`id_execucao` (UUID), incluindo as tabelas lidas "
            "(EtlExecucaoTabelaLida) e escritas (EtlExecucaoTabelaEscrita) "
            "associadas ao mesmo `id_execucao`."
        ),
        responses={200: EtlExecucaoDetalheSerializer, 404: None},
    )
    def get(self, request: Request, id_execucao: str) -> Response:
        """Retorna execução com tabelas lidas e escritas aninhadas."""
        try:
            execucao = EtlExecucao.objects.get(id_execucao=id_execucao)
        except EtlExecucao.DoesNotExist:
            return Response(
                {"erro": "execução não encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EtlExecucaoDetalheSerializer(execucao)
        return Response(serializer.data)


@extend_schema(tags=["Execuções"])
class ExecucoesTabelaLidaView(APIView):
    """Lista registros de leitura por execucao ETL."""

    @extend_schema(
        summary="Lista tabelas lidas",
        description=(
            "Retorna os 50 registros mais recentes de tabelas lidas "
            "durante execuções ETL. "
            "O campo `id_execucao` referencia `EtlExecucao.id_execucao`."
        ),
        responses={200: EtlExecucaoTabelaLidaSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Retorna registros de tabelas lidas nas execuções."""
        queryset = EtlExecucaoTabelaLida.objects.all().order_by("-lido_em")[
            :_LIMITE_EXECUCOES_RECENTES
        ]
        serializer = EtlExecucaoTabelaLidaSerializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Execuções"])
class ExecucoesTabelaEscritaView(APIView):
    """Lista registros de escrita por execucao ETL."""

    @extend_schema(
        summary="Lista tabelas escritas",
        description=(
            "Retorna os 50 registros mais recentes de tabelas escritas "
            "durante execuções ETL. "
            "O campo `id_execucao` referencia `EtlExecucao.id_execucao`."
        ),
        responses={200: EtlExecucaoTabelaEscritaSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Retorna registros de tabelas escritas nas execuções."""
        queryset = EtlExecucaoTabelaEscrita.objects.all().order_by("-escrito_em")[
            :_LIMITE_EXECUCOES_RECENTES
        ]
        serializer = EtlExecucaoTabelaEscritaSerializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Domínios"])
class ExecutarDominioView(APIView):
    """Dispara execução de domínio ETL."""

    @extend_schema(
        summary="Disparar execução de domínio",
        description=(
            "Agenda ou executa imediatamente a sincronização de um domínio ETL. "
            "Se `executar_em` for informado, a task é agendada para aquela "
            "data/hora (ISO 8601). Caso contrário, executa imediatamente via Celery."
        ),
        responses={
            202: {
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
            }
        },
    )
    def post(self, request: Request, dominio: str) -> Response:
        """POST sem data agenda em execução imediata (delay)."""
        volume = request.data.get("volume", 100)
        offset = request.data.get("offset", 0)
        continuar = request.data.get("continuar", False)
        executar_em = request.data.get("executar_em")
        # Prioridade: 0 = mais urgente, 9 = menos urgente (padrão: 5)
        prioridade = int(request.data.get("prioridade", 5))

        kwargs_task = {
            "dominio": dominio,
            "volume": volume,
            "offset": offset,
            "continuar": continuar,
        }

        if executar_em:
            eta = parse_datetime(executar_em)
            if eta is None:
                return Response(
                    {"erro": "data inválida"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            resultado = executar_dominio_task.apply_async(
                kwargs=kwargs_task,
                eta=eta,
                priority=prioridade,
            )
        else:
            resultado = executar_dominio_task.apply_async(
                kwargs=kwargs_task,
                priority=prioridade,
            )

        return Response({"task_id": resultado.id}, status=status.HTTP_202_ACCEPTED)


@extend_schema(tags=["Monitoramento"])
class MonitoramentoExecucoesView(APIView):
    """Monitoramento público de execuções com filtros."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Lista execuções com filtros",
        description=(
            "Endpoint público para monitoramento de execuções ETL. "
            "Suporta filtro por domínio, data de início/fim e situação."
        ),
        parameters=[
            OpenApiParameter("dominio", str, description="Filtra pelo domínio ETL"),
            OpenApiParameter(
                "data_inicio",
                str,
                description="Data inicial no formato YYYY-MM-DD",
            ),
            OpenApiParameter(
                "data_fim",
                str,
                description="Data final no formato YYYY-MM-DD",
            ),
            OpenApiParameter(
                "situacao",
                str,
                description="Situação da execução (ex: concluido, erro, em_andamento)",
            ),
        ],
        responses={200: EtlExecucaoSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Retorna execuções filtradas por domínio, data e situação."""
        qs = _aplicar_filtros_execucao(
            qs=EtlExecucao.objects.all(),
            dominio=request.query_params.get("dominio", ""),
            data_inicio=request.query_params.get("data_inicio", ""),
            data_fim=request.query_params.get("data_fim", ""),
            situacao=request.query_params.get("situacao", ""),
        )
        serializer = EtlExecucaoSerializer(
            qs.order_by("-iniciado_em")[:_LIMITE_MONITORAMENTO], many=True
        )
        return Response(serializer.data)


@extend_schema(tags=["Monitoramento"])
class MonitoramentoResumoView(APIView):
    """Resumo público com a última execução por domínio."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Última execução por domínio",
        description=(
            "Endpoint público. Retorna a execução mais recente de cada domínio ETL, "
            "útil para visualizar rapidamente o estado atual de cada pipeline."
        ),
        responses={200: EtlExecucaoSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Retorna a última execução de cada domínio."""
        serializer = EtlExecucaoSerializer(_qs_ultima_execucao_por_dominio(), many=True)
        return Response(serializer.data)


class DashboardView(View):
    """Dashboard público de monitoramento das execuções ETL."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Renderiza o dashboard com resumo por domínio e execuções recentes."""
        dominio = request.GET.get("dominio", "")
        data_inicio = request.GET.get("data_inicio", "")
        data_fim = request.GET.get("data_fim", "")
        situacao = request.GET.get("situacao", "")

        # Total de registros processados por domínio via checkpoint
        checkpoints = {
            c.dominio: int(c.token_parada or 0)
            for c in EtlCheckpointDominio.objects.all()
        }
        ultima_por_dominio = list(_qs_ultima_execucao_por_dominio())
        for exec_obj in ultima_por_dominio:
            exec_obj.total_processado = checkpoints.get(exec_obj.dominio, 0)

        qs_filtrado = _aplicar_filtros_execucao(
            qs=EtlExecucao.objects.all(),
            dominio=dominio,
            data_inicio=data_inicio,
            data_fim=data_fim,
            situacao=situacao,
        ).order_by("-iniciado_em")

        execucoes = qs_filtrado[:_LIMITE_MONITORAMENTO]

        # Últimas 10 execuções com detalhes de tabelas escritas
        ultimas_10 = list(qs_filtrado[:10])
        ids_ultimas_10 = [e.id_execucao for e in ultimas_10]
        tabelas_map: dict[str, list] = {}
        for te in EtlExecucaoTabelaEscrita.objects.filter(
            id_execucao__in=ids_ultimas_10
        ).order_by("tabela_destino"):
            tabelas_map.setdefault(str(te.id_execucao), []).append(te)
        ultimas_10_com_tabelas = [
            {"exec": e, "tabelas": tabelas_map.get(str(e.id_execucao), [])}
            for e in ultimas_10
        ]

        dominios_disponiveis = (
            EtlExecucao.objects.values_list("dominio", flat=True)
            .distinct()
            .order_by("dominio")
        )
        situacoes_disponiveis = (
            EtlExecucao.objects.values_list("situacao", flat=True)
            .distinct()
            .order_by("situacao")
        )

        return render(
            request,
            "dashboard.html",
            {
                "ultima_por_dominio": ultima_por_dominio,
                "execucoes": execucoes,
                "ultimas_10": ultimas_10_com_tabelas,
                "dominios": dominios_disponiveis,
                "situacoes": situacoes_disponiveis,
                "filtros": {
                    "dominio": dominio,
                    "data_inicio": data_inicio,
                    "data_fim": data_fim,
                    "situacao": situacao,
                },
            },
        )


class KanbanView(View):
    """Kanban de processamento ETL por domínio."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Renderiza kanban com estágios de leitura, hash, escrita e checkpoint."""
        dominio_filtro = request.GET.get("dominio", "")

        ultima_por_dominio = list(_qs_ultima_execucao_por_dominio())
        if dominio_filtro:
            ultima_por_dominio = [
                e for e in ultima_por_dominio if e.dominio == dominio_filtro
            ]

        checkpoints = {c.dominio: c for c in EtlCheckpointDominio.objects.all()}

        ids_execucao = [e.id_execucao for e in ultima_por_dominio]

        lidas_map: dict[str, list] = {}
        for tl in EtlExecucaoTabelaLida.objects.filter(
            id_execucao__in=ids_execucao
        ).order_by("tabela_origem"):
            lidas_map.setdefault(str(tl.id_execucao), []).append(tl)

        escritas_map: dict[str, list] = {}
        for te in EtlExecucaoTabelaEscrita.objects.filter(
            id_execucao__in=ids_execucao
        ).order_by("tabela_destino"):
            escritas_map.setdefault(str(te.id_execucao), []).append(te)

        # Contagem de hashes por prefixo de tabela (tabela:id)
        tabelas_unicas = {
            te.tabela_destino for lista in escritas_map.values() for te in lista
        }
        hash_por_tabela: dict[str, int] = {
            tabela: EtlAuditoriaLinha.objects.filter(
                id_destino__startswith=f"{tabela}:"
            ).count()
            for tabela in tabelas_unicas
        }

        dominios_kanban = []
        for exec_obj in ultima_por_dominio:
            key = str(exec_obj.id_execucao)
            tabelas_lidas = lidas_map.get(key, [])
            tabelas_escritas = escritas_map.get(key, [])
            cp = checkpoints.get(exec_obj.dominio)

            dominios_kanban.append(
                {
                    "exec": exec_obj,
                    "checkpoint": cp,
                    "tabelas_lidas": tabelas_lidas,
                    "tabelas_escritas": tabelas_escritas,
                    "total_lido": sum(t.linhas_lidas for t in tabelas_lidas),
                    "total_escrito": sum(t.linhas_escritas for t in tabelas_escritas),
                    "hash_por_tabela": {
                        te.tabela_destino: hash_por_tabela.get(te.tabela_destino, 0)
                        for te in tabelas_escritas
                    },
                    "total_hashes": sum(
                        hash_por_tabela.get(te.tabela_destino, 0)
                        for te in tabelas_escritas
                    ),
                }
            )

        todos_dominios = list(
            EtlExecucao.objects.values_list("dominio", flat=True)
            .distinct()
            .order_by("dominio")
        )

        return render(
            request,
            "kanban.html",
            {
                "dominios_kanban": dominios_kanban,
                "dominio_filtro": dominio_filtro,
                "todos_dominios": todos_dominios,
            },
        )


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
        """Retorna se esta conectado ao banco de dados default."""
        if not os.environ.get("URL_BANCO_AUDITORIA"):
            return {"status": "unhealthy"}
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            return {"status": "healthy"}

        except Exception:
            return {"status": "unhealthy"}
