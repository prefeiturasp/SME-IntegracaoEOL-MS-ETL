"""Config do app programas."""

from django.apps import AppConfig


class ProgramasConfig(AppConfig):
    """AppConfig para apps.programas - banco PROGRAMAS_DB."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.programas"
    verbose_name = "Programas"
