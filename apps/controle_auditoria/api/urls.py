"""Rotas da API de controle/auditoria."""

from django.urls import path

from apps.controle_auditoria.api.views import (
    CheckpointsView,
    ExecucaoDetalheView,
    ExecucoesTabelaEscritaView,
    ExecucoesTabelaLidaView,
    ExecucoesView,
    ExecutarDominioView,
    MonitoramentoExecucoesView,
    MonitoramentoResumoView,
)

urlpatterns = [
    path("checkpoints/", CheckpointsView.as_view(), name="checkpoints"),
    # Monitoramento público (sem auth)
    path(
        "monitoramento/execucoes/",
        MonitoramentoExecucoesView.as_view(),
        name="monitoramento-execucoes",
    ),
    path(
        "monitoramento/resumo/",
        MonitoramentoResumoView.as_view(),
        name="monitoramento-resumo",
    ),
    # Execuções — rotas fixas antes da rota com parâmetro
    path("execucoes/", ExecucoesView.as_view(), name="execucoes"),
    path(
        "execucoes/tabelas-lidas/",
        ExecucoesTabelaLidaView.as_view(),
        name="execucoes-tabelas-lidas",
    ),
    path(
        "execucoes/tabelas-escritas/",
        ExecucoesTabelaEscritaView.as_view(),
        name="execucoes-tabelas-escritas",
    ),
    path(
        "execucoes/<str:id_execucao>/",
        ExecucaoDetalheView.as_view(),
        name="execucao-detalhe",
    ),
    path(
        "dominios/<str:dominio>/executar/",
        ExecutarDominioView.as_view(),
        name="executar-dominio",
    ),
]
