"""Rotas da API de institucional."""

from django.urls import path

from apps.institucional.api.views import HealthInstitucionalView

urlpatterns = [
    path(
        "institucional/health/", HealthInstitucionalView.as_view(), name="institucional"
    ),
]
