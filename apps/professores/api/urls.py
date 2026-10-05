"""Rotas da API de Professores."""

from django.urls import path

from apps.professores.api.views import HealthProfessoresView

urlpatterns = [
    path(
        "professores/health/",
        HealthProfessoresView.as_view(),
        name="professores",
    ),
]
