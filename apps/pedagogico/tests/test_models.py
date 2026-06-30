from django.test import TestCase

from apps.pedagogico.models import (
    AgrupamentoAtribuicaoTerritorioSaber,
    ComponenteCurricular,
    ComponenteCurricularAgrupamento,
    GradeComponenteCurricular,
    Turma,
    TurmaItinerarioEnsinoMedio,
)


class PedagogicoModelsTest(TestCase):
    """Testes para cobrir métodos ``__str__`` do app pedagogico."""

    def test_componente_curricular_str(self) -> None:
        obj = ComponenteCurricular(codigo=100, descricao="Arte")
        self.assertEqual(str(obj), "100 - Arte")

    def test_componente_curricular_agrupamento_str(self) -> None:
        obj = ComponenteCurricularAgrupamento(
            componente_codigo=300,
            turma_codigo="T2",
            codigo_agrupamento=999,
            ano_letivo=2025,
        )
        self.assertEqual(str(obj), "componente=300 turma=T2 agrupamento=999")

    def test_grade_componente_curricular_str(self) -> None:
        obj = GradeComponenteCurricular(
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

    def test_turma_str(self) -> None:
        obj = Turma(
            codigo=123456,
            nome_turma="5A Manhã",
            tipo_turma=1,
            ano_letivo=2025,
            ue_codigo="001234",
        )
        self.assertEqual(str(obj), "123456 - 5A Manhã")

    def test_turma_campos_grade_programa_default(self) -> None:
        """Campos NOT NULL de grade de programa têm default zero/vazio."""
        obj = Turma(
            codigo=123456,
            nome_turma="5A Manhã",
            tipo_turma=1,
            ano_letivo=2025,
            ue_codigo="001234",
        )
        self.assertEqual(obj.tipo_escola, 0)
        self.assertEqual(obj.codigo_grade_programa, 0)
        self.assertEqual(obj.descricao_grade_programa, "NAO INFORMADA")
        self.assertEqual(obj.tipo_grade_programa, 0)

    def test_turma_itinerario_ensino_medio_str(self) -> None:
        obj = TurmaItinerarioEnsinoMedio(nome="Itinerário A", serie="3")
        self.assertEqual(str(obj), "Itinerário A")
