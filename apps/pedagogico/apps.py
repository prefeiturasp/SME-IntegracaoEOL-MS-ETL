"""Config do app pedagogico."""

from django.apps import AppConfig


class PedagogicoConfig(AppConfig):
    """AppConfig para apps.pedagogico - banco PEDAGOGICO_DB."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pedagogico"
    verbose_name = "Pedagógico"
