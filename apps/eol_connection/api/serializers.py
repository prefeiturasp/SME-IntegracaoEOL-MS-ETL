"""Serializers do app eol_connection (status de saude)."""

from rest_framework import serializers


class HealthStatusSerializer(serializers.Serializer):
    """Serializer para resposta do endpoint de healthcheck."""

    status = serializers.ChoiceField(
        choices=["healthy", "degraded", "unhealthy"],
        help_text="Estado geral do servico.",
    )
