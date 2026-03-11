"""Admin do app escolas."""

from django.contrib import admin

from apps.escolas.models import ConsultaEscolasLog


@admin.register(ConsultaEscolasLog)
class ConsultaEscolasLogAdmin(admin.ModelAdmin):
    """Admin de log de consultas de escolas."""

    list_display = (
        "id",
        "offset_inicial",
        "limite",
        "total_retorno",
        "executado_em",
    )
    ordering = ("-executado_em",)
