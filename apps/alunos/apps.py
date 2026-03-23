"""Config do app alunos."""

from django.apps import AppConfig


class AlunosConfig(AppConfig):
    """AppConfig para apps.alunos - banco ALUNOS_DB."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.alunos"
    verbose_name = "Alunos"
