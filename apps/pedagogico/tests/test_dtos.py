from datetime import datetime

from django.test import SimpleTestCase
from django.utils import timezone

from apps.pedagogico.dtos.model_in import (
    ApiEolAgrupamentoAtribuicaoTerritorioSaberIn,
    ApiEolComponenteCurricularHierarquiaIn,
    ApiEolComponenteCurricularIn,
    ApiEolComponenteCurricularPAPIn,
    ApiEolComponenteCurricularPlanejamentoRegenciaIn,
    ApiEolTurmaItinerarioEnsinoMedioIn,
    ComponenteCurricularSimplesIn,
    ComponenteTurmaIn,
    GradeComponenteCurricularIn,
    TurmaIn,
)
from apps.pedagogico.queries import API_EOL_PEDAGOGICO_TABLE_MAPPINGS


class ApiEolPedagogicoTableMappingsTest(SimpleTestCase):
    """Testes do mapeamento Postgres API EOL para Pedagógico."""

    def test_mapeia_tabelas_origem_e_destino(self) -> None:
        esperado = {
            "componente_curricular_api_eol": (
                "componentecurricular, componentecurricularpai",
                "componente_curricular_api_eol",
            ),
            "componentecurricularhierarquia": (
                "componentecurricularpai",
                "componente_curricular_hierarquia",
            ),
            "componentecurricularpap": (
                "componentecurricularpap",
                "componente_curricular_pap",
            ),
            "componentecurricularplanejamentoregencia": (
                "regenciacomponentecurricular",
                "componente_curricular_planejamento_regencia",
            ),
            "turmaitinerarioensinomedio": (
                "turma_tipo_itinerario",
                "turma_itinerario_ensino_medio",
            ),
            "agrupamento_atribuicao_territorio_saber": (
                "agrupamentoatribuicaoterritoriosaber",
                "agrupamento_atribuicao_territorio_saber",
            ),
        }

        obtido = {
            nome: (config["source_table"], config["target_table"])
            for nome, config in API_EOL_PEDAGOGICO_TABLE_MAPPINGS.items()
        }

        self.assertEqual(obtido, esperado)


class ApiEolPedagogicoDtoTest(SimpleTestCase):
    """Testes dos DTOs da fonte Postgres API EOL."""

    def test_componente_curricular_api_eol_com_relacao_pai(self) -> None:
        dto = ApiEolComponenteCurricularIn(
            "10",
            "513",
            True,
            False,
            " Arte ",
            "512",
            datetime(2021, 12, 31, 0, 0, 0),
        )

        data = dto.to_domain("agora")

        self.assertEqual(data["id_relacao_origem"], 10)
        self.assertEqual(data["id_componente_curricular"], 513)
        self.assertTrue(data["eh_regencia"])
        self.assertFalse(data["eh_territorio"])
        self.assertEqual(data["descricao"], "Arte")
        self.assertEqual(data["id_componente_curricular_pai"], 512)
        self.assertTrue(timezone.is_aware(data["vigencia"]))
        self.assertEqual(data["transferido_em"], "agora")

    def test_componente_curricular_api_eol_sem_relacao_pai(self) -> None:
        dto = ApiEolComponenteCurricularIn(
            None,
            "513",
            False,
            True,
            "Território do Saber",
            None,
            None,
        )

        data = dto.to_domain("agora")

        self.assertIsNone(data["id_relacao_origem"])
        self.assertIsNone(data["id_componente_curricular_pai"])
        self.assertIsNone(data["vigencia"])
        self.assertTrue(data["eh_territorio"])

    def test_componente_curricular_api_eol_sem_descricao(self) -> None:
        dto = ApiEolComponenteCurricularIn(
            None,
            "1",
            False,
            False,
            None,
            None,
            None,
        )

        data = dto.to_domain("agora")

        self.assertIsNone(data["descricao"])

    def test_componente_curricular_api_eol_define_transferencia_atual(
        self,
    ) -> None:
        dto = ApiEolComponenteCurricularIn(
            None,
            "1",
            False,
            False,
            "Arte",
            None,
            None,
        )

        antes = timezone.now()
        data = dto.to_domain()
        depois = timezone.now()

        self.assertGreaterEqual(data["transferido_em"], antes)
        self.assertLessEqual(data["transferido_em"], depois)

    def test_componente_curricular_hierarquia(self) -> None:
        dto = ApiEolComponenteCurricularHierarquiaIn(
            1,
            "512",
            "513",
            datetime(2021, 12, 31, 0, 0, 0),
        )

        data = dto.to_domain("agora")

        self.assertEqual(data["id"], 1)
        self.assertEqual(data["id_componente_curricular_pai"], 512)
        self.assertEqual(data["id_componente_curricular"], 513)
        self.assertTrue(timezone.is_aware(data["vigencia"]))
        self.assertEqual(data["transferido_em"], "agora")

    def test_componente_curricular_pap(self) -> None:
        dto = ApiEolComponenteCurricularPAPIn(2, "1322")

        data = dto.to_domain("agora")

        self.assertEqual(
            data,
            {
                "id": 2,
                "id_componente_curricular": 1322,
                "transferido_em": "agora",
            },
        )

    def test_componente_curricular_planejamento_regencia(self) -> None:
        dto = ApiEolComponenteCurricularPlanejamentoRegenciaIn(
            "218",
            None,
            "5",
        )

        data = dto.to_domain("agora")

        self.assertEqual(data["id_componente_curricular"], 218)
        self.assertIsNone(data["turno"])
        self.assertEqual(data["ano"], 5)
        self.assertEqual(data["transferido_em"], "agora")

    def test_turma_itinerario_ensino_medio(self) -> None:
        dto = ApiEolTurmaItinerarioEnsinoMedioIn(
            "9",
            " Investigação cientifica ",
            2,
        )

        data = dto.to_domain("agora")

        self.assertEqual(data["id"], 9)
        self.assertEqual(data["nome"], "Investigação cientifica")
        self.assertEqual(data["serie"], "2")
        self.assertEqual(data["transferido_em"], "agora")

    def test_agrupamento_atribuicao_territorio_saber(self) -> None:
        dto = ApiEolAgrupamentoAtribuicaoTerritorioSaberIn(
            "1",
            "811496",
            "2",
            "68",
            datetime(2025, 2, 3, 0, 0, 0),
            "2025",
            None,
            datetime(2025, 12, 19, 0, 0, 0),
            "8580464",
            "2855275",
            "1214,1215",
            "2025",
            None,
            " I - EDUCOMUNICAÇÃO E NOVAS LINGUAGENS ",
            " CLUBE DA LEITURA ",
            False,
        )

        data = dto.to_domain("agora")

        self.assertEqual(data["cod_agrupamento"], 811496)
        self.assertEqual(data["cod_territorio_saber"], 2)
        self.assertEqual(data["cod_experiencia_pedagogica"], 68)
        self.assertTrue(timezone.is_aware(data["dt_inicio_atribuicao"]))
        self.assertIsNone(data["dt_fim_atribuicao"])
        self.assertEqual(data["rf_professor"], "8580464")
        self.assertEqual(data["cod_turma"], "2855275")
        self.assertEqual(data["cod_componentes_curriculares"], "1214,1215")
        self.assertEqual(data["ano_letivo"], 2025)
        self.assertIsNone(data["cod_motivo_disponibilizacao"])
        self.assertEqual(
            data["desc_territorio_saber"],
            "I - EDUCOMUNICAÇÃO E NOVAS LINGUAGENS",
        )
        self.assertEqual(
            data["desc_experiencia_pedagogica"], "CLUBE DA LEITURA"
        )
        self.assertFalse(
            data["encerramento_atribuicao_agrupamento_atualizado"]
        )
        self.assertEqual(data["transferido_em"], "agora")


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
        self.assertIsNone(data["desc_territorio_saber"])
        self.assertIsNone(data["desc_experiencia_pedagogica"])
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
        "tipo_escola": 1,
        "codigo_grade_programa": 42,
        "descricao_grade_programa": " Programa Mais Educação ",
        "tipo_grade_programa": 7,
        "codigo_tipo_periodicidade": 3,
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
        self.assertEqual(data["tipo_escola"], 1)
        self.assertEqual(data["codigo_grade_programa"], 42)
        self.assertEqual(
            data["descricao_grade_programa"], "Programa Mais Educação"
        )
        self.assertEqual(data["tipo_grade_programa"], 7)
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

    def test_grade_programa_nulos_viram_default(self) -> None:
        """Campos NOT NULL recebem default quando a origem é nula."""
        data = _turma_in_completa(
            tipo_escola=None,
            codigo_grade_programa=None,
            descricao_grade_programa=None,
            tipo_grade_programa=None,
        ).to_domain("agora")

        self.assertEqual(data["tipo_escola"], 0)
        self.assertEqual(data["codigo_grade_programa"], 0)
        self.assertEqual(data["descricao_grade_programa"], "NAO INFORMADA")
        self.assertEqual(data["tipo_grade_programa"], 0)

    def test_descricao_grade_programa_vazia_vira_default(self) -> None:
        data = _turma_in_completa(descricao_grade_programa="   ").to_domain(
            "agora"
        )
        self.assertEqual(data["descricao_grade_programa"], "NAO INFORMADA")

    def test_ordem_posicional_alinha_com_select(self) -> None:
        """As últimas colunas do SELECT mapeiam os campos corretos."""
        row = (
            123456,
            2025,
            "5",
            1,
            " 5A Manhã ",
            5,
            2,
            datetime(2025, 2, 5, 8, 0, 0),
            None,
            0,
            "O",
            "001234",
            datetime(2025, 1, 10, 0, 0, 0),
            None,
            " 5o ano ",
            50,
            " Fundamental ",
            5,
            3,
            5,
            0,
            0,
            5,
            3,
            7,
            42,
            " Programa Mais Educação ",
            9,
            3,
        )

        dto = TurmaIn(*row)
        data = dto.to_domain("agora")

        self.assertEqual(data["tipo_escola"], 7)
        self.assertEqual(data["codigo_grade_programa"], 42)
        self.assertEqual(
            data["descricao_grade_programa"], "Programa Mais Educação"
        )
        self.assertEqual(data["tipo_grade_programa"], 9)
        self.assertEqual(data["codigo_tipo_periodicidade"], 3)
