"""Rotas da API de professores."""

from django.urls import path

from apps.professores.api.views import FuncionariosEscolaView

urlpatterns = [
    path(
        "professores/escolas/<str:codigo_ue>/funcionarios/",
        FuncionariosEscolaView.as_view(),
        name="professores-funcionarios-escola",
    ),
]
