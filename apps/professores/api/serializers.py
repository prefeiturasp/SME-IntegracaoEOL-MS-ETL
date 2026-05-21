"""Serializers da API do dominio professores."""

from datetime import datetime

from django.utils import timezone
from rest_framework import serializers

from apps.professores.models import FuncionarioUnidadeEducacional


class FuncionarioUnidadeEducacionalSerializer(serializers.ModelSerializer):
    """Serializer de funcionarios por unidade educacional."""

    data_inicio = serializers.SerializerMethodField()
    data_fim = serializers.SerializerMethodField()

    class Meta:
        model = FuncionarioUnidadeEducacional
        fields = [
            "codigo_rf",
            "nome",
            "data_inicio",
            "data_fim",
            "cargo",
            "codigo_tipo_funcao_atividade",
            "esta_afastado",
            "funcao_externo",
            "tipo_funcao_externo",
        ]

    def get_data_inicio(
        self, obj: FuncionarioUnidadeEducacional
    ) -> str | None:
        """Formata data de inicio no contrato legado.

        Args:
            obj: Registro de funcionario.
        Returns:
            Data formatada ou `None`.
        """
        return self._formatar_data(obj.data_inicio)

    def get_data_fim(
        self, obj: FuncionarioUnidadeEducacional
    ) -> str | None:
        """Formata data de fim no contrato legado.

        Args:
            obj: Registro de funcionario.
        Returns:
            Data formatada ou `None`.
        """
        return self._formatar_data(obj.data_fim)

    def _formatar_data(self, valor: datetime | None) -> str | None:
        """Formata datetime em DD/MM/YYYY HH:mm:ss.

        Args:
            valor: Data/hora armazenada no destino.
        Returns:
            Data formatada ou `None`.
        """
        if valor is None:
            return None
        if timezone.is_aware(valor):
            valor = timezone.localtime(valor)
        return valor.strftime("%d/%m/%Y %H:%M:%S")
