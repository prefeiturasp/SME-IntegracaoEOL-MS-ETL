"""Serializers DRF para controle de auditoria."""

from rest_framework import serializers

from apps.controle_auditoria.models import (
    EtlCheckpointDominio,
    EtlExecucao,
    EtlExecucaoTabelaEscrita,
    EtlExecucaoTabelaLida,
    EtlProgressoExecucao,
)
from apps.core.api.serializers import (
    HealthStatusSerializer as BaseHealthStatusSerializer,
)


class EtlCheckpointDominioSerializer(serializers.ModelSerializer):
    """Serializa checkpoint por dominio."""

    class Meta:

        model = EtlCheckpointDominio
        fields = "__all__"


class EtlExecucaoSerializer(serializers.ModelSerializer):
    """Serializa execucoes ETL."""

    class Meta:

        model = EtlExecucao
        fields = "__all__"


class EtlExecucaoTabelaLidaSerializer(serializers.ModelSerializer):
    """Serializa rastreio de leitura por execucao."""

    class Meta:

        model = EtlExecucaoTabelaLida
        fields = "__all__"


class EtlExecucaoTabelaEscritaSerializer(serializers.ModelSerializer):
    """Serializa rastreio de escrita por execucao."""

    class Meta:

        model = EtlExecucaoTabelaEscrita
        fields = "__all__"


class EtlProgressoExecucaoSerializer(serializers.ModelSerializer):
    """Serializa progresso operacional de uma execução ETL."""

    class Meta:

        model = EtlProgressoExecucao
        fields = "__all__"


class EtlExecucaoDetalheSerializer(serializers.ModelSerializer):
    """Serializa execucao ETL com tabelas relacionadas via id_execucao."""

    tabelas_lidas = serializers.SerializerMethodField(
        help_text="Tabelas lidas nesta execução (EtlExecucaoTabelaLida)"
    )
    tabelas_escritas = serializers.SerializerMethodField(
        help_text="Tabelas escritas nesta execução (EtlExecucaoTabelaEscrita)"
    )
    progresso = serializers.SerializerMethodField(
        help_text="Progresso operacional por fase."
    )

    class Meta:

        model = EtlExecucao
        fields = [
            "id",
            "id_execucao",
            "dominio",
            "situacao",
            "iniciado_em",
            "finalizado_em",
            "mensagem_erro",
            "parametros",
            "criado_em",
            "tabelas_lidas",
            "tabelas_escritas",
            "progresso",
        ]

    def get_tabelas_lidas(self, obj: EtlExecucao) -> list:
        """Retorna tabelas lidas com o mesmo id_execucao."""
        qs = EtlExecucaoTabelaLida.objects.filter(id_execucao=obj.id_execucao)
        return list(EtlExecucaoTabelaLidaSerializer(qs, many=True).data)

    def get_tabelas_escritas(self, obj: EtlExecucao) -> list:
        """Retorna tabelas escritas com o mesmo id_execucao."""
        qs = EtlExecucaoTabelaEscrita.objects.filter(
            id_execucao=obj.id_execucao
        )
        return list(EtlExecucaoTabelaEscritaSerializer(qs, many=True).data)

    def get_progresso(self, obj: EtlExecucao) -> list:
        """Retorna progresso operacional com o mesmo id_execucao."""
        qs = EtlProgressoExecucao.objects.filter(
            id_execucao=obj.id_execucao
        ).order_by("fase_numero")
        return list(EtlProgressoExecucaoSerializer(qs, many=True).data)


class HealthStatusSerializer(BaseHealthStatusSerializer):
    """Serializer para resposta do endpoint de healthcheck."""

    pass
