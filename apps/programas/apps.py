"""Config do app programas."""

from django.apps import AppConfig


class ProgramasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.programas"
    verbose_name = "Programas"
