"""Serializers DRF para controle de auditoria."""

from rest_framework import serializers

from apps.controle_auditoria.models import (
    EtlCheckpointDominio,
    EtlExecucao,
    EtlExecucaoTabelaEscrita,
    EtlExecucaoTabelaLida,
)


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


class EtlExecucaoTabelaLidaSerializer(serializers.ModelSerializer):
    """Serializa rastreio de leitura por execucao."""

    class Meta:
        """Configuração de metadados do modelo."""

        model = EtlExecucaoTabelaLida
        fields = "__all__"


class EtlExecucaoTabelaEscritaSerializer(serializers.ModelSerializer):
    """Serializa rastreio de escrita por execucao."""

    class Meta:
        """Configuração de metadados do modelo."""

        model = EtlExecucaoTabelaEscrita
        fields = "__all__"


class EtlExecucaoDetalheSerializer(serializers.ModelSerializer):
    """Serializa execucao ETL com tabelas relacionadas via id_execucao."""

    tabelas_lidas = serializers.SerializerMethodField(
        help_text="Tabelas lidas nesta execução (EtlExecucaoTabelaLida)"
    )
    tabelas_escritas = serializers.SerializerMethodField(
        help_text="Tabelas escritas nesta execução (EtlExecucaoTabelaEscrita)"
    )

    class Meta:
        """Configuração de metadados do modelo."""

        model = EtlExecucao
        fields = [
            "id",
            "id_execucao",
            "dominio",
            "situacao",
            "iniciado_em",
            "finalizado_em",
            "mensagem_erro",
            "criado_em",
            "tabelas_lidas",
            "tabelas_escritas",
        ]

    def get_tabelas_lidas(self, obj: EtlExecucao) -> list:
        """Retorna tabelas lidas com o mesmo id_execucao."""
        qs = EtlExecucaoTabelaLida.objects.filter(id_execucao=obj.id_execucao)
        return list(EtlExecucaoTabelaLidaSerializer(qs, many=True).data)

    def get_tabelas_escritas(self, obj: EtlExecucao) -> list:
        """Retorna tabelas escritas com o mesmo id_execucao."""
        qs = EtlExecucaoTabelaEscrita.objects.filter(id_execucao=obj.id_execucao)
        return list(EtlExecucaoTabelaEscritaSerializer(qs, many=True).data)


class HealthStatusSerializer(serializers.Serializer):
    """Serializer para resposta do endpoint de healthcheck."""

    status = serializers.ChoiceField(choices=["healthy", "degraded", "unhealthy"])
