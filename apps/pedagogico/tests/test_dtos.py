from datetime import datetime

from django.test import SimpleTestCase
from django.utils import timezone

from apps.pedagogico.dtos.model_in import (
    ComponenteCurricularSimplesIn,
    ComponenteInicioTurmaIn,
    ComponentePorTurmaIn,
    ComponenteRegenciaIn,
    GradeCurricularSerieIn,
    TurmaIn,
)


class ComponenteCurricularSimplesInTest(SimpleTestCase):
    """Testes de ``ComponenteCurricularSimplesIn.to_domain()``."""

    def test_mapeamento_basico(self) -> None:
        dto = ComponenteCurricularSimplesIn(codigo="100", descricao=" Arte ")
        data = dto.to_domain("agora")

        self.assertEqual(data["codigo"], 100)
        self.assertEqual(data["descricao"], "Arte")
        self.assertEqual(data["transferido_em"], "agora")


class ComponentePorTurmaInTest(SimpleTestCase):
    """Testes de ``ComponentePorTurmaIn.to_domain()``."""

    def test_mapeia_flags_e_componente_pai(self) -> None:
        dto = ComponentePorTurmaIn(
            codigo=513,
            descricao=" Inglês ",
            eh_regencia=1,
            eh_territorio=1,
            tipo_escola=1,
            turno_turma=6,
            ano_turma="7",
            ano_letivo=2025,
            turma_codigo=123,
            professor=456,
            atribuicao_externa=0,
        )
        data = dto.to_domain(transferido_em="agora", planejamento=False)

        self.assertEqual(data["codigo"], 513)
        self.assertEqual(data["descricao"], "Inglês")
        self.assertTrue(data["regencia"])
        self.assertTrue(data["territorio_saber"])
        self.assertFalse(data["planejamento_regencia"])
        self.assertEqual(data["codigo_componente_territorio_saber"], 513)
        self.assertEqual(data["codigo_componente_curricular_pai"], 512)
        self.assertEqual(data["turma_codigo"], "123")
        self.assertEqual(data["professor"], "456")
        self.assertTrue(data["exibir_componente_eol"])

    def test_componente_com_pai_vigente_ate_2021_nao_exibe_em_ano_historico(
        self,
    ) -> None:
        # codigo=513 está em MAPA_COMPONENTE_PAI (vigência 2021-12-31)
        # Para ano_letivo <= 2021 a vigência ainda é ativa → exibir = False
        dto = ComponentePorTurmaIn(
            codigo=513,
            descricao=" Inglês ",
            eh_regencia=0,
            eh_territorio=0,
            tipo_escola=1,
            turno_turma=6,
            ano_turma="7",
            ano_letivo=2021,
            turma_codigo=None,
            professor=None,
            atribuicao_externa=0,
        )
        data = dto.to_domain(transferido_em="agora")
        self.assertFalse(data["exibir_componente_eol"])

    def test_componente_com_pai_vigente_ate_2021_exibe_em_ano_posterior(
        self,
    ) -> None:
        # mesmo codigo=513, mas ano_letivo >= 2022 →
        # vigência expirou → exibir = True
        dto = ComponentePorTurmaIn(
            codigo=513,
            descricao=" Inglês ",
            eh_regencia=0,
            eh_territorio=0,
            tipo_escola=1,
            turno_turma=6,
            ano_turma="7",
            ano_letivo=2022,
            turma_codigo=None,
            professor=None,
            atribuicao_externa=0,
        )
        data = dto.to_domain(transferido_em="agora")
        self.assertTrue(data["exibir_componente_eol"])

    def test_componente_sem_pai_sempre_exibe(self) -> None:
        # codigo sem entrada em MAPA_COMPONENTE_PAI →
        # exibir = True em qualquer ano
        dto = ComponentePorTurmaIn(
            codigo=1322,
            descricao=" PAP ",
            eh_regencia=0,
            eh_territorio=0,
            tipo_escola=1,
            turno_turma=6,
            ano_turma="7",
            ano_letivo=2019,
            turma_codigo=None,
            professor=None,
            atribuicao_externa=0,
        )
        data = dto.to_domain(transferido_em="agora", planejamento=True)
        self.assertTrue(data["exibir_componente_eol"])
        self.assertIsNone(data["codigo_componente_territorio_saber"])
        self.assertIsNone(data["codigo_componente_curricular_pai"])
        self.assertIsNone(data["turma_codigo"])
        self.assertIsNone(data["professor"])
        self.assertTrue(data["planejamento_regencia"])


class ComponenteRegenciaInTest(SimpleTestCase):
    """Testes de ``ComponenteRegenciaIn.to_domain()``."""

    def test_mapeamento_com_datetimes_aware(self) -> None:
        dto = ComponenteRegenciaIn(
            codigo_componente_curricular=200,
            descricao_componente_curricular=" Ciências ",
            ano_turma="5",
            ano_letivo=2025,
            turma_codigo=321,
            tipo_escola=2,
            turno_turma=5,
            rf_professor=999,
            codigo_experiencia_pedagogica=10,
            codigo_territorio_saber=20,
            descricao_territorio_saber="Território",
            descricao_experiencia_pedagogica="Experiência",
            data_atribuicao="2025-02-01T10:00:00",
            ano_atribuicao=2025,
            data_fim_turma=None,
            atribuicao_externa=0,
            data_disponibilizacao="2025-12-01T10:00:00",
            codigo_motivo_disponibilizacao=34,
        )
        data = dto.to_domain(transferido_em="agora", planejamento=True)

        self.assertEqual(data["codigo"], 200)
        self.assertEqual(data["descricao"], "Ciências")
        self.assertTrue(data["territorio_saber"])
        self.assertEqual(data["codigo_componente_territorio_saber"], 20)
        self.assertEqual(data["professor"], "999")
        self.assertEqual(data["ano_turma"], "5")
        self.assertTrue(data["componente_planejamento_regencia"])
        self.assertTrue(timezone.is_aware(data["inicio_atribuicao"]))
        self.assertTrue(timezone.is_aware(data["fim_atribuicao"]))


class ComponenteInicioTurmaInTest(SimpleTestCase):
    """Testes de ``ComponenteInicioTurmaIn.to_domain()``."""

    def test_mapeamento_completo(self) -> None:
        dto = ComponenteInicioTurmaIn(
            componente_codigo=100,
            componente_descricao=" Arte ",
            turma_codigo=200,
            data_inicio_turma=datetime(2025, 3, 10, 8, 0, 0),
            ue_codigo=300,
            ano_letivo=2025,
            tipo_periodicidade=1,
        )
        data = dto.to_domain("agora")

        self.assertEqual(data["componente_codigo"], "100")
        self.assertEqual(data["componente_descricao"], "Arte")
        self.assertEqual(data["turma_codigo"], "200")
        self.assertTrue(timezone.is_aware(data["data_inicio_turma"]))
        self.assertEqual(data["ue_codigo"], "300")
        self.assertEqual(data["ano_letivo"], 2025)
        self.assertEqual(data["tipo_periodicidade"], 1)

    def test_campos_opcionais_nulos(self) -> None:
        dto = ComponenteInicioTurmaIn(
            componente_codigo=100,
            componente_descricao=" Arte ",
            turma_codigo=200,
            data_inicio_turma=None,
            ue_codigo=None,
            ano_letivo=None,
            tipo_periodicidade=None,
        )
        data = dto.to_domain("agora")

        self.assertIsNone(data["data_inicio_turma"])
        self.assertIsNone(data["ue_codigo"])
        self.assertIsNone(data["ano_letivo"])
        self.assertIsNone(data["tipo_periodicidade"])


class GradeCurricularSerieInTest(SimpleTestCase):
    """Testes de ``GradeCurricularSerieIn.to_domain()``."""

    def test_mapeamento_basico(self) -> None:
        dto = GradeCurricularSerieIn(
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
        dto = GradeCurricularSerieIn(
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
        "modalidade": " Fundamental ",
        "codigo_modalidade": 5,
        "semestre": 0,
        "ensino_especial": 0,
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
        self.assertEqual(data["modalidade"], "Fundamental")
        self.assertEqual(data["codigo_modalidade"], 5)
        self.assertEqual(data["semestre"], 0)
        self.assertFalse(data["ensino_especial"])
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
            modalidade=None,
            codigo_modalidade=None,
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
