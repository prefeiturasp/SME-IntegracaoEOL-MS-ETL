"""Configuracao do app controle_auditoria."""

from django.apps import AppConfig


class ControleAuditoriaConfig(AppConfig):
    """Configuracao principal do app de auditoria."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.controle_auditoria"
    verbose_name = "Controle e Auditoria"
