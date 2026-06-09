from datetime import datetime

from django.test import SimpleTestCase
from django.utils import timezone

from apps.pedagogico.dtos.model_in import (
    ComponenteCurricularSimplesIn,
    ComponenteTurmaIn,
    GradeComponenteCurricularIn,
    TurmaIn,
)


class ComponenteCurricularSimplesInTest(SimpleTestCase):
    """Testes de ``ComponenteCurricularSimplesIn.to_domain()``."""

    def test_mapeamento_basico(self) -> None:
        dto = ComponenteCurricularSimplesIn(
            codigo="100", descricao=" Arte ", regencia=1
        )
        data = dto.to_domain("agora")

        self.assertEqual(data["codigo"], 100)
        self.assertEqual(data["descricao"], "Arte")
        self.assertTrue(data["regencia"])
        self.assertEqual(data["transferido_em"], "agora")


class ComponenteTurmaInTest(SimpleTestCase):
    """Testes de ``ComponenteTurmaIn.to_domain()``."""

    def test_mapeamento_minimo(self) -> None:
        dto = ComponenteTurmaIn(
            turma_codigo=123,
            componente_codigo=220,
            codigo_componente_territorio_saber=None,
        )

        data = dto.to_domain("agora")

        self.assertEqual(data["turma_codigo"], "123")
        self.assertEqual(data["componente_codigo"], 220)
        self.assertIsNone(data["codigo_componente_territorio_saber"])
        self.assertEqual(data["transferido_em"], "agora")


class GradeComponenteCurricularInTest(SimpleTestCase):
    """Testes de ``GradeComponenteCurricularIn.to_domain()``."""

    def test_mapeamento_basico(self) -> None:
        dto = GradeComponenteCurricularIn(
            codigo_componente_curricular=700,
            descricao_componente_curricular=" Geografia ",
            codigo_ano_turma=8,
            descricao_serie_ensino=" 8o ano ",
            codigo_serie_ensino=80,
            modalidade=5,
            ano_letivo=2025,
        )
        data = dto.to_domain("agora")

        self.assertEqual(data["codigo_componente_curricular"], 700)
        self.assertEqual(data["descricao_componente_curricular"], "Geografia")
        self.assertEqual(data["codigo_ano_turma"], "8")
        self.assertEqual(data["descricao_serie_ensino"], "8o ano")
        self.assertEqual(data["codigo_serie_ensino"], 80)
        self.assertEqual(data["modalidade"], 5)
        self.assertEqual(data["ano_letivo"], 2025)

    def test_campos_opcionais_nulos(self) -> None:
        dto = GradeComponenteCurricularIn(
            codigo_componente_curricular=700,
            descricao_componente_curricular=" Geografia ",
            codigo_ano_turma=None,
            descricao_serie_ensino=None,
            codigo_serie_ensino=None,
            modalidade=None,
            ano_letivo=2025,
        )
        data = dto.to_domain("agora")

        self.assertIsNone(data["codigo_ano_turma"])
        self.assertIsNone(data["descricao_serie_ensino"])
        self.assertIsNone(data["codigo_serie_ensino"])
        self.assertIsNone(data["modalidade"])


def _turma_in_completa(**overrides: object) -> TurmaIn:
    defaults: dict[str, object] = {
        "codigo": 123456,
        "ano_letivo": 2025,
        "ano": "5",
        "tipo_turma": 1,
        "nome_turma": " 5A Manhã ",
        "duracao_turno": 5,
        "tipo_turno": 2,
        "data_inicio_turma": datetime(2025, 2, 5, 8, 0, 0),
        "data_fim": None,
        "extinta": 0,
        "situacao": "O",
        "ue_codigo": "001234",
        "data_atualizacao": datetime(2025, 1, 10, 0, 0, 0),
        "data_status_turma_escola": None,
        "serie_ensino": " 5o ano ",
        "codigo_serie_ensino": 50,
        "modalidade": " Fundamental ",
        "codigo_modalidade": 5,
        "codigo_tipo_programa": 3,
        "codigo_modalidade_etapa": 5,
        "semestre": 0,
        "ensino_especial": 0,
        "codigo_etapa_ensino": 5,
        "codigo_ciclo_ensino": 3,
    }
    defaults.update(overrides)
    return TurmaIn(**defaults)


class TurmaInTest(SimpleTestCase):
    """Testes de ``TurmaIn.to_domain()``."""

    def test_mapeamento_tipos_basicos(self) -> None:
        data = _turma_in_completa().to_domain("agora")

        self.assertEqual(data["codigo"], 123456)
        self.assertEqual(data["ano_letivo"], 2025)
        self.assertEqual(data["ano"], "5")
        self.assertEqual(data["tipo_turma"], 1)
        self.assertEqual(data["nome_turma"], "5A Manhã")
        self.assertEqual(data["duracao_turno"], 5)
        self.assertEqual(data["tipo_turno"], 2)
        self.assertFalse(data["extinta"])
        self.assertEqual(data["situacao"], "O")
        self.assertEqual(data["ue_codigo"], "001234")
        self.assertEqual(data["serie_ensino"], "5o ano")
        self.assertEqual(data["codigo_serie_ensino"], 50)
        self.assertEqual(data["modalidade"], "Fundamental")
        self.assertEqual(data["codigo_modalidade"], 5)
        self.assertEqual(data["codigo_tipo_programa"], 3)
        self.assertEqual(data["semestre"], 0)
        self.assertFalse(data["ensino_especial"])
        self.assertEqual(data["codigo_etapa_ensino"], 5)
        self.assertEqual(data["codigo_ciclo_ensino"], 3)
        self.assertEqual(data["transferido_em"], "agora")

    def test_data_inicio_turma_aware(self) -> None:
        data = _turma_in_completa().to_domain("agora")
        self.assertIsNotNone(data["data_inicio_turma"])
        self.assertTrue(timezone.is_aware(data["data_inicio_turma"]))

    def test_data_atualizacao_aware(self) -> None:
        data = _turma_in_completa().to_domain("agora")
        self.assertIsNotNone(data["data_atualizacao"])
        self.assertTrue(timezone.is_aware(data["data_atualizacao"]))

    def test_extinta_true_quando_valor_truthy(self) -> None:
        data = _turma_in_completa(extinta=1).to_domain("agora")
        self.assertTrue(data["extinta"])

    def test_ensino_especial_true_quando_valor_truthy(self) -> None:
        data = _turma_in_completa(ensino_especial=1).to_domain("agora")
        self.assertTrue(data["ensino_especial"])

    def test_semestre_none_vira_zero(self) -> None:
        data = _turma_in_completa(semestre=None).to_domain("agora")
        self.assertEqual(data["semestre"], 0)

    def test_semestre_dois(self) -> None:
        data = _turma_in_completa(semestre=2).to_domain("agora")
        self.assertEqual(data["semestre"], 2)

    def test_campos_opcionais_nulos(self) -> None:
        data = _turma_in_completa(
            data_inicio_turma=None,
            data_fim=None,
            duracao_turno=None,
            tipo_turno=None,
            situacao=None,
            ue_codigo=None,
            data_atualizacao=None,
            data_status_turma_escola=None,
            serie_ensino=None,
            codigo_serie_ensino=None,
            modalidade=None,
            codigo_modalidade=None,
            codigo_tipo_programa=None,
        ).to_domain("agora")

        self.assertIsNone(data["data_inicio_turma"])
        self.assertIsNone(data["data_fim"])
        self.assertIsNone(data["duracao_turno"])
        self.assertIsNone(data["tipo_turno"])
        self.assertIsNone(data["situacao"])
        self.assertIsNone(data["ue_codigo"])
        self.assertIsNone(data["data_atualizacao"])
        self.assertIsNone(data["data_status_turma_escola"])
        self.assertIsNone(data["serie_ensino"])
        self.assertIsNone(data["codigo_serie_ensino"])
        self.assertIsNone(data["modalidade"])
        self.assertIsNone(data["codigo_modalidade"])

    def test_data_status_turma_escola_aware(self) -> None:
        data = _turma_in_completa(
            data_status_turma_escola=datetime(2025, 6, 30, 12, 0, 0)
        ).to_domain("agora")
        self.assertTrue(timezone.is_aware(data["data_status_turma_escola"]))

    def test_data_fim_aware(self) -> None:
        data = _turma_in_completa(
            data_fim=datetime(2025, 12, 20, 0, 0, 0)
        ).to_domain("agora")
        self.assertTrue(timezone.is_aware(data["data_fim"]))
