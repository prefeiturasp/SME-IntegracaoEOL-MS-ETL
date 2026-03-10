"""Rotas da API de controle/auditoria."""

from django.urls import path

from apps.controle_auditoria.api.views import (
    CheckpointsView,
    ExecucoesView,
    ExecutarDominioView,
)

urlpatterns = [
    path("checkpoints/", CheckpointsView.as_view(), name="checkpoints"),
    path("execucoes/", ExecucoesView.as_view(), name="execucoes"),
    path(
        "dominios/<str:dominio>/executar/",
        ExecutarDominioView.as_view(),
        name="executar-dominio",
    ),
]
