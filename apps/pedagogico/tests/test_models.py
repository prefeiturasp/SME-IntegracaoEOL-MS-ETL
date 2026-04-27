from django.test import TestCase

from apps.pedagogico.models import (
    AgrupamentoAtribuicaoTerritorioSaber,
    ComponenteCurricular,
    ComponenteCurricularAgrupamento,
    ComponenteCurricularPorTurma,
    ComponenteInicioTurma,
    GradeCurricularSerie,
)


class PedagogicoModelsTest(TestCase):
    """Testes para cobrir métodos ``__str__`` do app pedagogico."""

    def test_componente_curricular_str(self) -> None:
        obj = ComponenteCurricular(codigo=100, descricao="Arte")
        self.assertEqual(str(obj), "100 - Arte")

    def test_componente_curricular_por_turma_str(self) -> None:
        obj = ComponenteCurricularPorTurma(
            codigo=200,
            descricao="Matemática",
            regencia=False,
            planejamento_regencia=True,
            territorio_saber=False,
            turma_codigo="T1",
            exibir_componente_eol=True,
            professor="RF123",
            ano_letivo=2025,
        )
        self.assertEqual(str(obj), "200 turma=T1 professor=RF123")

    def test_componente_curricular_agrupamento_str(self) -> None:
        obj = ComponenteCurricularAgrupamento(
            componente_codigo=300,
            turma_codigo="T2",
            codigo_agrupamento=999,
            ano_letivo=2025,
        )
        self.assertEqual(str(obj), "componente=300 turma=T2 agrupamento=999")

    def test_dados_aula_turma_str(self) -> None:
        obj = ComponenteInicioTurma(
            componente_codigo="500",
            componente_descricao="História",
            turma_codigo="T3",
        )
        self.assertEqual(str(obj), "500 turma=T3")

    def test_componente_curricular_por_ano_letivo_str(self) -> None:
        obj = GradeCurricularSerie(
            codigo_componente_curricular=600,
            descricao_componente_curricular="Geografia",
            ano_letivo=2025,
            modalidade=5,
        )
        self.assertEqual(str(obj), "600 ano_letivo=2025 modalidade=5")

    def test_agrupamento_atribuicao_territorio_saber_str(self) -> None:
        obj = AgrupamentoAtribuicaoTerritorioSaber(
            cod_agrupamento=777,
            cod_territorio_saber=88,
            dt_inicio_atribuicao="2025-01-01T00:00:00",
            ano_atribuicao=2025,
            ano_letivo=2025,
        )
        self.assertEqual(
            str(obj), "agrupamento=777 territorio=88 ano_letivo=2025"
        )
