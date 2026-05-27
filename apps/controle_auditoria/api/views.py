"""Views DRF para controle e auditoria de execuções ETL."""

from typing import Any

from django.core.exceptions import ValidationError
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
from apps.controle_auditoria.libs.dominios import validar_parametros_dominio
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
_LIMITE_EXECUCOES_KANBAN = 100


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
            "Retorna as 50 execuções ETL mais recentes "
            "ordenadas por data de início."
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
        queryset = EtlExecucaoTabelaEscrita.objects.all().order_by(
            "-escrito_em"
        )[:_LIMITE_EXECUCOES_RECENTES]
        serializer = EtlExecucaoTabelaEscritaSerializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Domínios"])
class ExecutarDominioView(APIView):
    """Dispara execução de domínio ETL."""

    @extend_schema(
        summary="Disparar execução de domínio",
        description=(
            "Agenda ou executa imediatamente a sincronização de um "
            "domínio ETL. Se `executar_em` for informado, a task é "
            "agendada para aquela data/hora (ISO 8601). Caso contrário, "
            "executa imediatamente via Celery."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "volume": {
                        "type": "integer",
                        "default": 100,
                    },
                    "offset": {
                        "type": "integer",
                        "default": 0,
                    },
                    "continuar": {
                        "type": "boolean",
                        "default": False,
                    },
                    "prioridade": {
                        "type": "integer",
                        "default": 5,
                        "description": "0 = mais urgente, 9 = menos urgente.",
                    },
                    "executar_em": {
                        "type": "string",
                        "format": "date-time",
                        "description": (
                            "Agenda a execução para esta data/hora (ISO 8601)."
                        ),
                    },
                    "ano_letivo": {
                        "type": "integer",
                        "nullable": True,
                        "x-nullable": True,
                        "description": (
                            "Opcional. Quando informado, processa apenas "
                            "anos letivos a partir deste valor (inclusive)."
                            " Aplicável aos domínios alunos e pedagógico."
                        ),
                        "example": None,
                    },
                    "fases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "nullable": True,
                        "x-nullable": True,
                        "description": (
                            "Opcional. Lista de nomes de fases a executar. "
                            "Os nomes variam por domínio. Quando omitido, "
                            "todas as fases são executadas."
                        ),
                        "example": None,
                    },
                },
            }
        },
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
        ano_letivo = request.data.get("ano_letivo")
        fases = request.data.get("fases")

        erro_parametros = validar_parametros_dominio(
            dominio,
            ano_letivo=int(ano_letivo) if ano_letivo is not None else None,
            fases=list(fases) if fases is not None else None,
        )
        if erro_parametros:
            return Response(
                {"erro": erro_parametros},
                status=status.HTTP_400_BAD_REQUEST,
            )

        kwargs_task: dict[str, Any] = {
            "dominio": dominio,
            "volume": volume,
            "offset": offset,
            "continuar": continuar,
        }
        if ano_letivo is not None:
            kwargs_task["ano_letivo"] = int(ano_letivo)
        if fases is not None:
            kwargs_task["fases"] = list(fases)

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

        return Response(
            {"task_id": resultado.id}, status=status.HTTP_202_ACCEPTED
        )


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
            OpenApiParameter(
                "dominio", str, description="Filtra pelo domínio ETL"
            ),
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
                description=(
                    "Situação da execução (ex: concluido, erro, em_andamento)"
                ),
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
            "Endpoint público. Retorna a execução mais recente de cada "
            "domínio ETL, útil para visualizar rapidamente o estado "
            "atual de cada pipeline."
        ),
        responses={200: EtlExecucaoSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Retorna a última execução de cada domínio."""
        serializer = EtlExecucaoSerializer(
            _qs_ultima_execucao_por_dominio(), many=True
        )
        return Response(serializer.data)


class DashboardView(View):
    """Dashboard público de monitoramento das execuções ETL."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Renderiza o dashboard com resumo por domínio."""
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
        tabelas_map = _agregar_tabelas_escritas(ids_ultimas_10)
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


def _agregar_tabelas_lidas(ids_execucao: list) -> dict[str, list]:
    """Agrega linhas lidas por tabela_origem."""
    agg: dict[str, dict[str, dict]] = {}
    for tl in EtlExecucaoTabelaLida.objects.filter(
        id_execucao__in=ids_execucao
    ).order_by("tabela_origem"):
        key = str(tl.id_execucao)
        bucket = agg.setdefault(key, {})
        tabela = tl.tabela_origem
        if tabela not in bucket:
            bucket[tabela] = {
                "tabela_origem": tabela,
                "linhas_lidas": 0,
                "num_paginas": 0,
            }
        bucket[tabela]["linhas_lidas"] += tl.linhas_lidas
        bucket[tabela]["num_paginas"] += 1
    return {
        key: sorted(tabelas.values(), key=lambda x: x["tabela_origem"])
        for key, tabelas in agg.items()
    }


def _agregar_tabelas_escritas(ids_execucao: list) -> dict[str, list]:
    """Mantém a escrita mais recente por tabela_destino."""
    agg: dict[str, dict[str, dict]] = {}
    for te in EtlExecucaoTabelaEscrita.objects.filter(
        id_execucao__in=ids_execucao
    ).order_by("tabela_destino", "-escrito_em"):
        key = str(te.id_execucao)
        bucket = agg.setdefault(key, {})
        tabela = te.tabela_destino
        if tabela not in bucket:
            bucket[tabela] = {
                "tabela_destino": tabela,
                "linhas_escritas": 0,
                "modo_escrita": te.modo_escrita,
            }
            bucket[tabela]["linhas_escritas"] = te.linhas_escritas
    return {
        key: sorted(tabelas.values(), key=lambda x: x["tabela_destino"])
        for key, tabelas in agg.items()
    }


def _resolver_execucoes_kanban(
    qs_base: QuerySet,
    id_execucao_filtro: str,
    dominio_filtro: str,
    execucoes_disponiveis: list,
) -> tuple[list, str]:
    """Resolve execuções a renderizar no kanban."""
    if not id_execucao_filtro:
        ultima = list(_qs_ultima_execucao_por_dominio())
        if dominio_filtro:
            ultima = [e for e in ultima if e.dominio == dominio_filtro]
        return ultima, "Nenhuma execução encontrada."

    try:
        selecionada = qs_base.get(id_execucao=id_execucao_filtro)
    except (EtlExecucao.DoesNotExist, ValidationError, ValueError):
        selecionada = None

    if selecionada is None:
        return [], "Execução não encontrada para os filtros aplicados."

    if not any(
        e.id_execucao == selecionada.id_execucao for e in execucoes_disponiveis
    ):
        execucoes_disponiveis.insert(0, selecionada)
    return [selecionada], "Nenhuma execução encontrada."


class KanbanView(View):
    """Kanban de processamento ETL por domínio."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Renderiza kanban com estágios de leitura, hash e escrita."""
        dominio_filtro = request.GET.get("dominio", "")
        id_execucao_filtro = request.GET.get("id_execucao", "").strip()

        qs_execucoes_select = EtlExecucao.objects.all()
        if dominio_filtro:
            qs_execucoes_select = qs_execucoes_select.filter(
                dominio=dominio_filtro
            )

        execucoes_disponiveis = list(
            qs_execucoes_select.order_by("-iniciado_em")[
                :_LIMITE_EXECUCOES_KANBAN
            ]
        )

        ultima_por_dominio, mensagem_kanban_vazio = _resolver_execucoes_kanban(
            qs_execucoes_select,
            id_execucao_filtro,
            dominio_filtro,
            execucoes_disponiveis,
        )

        checkpoints = {
            c.dominio: c for c in EtlCheckpointDominio.objects.all()
        }
        ids_execucao = [e.id_execucao for e in ultima_por_dominio]

        lidas_map = _agregar_tabelas_lidas(ids_execucao)
        escritas_map = _agregar_tabelas_escritas(ids_execucao)

        tabelas_unicas = {
            te["tabela_destino"]
            for lista in escritas_map.values()
            for te in lista
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
            cp_da_execucao = bool(
                cp and str(cp.ultimo_id_execucao) == str(exec_obj.id_execucao)
            )
            dominios_kanban.append(
                {
                    "exec": exec_obj,
                    "checkpoint": cp,
                    "checkpoint_da_execucao": cp_da_execucao,
                    "tabelas_lidas": tabelas_lidas,
                    "tabelas_escritas": tabelas_escritas,
                    "total_lido": sum(
                        t["linhas_lidas"] for t in tabelas_lidas
                    ),
                    "total_escrito": sum(
                        t["linhas_escritas"] for t in tabelas_escritas
                    ),
                    "hash_por_tabela": {
                        te["tabela_destino"]: hash_por_tabela.get(
                            te["tabela_destino"], 0
                        )
                        for te in tabelas_escritas
                    },
                    "total_hashes": sum(
                        hash_por_tabela.get(te["tabela_destino"], 0)
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
                "id_execucao_filtro": id_execucao_filtro,
                "execucoes_disponiveis": execucoes_disponiveis,
                "todos_dominios": todos_dominios,
                "mensagem_kanban_vazio": mensagem_kanban_vazio,
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
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            return {"status": "healthy"}

        except Exception:
            return {"status": "unhealthy"}
