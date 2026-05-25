"""Configuração do app Programas."""

from django.apps import AppConfig


class ProgramasConfig(AppConfig):
    """Configuração Django do app Programas."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.programas"
    verbose_name = "Programas"
