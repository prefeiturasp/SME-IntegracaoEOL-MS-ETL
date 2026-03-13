"""Serializers DRF para controle do institucional."""

from rest_framework import serializers


class HealthStatusSerializer(serializers.Serializer):
    """Serializer para resposta do endpoint de healthcheck."""

    status = serializers.ChoiceField(choices=["healthy", "degraded", "unhealthy"])
