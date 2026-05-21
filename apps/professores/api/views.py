"""Views da API de professores."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.professores.api.serializers import FuncionarioUnidadeEducacionalSerializer
from apps.professores.models import FuncionarioUnidadeEducacional


class FuncionariosEscolaView(APIView):
    """Lista funcionarios de uma unidade educacional."""

    serializer_class = FuncionarioUnidadeEducacionalSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="codigo_ue",
                type=str,
                location=OpenApiParameter.PATH,
                required=True,
                description="Codigo da unidade educacional.",
            ),
            OpenApiParameter(
                name="codigo_cargo",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filtro opcional por cargo.",
            ),
        ],
        responses={200: FuncionarioUnidadeEducacionalSerializer(many=True)},
    )
    def get(self, request: Request, codigo_ue: str) -> Response:
        """Retorna funcionarios da escola.

        Args:
            request: Requisicao HTTP com query params.
            codigo_ue: Codigo da unidade educacional.
        Returns:
            Lista de funcionarios ou erro de validacao.
        """
        codigo_cargo = request.query_params.get("codigo_cargo")
        if codigo_cargo is not None and not codigo_cargo.isdecimal():
            return Response({"erro": "codigo_cargo invalido"}, status=400)

        queryset = FuncionarioUnidadeEducacional.objects.using(
            "professores_db"
        ).filter(codigo_ue=str(codigo_ue))
        if codigo_cargo is not None:
            queryset = queryset.filter(codigo_cargo=str(int(codigo_cargo)))

        queryset = queryset.order_by("nome")
        serializer = FuncionarioUnidadeEducacionalSerializer(queryset, many=True)
        return Response(serializer.data)
