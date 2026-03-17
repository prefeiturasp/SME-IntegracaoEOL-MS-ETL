"""Serializers DRF para controle de auditoria."""

from rest_framework import serializers

from apps.controle_auditoria.models import EtlCheckpointDominio, EtlExecucao


class EtlCheckpointDominioSerializer(serializers.ModelSerializer):
    """Serializa checkpoint por dominio."""

    class Meta:
        """Configuração de metadados do modelo."""

        model = EtlCheckpointDominio
        fields = "__all__"


class EtlExecucaoSerializer(serializers.ModelSerializer):
    """Serializa execucoes ETL."""

    class Meta:
        """Configuração de metadados do modelo."""

        model = EtlExecucao
        fields = "__all__"


class HealthStatusSerializer(serializers.Serializer):
    """Serializer para resposta do endpoint de healthcheck."""

    status = serializers.ChoiceField(choices=["healthy", "degraded", "unhealthy"])
