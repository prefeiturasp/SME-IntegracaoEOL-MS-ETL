"""Config do app professores."""

from django.apps import AppConfig


class ProfessoresConfig(AppConfig):
    """AppConfig para apps.professores - banco PROFESSORES_DB."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.professores"
    verbose_name = "Professores"
