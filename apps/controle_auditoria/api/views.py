"""Views DRF para controle e auditoria de execuções ETL."""

from typing import Any
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import connections
from django.db.models import OuterRef, QuerySet, Subquery
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
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
from apps.controle_auditoria.libs.celery_app import aplicacao_celery
from apps.controle_auditoria.libs.dominios import (
    FASES_COM_ANOS_LETIVOS,
    FASES_POR_DOMINIO,
    validar_parametros_dominio,
)
from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)
from apps.controle_auditoria.libs.tasks import executar_dominio_task
from apps.controle_auditoria.models import (
    EtlAuditoriaLinha,
    EtlCheckpointDominio,
    EtlExecucao,
    EtlExecucaoTabelaEscrita,
    EtlExecucaoTabelaLida,
    EtlProgressoExecucao,
)

_LIMITE_EXECUCOES_RECENTES = 50
_LIMITE_MONITORAMENTO = 100
_LIMITE_EXECUCOES_KANBAN = 100
_LIMITE_RECOVERY = 25
_MAX_TENTATIVAS_RECOVERY = 3
_STATUS_EM_EXECUCAO = frozenset({"em_execucao", "em_andamento"})


def _descricao_execucao_dominio() -> str:
    """Monta descrição do contrato de execução para o Swagger."""
    linhas = [
        "Agenda ou executa imediatamente a sincronização de um domínio ETL. "
        "Se `executar_em` for informado, a task é agendada para aquela "
        "data/hora (ISO 8601). Caso contrário, executa imediatamente via "
        "Celery.",
        "",
        "Use `anos_letivos` para restringir cargas por ano.",
        "",
        "Domínios e fases:",
    ]

    for dominio, fases in FASES_POR_DOMINIO.items():
        fases_ano = set(FASES_COM_ANOS_LETIVOS.get(dominio, ()))
        linhas.append(f"- `{dominio}`")
        linhas.append("  - fases:")
        for fase in fases:
            marcador = (
                " - aceita filtro por ano letivo" if fase in fases_ano else ""
            )
            linhas.append(f"    - `{fase}`{marcador}")

    return "\n".join(linhas)


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


def _formatar_duracao(segundos: int | float | None) -> str:
    """Formata duração curta para dashboard."""
    if segundos is None:
        return ""
    total = max(int(segundos), 0)
    horas, resto = divmod(total, 3600)
    minutos, segs = divmod(resto, 60)
    if horas:
        return f"{horas}h {minutos}min"
    if minutos:
        return f"{minutos}min {segs}s"
    return f"{segs}s"


def _segundos_entre(inicio: Any, fim: Any) -> int:
    """Calcula segundos entre duas datas."""
    if not inicio or not fim:
        return 0
    return max(int((fim - inicio).total_seconds()), 0)


def _percentual(parte: int | float, total: int | float) -> str:
    """Formata percentual com uma casa decimal."""
    if not total:
        return "0%"
    valor = (float(parte) / float(total)) * 100
    return f"{valor:.1f}%".replace(".", ",")


def _por_minuto(total: int | float, segundos: int) -> int:
    """Calcula taxa por minuto."""
    if segundos <= 0:
        return 0
    return int((float(total) / segundos) * 60)


def _enriquecer_progresso_item(
    progresso: dict[str, Any], execucao: EtlExecucao, agora: Any
) -> None:
    """Adiciona métricas derivadas ao item de progresso."""
    total_fases = int(progresso.get("total_fases") or 0)
    fase_numero = int(progresso.get("fase_numero") or 0)
    linhas_lidas = int(progresso.get("linhas_lidas") or 0)
    linhas_escritas = int(progresso.get("linhas_escritas") or 0)
    linhas_ignoradas = int(progresso.get("linhas_ignoradas") or 0)
    iniciado_em = progresso.get("iniciado_em")
    atualizado_em = progresso.get("atualizado_em")
    base_fim = atualizado_em or execucao.finalizado_em or agora
    segundos = _segundos_entre(execucao.iniciado_em, base_fim)
    segundos_fase = _segundos_entre(iniciado_em, base_fim)
    segundos_update = _segundos_entre(atualizado_em, agora)

    progresso["percentual_fase"] = _percentual(fase_numero, total_fases)
    progresso["atualizado_ha"] = _formatar_duracao(segundos_update)
    progresso["taxa_lidas_minuto"] = _por_minuto(linhas_lidas, segundos)
    progresso["duracao_fase_segundos"] = segundos_fase
    progresso["duracao_fase_label"] = _formatar_duracao(segundos_fase)
    progresso["taxa_fase_lidas_minuto"] = _por_minuto(
        linhas_lidas, segundos_fase
    )
    progresso["taxa_alteracao"] = _percentual(linhas_escritas, linhas_lidas)
    progresso["taxa_gravacao"] = progresso["taxa_alteracao"]
    progresso["taxa_ignoradas"] = _percentual(linhas_ignoradas, linhas_lidas)


def _enriquecer_execucao(
    execucao: EtlExecucao,
    progresso: list[dict[str, Any]],
    agora: Any,
) -> None:
    """Adiciona métricas derivadas usadas pelos templates."""
    fim = execucao.finalizado_em or agora
    segundos = _segundos_entre(execucao.iniciado_em, fim)
    execucao.duracao_label = _formatar_duracao(segundos)
    execucao.duracao_prefixo = (
        "rodando há" if execucao.situacao in _STATUS_EM_EXECUCAO else "duração"
    )
    for item in progresso:
        _enriquecer_progresso_item(item, execucao, agora)
    execucao.progresso_atual = progresso[-1] if progresso else None
    execucao.tempo_por_fase = sorted(
        progresso,
        key=lambda item: int(item.get("duracao_fase_segundos") or 0),
        reverse=True,
    )


def _parametros_execucao(execucao: EtlExecucao) -> dict[str, Any]:
    """Retorna parâmetros de execução gravados na auditoria."""
    parametros = execucao.parametros or {}
    if not isinstance(parametros, dict):
        return {}
    dados = parametros.get("execucao", {})
    return dados if isinstance(dados, dict) else {}


def _parametros_disparo(execucao: EtlExecucao) -> dict[str, Any]:
    """Retorna parâmetros de disparo gravados na auditoria."""
    parametros = execucao.parametros or {}
    if not isinstance(parametros, dict):
        return {}
    dados = parametros.get("disparo", {})
    return dados if isinstance(dados, dict) else {}


def _normalizar_lista(valor: Any, tipo: type = str) -> list | None:
    """Normaliza listas de parâmetros vindas da auditoria ou da request."""
    if valor in (None, "", []):
        return None
    if isinstance(valor, list | tuple):
        return [tipo(item) for item in valor]
    return [tipo(valor)]


def _id_origem_reprocessamento(execucao: EtlExecucao) -> str:
    """Resolve a execução raiz para contabilizar tentativas de recovery."""
    disparo = _parametros_disparo(execucao)
    return str(disparo.get("execucao_origem") or execucao.id_execucao)


def _contar_reprocessamentos(id_origem: str) -> int:
    """Conta quantas execuções já foram disparadas pelo recovery."""
    total: int = EtlExecucao.objects.filter(
        parametros__disparo__origem="recovery",
        parametros__disparo__execucao_origem=id_origem,
    ).count()
    return total


def _task_id_execucao(execucao: EtlExecucao) -> str:
    """Retorna o task_id Celery registrado na execução."""
    disparo = _parametros_disparo(execucao)
    return str(disparo.get("celery_task_id") or "")


def _coletar_ids_tasks(payload: Any) -> set[str]:
    """Coleta ids de tasks em respostas do Celery inspect."""
    ids: set[str] = set()
    if isinstance(payload, dict):
        for chave, valor in payload.items():
            if chave == "id" and valor:
                ids.add(str(valor))
            else:
                ids.update(_coletar_ids_tasks(valor))
    elif isinstance(payload, list):
        for item in payload:
            ids.update(_coletar_ids_tasks(item))
    return ids


def _ids_tasks_celery_vivas() -> tuple[set[str], bool]:
    """Retorna task_ids active/reserved/scheduled conhecidos pelo Celery."""
    try:
        inspetor = aplicacao_celery.control.inspect(timeout=1.0)
        payloads = [
            inspetor.active(),
            inspetor.reserved(),
            inspetor.scheduled(),
        ]
    except Exception:
        return set(), False

    if all(payload is None for payload in payloads):
        return set(), False

    ids: set[str] = set()
    for payload in payloads:
        ids.update(_coletar_ids_tasks(payload or {}))
    return ids, True


def _ultimo_heartbeat_execucao(execucao: EtlExecucao) -> Any:
    """Retorna último progresso da execução ou o início como fallback."""
    progresso = (
        EtlProgressoExecucao.objects.filter(id_execucao=execucao.id_execucao)
        .order_by("-atualizado_em")
        .values_list("atualizado_em", flat=True)
        .first()
    )
    return progresso or execucao.iniciado_em


def _novo_task_id() -> str:
    """Gera task_id rastreável antes de enfileirar no Celery."""
    return str(uuid4())


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

    @extend_schema(
        summary="Cancelar execução",
        description=(
            "Marca uma execução como cancelada. Útil para desbloquear "
            "execuções presas em 'em_execucao'. Retorna 409 se a execução "
            "já estiver finalizada (sucesso, erro ou cancelado)."
        ),
        responses={
            200: {
                "type": "object",
                "properties": {"cancelado": {"type": "string"}},
            },
            404: None,
            409: {
                "type": "object",
                "properties": {"erro": {"type": "string"}},
            },
        },
    )
    def delete(self, request: Request, id_execucao: str) -> Response:
        """Cancela execução em andamento pelo id_execucao."""
        try:
            execucao = EtlExecucao.objects.get(id_execucao=id_execucao)
        except EtlExecucao.DoesNotExist:
            return Response(
                {"erro": "execução não encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if execucao.situacao != "em_execucao":
            return Response(
                {
                    "erro": (
                        "execução já finalizada com situação "
                        f"'{execucao.situacao}'"
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        execucao.situacao = "cancelado"
        execucao.finalizado_em = timezone.now()
        execucao.mensagem_erro = "Cancelado manualmente via API"
        execucao.save(
            update_fields=["situacao", "finalizado_em", "mensagem_erro"]
        )
        return Response({"cancelado": str(execucao.id_execucao)})


@extend_schema(tags=["Execuções"])
class LimparOrfasView(APIView):
    """Marca execuções sem task viva como interrompidas."""

    @extend_schema(
        summary="Limpa execuções órfãs",
        description=(
            "Marca como `interrompido` execuções que continuam em "
            "`em_execucao`, mas não aparecem como tasks vivas no Celery "
            "em `active`, `reserved` ou `scheduled`."
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "tasks_vivas": {"type": "integer"},
                    "total_analisado": {"type": "integer"},
                    "total_interrompido": {"type": "integer"},
                    "total_preservado": {"type": "integer"},
                    "itens": {"type": "array", "items": {"type": "object"}},
                },
            }
        },
    )
    def post(self, request: Request) -> Response:
        """Interrompe execuções órfãs com base no estado do Celery."""
        execucoes = list(
            EtlExecucao.objects.filter(
                situacao__in=_STATUS_EM_EXECUCAO
            ).order_by("iniciado_em")
        )
        task_ids_vivos, celery_disponivel = _ids_tasks_celery_vivas()
        if not celery_disponivel:
            return Response(
                {
                    "erro": (
                        "Não foi possível consultar o estado dos workers "
                        "Celery. Nenhuma execução foi alterada."
                    ),
                    "total_analisado": len(execucoes),
                    "total_interrompido": 0,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        repositorio = RepositorioAuditoriaPostgres()
        itens = []
        for execucao in execucoes:
            task_id = _task_id_execucao(execucao)
            if task_id and task_id in task_ids_vivos:
                itens.append(
                    {
                        "dominio": execucao.dominio,
                        "id_execucao": str(execucao.id_execucao),
                        "heartbeat": None,
                        "task_id": task_id,
                        "status": "preservado",
                        "motivo": "task_celery_viva",
                    }
                )
                continue

            heartbeat = _ultimo_heartbeat_execucao(execucao)
            motivo = "task_celery_ausente" if task_id else "sem_task_id"
            agora = timezone.now()
            execucao.situacao = "interrompido"
            execucao.finalizado_em = agora
            execucao.mensagem_erro = (
                "Execução interrompida automaticamente: "
                "task Celery não encontrada em active, reserved ou scheduled."
            )
            execucao.save(
                update_fields=["situacao", "finalizado_em", "mensagem_erro"]
            )
            checkpoint_liberado = repositorio.marcar_checkpoint_interrompido(
                execucao.dominio
            )
            itens.append(
                {
                    "dominio": execucao.dominio,
                    "id_execucao": str(execucao.id_execucao),
                    "heartbeat": heartbeat.isoformat() if heartbeat else None,
                    "task_id": task_id or None,
                    "status": "interrompido",
                    "motivo": motivo,
                    "checkpoint_liberado": checkpoint_liberado,
                }
            )

        return Response(
            {
                "tasks_vivas": len(task_ids_vivos),
                "total_analisado": len(execucoes),
                "total_interrompido": sum(
                    1 for item in itens if item["status"] == "interrompido"
                ),
                "total_preservado": sum(
                    1 for item in itens if item["status"] == "preservado"
                ),
                "itens": itens,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Execuções"])
class ReprocessarErrosView(APIView):
    """Reprocessa execuções com erro de forma controlada."""

    @extend_schema(
        summary="Reprocessa últimas execuções com erro",
        description=(
            "Busca a última execução de cada domínio quando ela está em erro "
            "ou interrompida e agenda uma nova execução com `continuar=true`, "
            "reaproveitando os parâmetros rastreados na auditoria. Por padrão "
            "não reprocessa falhas antigas se já existir execução mais "
            "recente para o domínio."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "max_tentativas": {
                        "type": "integer",
                        "default": 3,
                        "description": (
                            "Quantidade máxima de reprocessamentos "
                            "automáticos por execução raiz."
                        ),
                    },
                },
            }
        },
        responses={
            202: {
                "type": "object",
                "properties": {
                    "total_analisado": {"type": "integer"},
                    "total_reprocessado": {"type": "integer"},
                    "itens": {"type": "array", "items": {"type": "object"}},
                },
            }
        },
    )
    def post(self, request: Request) -> Response:
        """Agenda recovery das últimas execuções com erro por domínio."""
        max_tentativas = int(
            request.data.get("max_tentativas", _MAX_TENTATIVAS_RECOVERY)
        )
        prioridade = 3
        limite = _LIMITE_RECOVERY

        qs = _qs_ultima_execucao_por_dominio().filter(
            situacao__in=("erro", "interrompido")
        )

        itens = []
        for execucao in qs.order_by("-iniciado_em")[:limite]:
            parametros_execucao = _parametros_execucao(execucao)
            id_origem = _id_origem_reprocessamento(execucao)
            tentativas = _contar_reprocessamentos(id_origem)

            if tentativas >= max_tentativas:
                itens.append(
                    {
                        "dominio": execucao.dominio,
                        "id_execucao": str(execucao.id_execucao),
                        "status": "ignorado",
                        "motivo": "limite_tentativas",
                        "tentativas": tentativas,
                        "max_tentativas": max_tentativas,
                    }
                )
                continue

            fases = _normalizar_lista(parametros_execucao.get("fases"), str)
            anos_letivos = _normalizar_lista(
                parametros_execucao.get("anos_letivos"), int
            )
            volume = int(parametros_execucao.get("volume") or 100)
            offset = int(parametros_execucao.get("offset") or 0)

            erro_parametros = validar_parametros_dominio(
                execucao.dominio,
                fases=fases,
                anos_letivos=anos_letivos,
            )
            if erro_parametros:
                itens.append(
                    {
                        "dominio": execucao.dominio,
                        "id_execucao": str(execucao.id_execucao),
                        "status": "ignorado",
                        "motivo": erro_parametros,
                    }
                )
                continue

            task_id = _novo_task_id()
            kwargs_task: dict[str, Any] = {
                "dominio": execucao.dominio,
                "volume": volume,
                "offset": offset,
                "continuar": True,
                "parametros_disparo": {
                    "origem": "recovery",
                    "execucao_origem": id_origem,
                    "execucao_erro": str(execucao.id_execucao),
                    "tentativa": tentativas + 1,
                    "prioridade": prioridade,
                    "continuar": True,
                    "celery_task_id": task_id,
                },
            }
            if fases:
                kwargs_task["fases"] = fases
            if anos_letivos:
                kwargs_task["anos_letivos"] = anos_letivos

            resultado = executar_dominio_task.apply_async(
                kwargs=kwargs_task,
                priority=prioridade,
                task_id=task_id,
            )
            itens.append(
                {
                    "dominio": execucao.dominio,
                    "id_execucao": str(execucao.id_execucao),
                    "status": "reprocessado",
                    "task_id": resultado.id,
                    "tentativa": tentativas + 1,
                    "fases": fases,
                    "anos_letivos": anos_letivos,
                    "volume": volume,
                }
            )

        total_reprocessado = sum(
            1 for item in itens if item["status"] == "reprocessado"
        )
        return Response(
            {
                "total_analisado": len(itens),
                "total_reprocessado": total_reprocessado,
                "itens": itens,
            },
            status=status.HTTP_202_ACCEPTED,
        )


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
        description=_descricao_execucao_dominio(),
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "volume": {
                        "type": "integer",
                        "default": 100,
                        "description": (
                            "Quantidade de registros processados por lote. "
                            "Valores maiores reduzem ciclos, mas aumentam "
                            "memória e duração de cada tentativa."
                        ),
                    },
                    "offset": {
                        "type": "integer",
                        "default": 0,
                        "description": (
                            "Posição inicial da leitura. Normalmente fica 0; "
                            "use apenas para iniciar de um ponto específico."
                        ),
                    },
                    "continuar": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "Quando true, retoma pelo checkpoint do domínio. "
                            "Quando false, começa conforme offset informado."
                        ),
                    },
                    "prioridade": {
                        "type": "integer",
                        "default": 5,
                        "description": (
                            "Prioridade da task no Celery/Redis. "
                            "0 = mais urgente, 9 = menos urgente."
                        ),
                    },
                    "executar_em": {
                        "type": "string",
                        "format": "date-time",
                        "description": (
                            "Agenda a execução para esta data/hora (ISO 8601)."
                        ),
                    },
                    "fases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "nullable": True,
                        "x-nullable": True,
                        "default": None,
                        "description": (
                            "Opcional. Lista de nomes de fases a executar. "
                            "Quando omitido, todas as fases são executadas. "
                        ),
                    },
                    "anos_letivos": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "nullable": True,
                        "x-nullable": True,
                        "default": None,
                        "description": (
                            "Opcional. Lista de anos letivos a processar. "
                            "Quando omitido, processa todos os anos. "
                        ),
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
        try:
            fases = _normalizar_lista(request.data.get("fases"), str)
            anos_letivos = _normalizar_lista(
                request.data.get("anos_letivos"), int
            )
        except (TypeError, ValueError):
            return Response(
                {
                    "erro": (
                        "Parâmetros inválidos. Use fases como lista de textos "
                        "e anos_letivos como lista de números."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        erro_parametros = validar_parametros_dominio(
            dominio,
            ano_letivo=int(ano_letivo) if ano_letivo is not None else None,
            fases=fases,
            anos_letivos=anos_letivos,
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
        if fases is not None:
            kwargs_task["fases"] = fases
        if anos_letivos is not None:
            kwargs_task["anos_letivos"] = anos_letivos
        task_id = _novo_task_id()
        parametros_disparo = {
            "origem": "api",
            "prioridade": prioridade,
            "executar_em": executar_em,
            "celery_task_id": task_id,
        }
        kwargs_task["parametros_disparo"] = parametros_disparo

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
                task_id=task_id,
            )
        else:
            resultado = executar_dominio_task.apply_async(
                kwargs=kwargs_task,
                priority=prioridade,
                task_id=task_id,
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
        agora = timezone.now()

        # Total de registros processados por domínio via checkpoint
        checkpoints = {
            c.dominio: int(c.token_parada or 0)
            for c in EtlCheckpointDominio.objects.all()
        }
        ultima_por_dominio = list(_qs_ultima_execucao_por_dominio())
        progresso_map = _agregar_progresso_execucoes(
            [e.id_execucao for e in ultima_por_dominio]
        )
        for exec_obj in ultima_por_dominio:
            exec_obj.total_processado = checkpoints.get(exec_obj.dominio, 0)
            progresso = progresso_map.get(str(exec_obj.id_execucao), [])
            _enriquecer_execucao(exec_obj, progresso, agora)

        qs_filtrado = _aplicar_filtros_execucao(
            qs=EtlExecucao.objects.all(),
            dominio=dominio,
            data_inicio=data_inicio,
            data_fim=data_fim,
            situacao=situacao,
        ).order_by("-iniciado_em")

        execucoes = list(qs_filtrado[:_LIMITE_MONITORAMENTO])
        progresso_execucoes = _agregar_progresso_execucoes(
            [e.id_execucao for e in execucoes]
        )
        for exec_obj in execucoes:
            _enriquecer_execucao(
                exec_obj,
                progresso_execucoes.get(str(exec_obj.id_execucao), []),
                agora,
            )

        # Últimas 10 execuções com detalhes de tabelas escritas
        ultimas_10 = list(qs_filtrado[:10])
        ids_ultimas_10 = [e.id_execucao for e in ultimas_10]
        tabelas_map = _agregar_tabelas_escritas(ids_ultimas_10)
        progresso_ultimas_10 = _agregar_progresso_execucoes(ids_ultimas_10)
        for exec_obj in ultimas_10:
            _enriquecer_execucao(
                exec_obj,
                progresso_ultimas_10.get(str(exec_obj.id_execucao), []),
                agora,
            )
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


def _agregar_progresso_execucoes(ids_execucao: list) -> dict[str, list]:
    """Agrupa progresso operacional por execução."""
    progresso: dict[str, list] = {}
    for item in (
        EtlProgressoExecucao.objects.filter(id_execucao__in=ids_execucao)
        .values(
            "id_execucao",
            "fase_numero",
            "total_fases",
            "fase_nome",
            "tabela_origem",
            "tabela_destino",
            "etapa",
            "chunk_atual",
            "linhas_lidas",
            "linhas_escritas",
            "linhas_ignoradas",
            "mensagem",
            "iniciado_em",
            "atualizado_em",
        )
        .order_by("id_execucao", "fase_numero")
    ):
        progresso.setdefault(str(item["id_execucao"]), []).append(item)
    return progresso


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
        agora = timezone.now()

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
        progresso_map = _agregar_progresso_execucoes(ids_execucao)

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
            progresso = progresso_map.get(key, [])
            _enriquecer_execucao(exec_obj, progresso, agora)
            total_lido = sum(t["linhas_lidas"] for t in tabelas_lidas)
            total_escrito = sum(t["linhas_escritas"] for t in tabelas_escritas)
            total_nao_gravado = max(total_lido - total_escrito, 0)
            duracao_segundos = _segundos_entre(
                exec_obj.iniciado_em, exec_obj.finalizado_em or agora
            )
            cp = checkpoints.get(exec_obj.dominio)
            cp_da_execucao = bool(
                cp and str(cp.ultimo_id_execucao) == str(exec_obj.id_execucao)
            )
            dominios_kanban.append(
                {
                    "exec": exec_obj,
                    "checkpoint": cp,
                    "checkpoint_da_execucao": cp_da_execucao,
                    "progresso": progresso,
                    "progresso_atual": exec_obj.progresso_atual,
                    "tabelas_lidas": tabelas_lidas,
                    "tabelas_escritas": tabelas_escritas,
                    "total_lido": total_lido,
                    "total_escrito": total_escrito,
                    "total_nao_gravado": total_nao_gravado,
                    "taxa_lidas_minuto": _por_minuto(
                        total_lido, duracao_segundos
                    ),
                    "taxa_alteracao": _percentual(total_escrito, total_lido),
                    "taxa_gravacao": _percentual(total_escrito, total_lido),
                    "taxa_nao_gravadas": _percentual(
                        total_nao_gravado, total_lido
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
