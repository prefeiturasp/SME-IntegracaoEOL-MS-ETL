"""Configuracao do app escolas."""

from django.apps import AppConfig


class EscolasConfig(AppConfig):
    """Configuracao principal do app de escolas."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.escolas"
    verbose_name = "Escolas"
