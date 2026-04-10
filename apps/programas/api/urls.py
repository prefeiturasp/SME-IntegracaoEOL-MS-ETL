"""Rotas da API de Programas."""

from django.urls import path

from apps.programas.api.views import HealthProgramasView

urlpatterns = [
    path(
        "programas/health/", HealthProgramasView.as_view(), name="programas"
    ),
]
