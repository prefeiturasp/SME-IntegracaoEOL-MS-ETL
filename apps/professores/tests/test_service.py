"""Testes de _row_to_*, _full_refresh, _params_cargo e EtlProfessoresService."""

import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.professores.services import (
    EtlProfessoresService,
    _full_refresh,
    _params_cargo,
    _row_to_atribuicao_aula,
    _row_to_atribuicao_externo,
    _row_to_cargo,
    _row_to_cargo_base,
    _row_to_cargo_sobreposto,
    _row_to_componente_curricular,
    _row_to_contrato_externo,
    _row_to_dre,
    _row_to_escola_grade,
    _row_to_funcao_atividade,
    _row_to_funcao_externo,
    _row_to_grade,
    _row_to_laudo,
    _row_to_lotacao,
    _row_to_pessoa,
    _row_to_professor,
    _row_to_serie_ensino,
    _row_to_serie_turma_grade,
    _row_to_territorio_saber,
    _row_to_tipo_escola,
    _row_to_tipo_experiencia,
    _row_to_turma_escola,
    _row_to_turma_escola_grade_programa,
    _row_to_turma_grade_territorio,
    _row_to_unidade_educacional,
)

# ---------------------------------------------------------------------------
# Transformadores
# ---------------------------------------------------------------------------


class RowToDreTest(TestCase):
    """Testes para a função _row_to_dre."""

    def test_campos_basicos(self) -> None:
        """Verifica que _row_to_dre extrai corretamente os campos básicos."""
        row = ("001", "DRE NORTE", "DN")
        r = _row_to_dre(row)
        self.assertEqual(r["codigo_dre"], "001")
        self.assertEqual(r["nome"], "DRE NORTE")
        self.assertEqual(r["sigla"], "DN")

    def test_sigla_none_quando_vazio(self) -> None:
        """Verifica que sigla None é preservada por _row_to_dre."""
        row = ("001", "DRE NORTE", None)
        r = _row_to_dre(row)
        self.assertIsNone(r["sigla"])

    def test_codigo_e_stripped(self) -> None:
        """Verifica que _row_to_dre remove espaços do código."""
        row = ("  002  ", "DRE SUL", "DS")
        r = _row_to_dre(row)
        self.assertEqual(r["codigo_dre"], "002")


class RowToTipoEscolaTest(TestCase):
    """Testes para a função _row_to_tipo_escola."""

    def test_campos_completos(self) -> None:
        """Verifica que _row_to_tipo_escola extrai todos os campos corretamente."""
        row = (1, "EMEF", "EF")
        r = _row_to_tipo_escola(row)
        self.assertEqual(r["codigo_tipo_escola"], 1)
        self.assertEqual(r["descricao"], "EMEF")
        self.assertEqual(r["sigla"], "EF")

    def test_sigla_none(self) -> None:
        """Verifica que sigla None é preservada por _row_to_tipo_escola."""
        row = (2, "CEI", None)
        r = _row_to_tipo_escola(row)
        self.assertIsNone(r["sigla"])

    def test_descricao_vazia_vira_string_vazia(self) -> None:
        """Verifica que descrição None é convertida para string vazia."""
        row = (3, None, "X")
        r = _row_to_tipo_escola(row)
        self.assertEqual(r["descricao"], "")


class RowToUnidadeEducacionalTest(TestCase):
    """Testes para a função _row_to_unidade_educacional."""

    def test_campos_completos(self) -> None:
        """Verifica que todos os campos da unidade educacional são extraídos."""
        row = ("000001", "ESCOLA A", "EA", "001", "DRE NORTE", "DN", 1, "EF")
        r = _row_to_unidade_educacional(row)
        self.assertEqual(r["codigo_ue"], "000001")
        self.assertEqual(r["nome"], "ESCOLA A")
        self.assertEqual(r["sigla"], "EA")
        self.assertEqual(r["dre_id"], "001")
        self.assertEqual(r["nome_dre"], "DRE NORTE")
        self.assertEqual(r["sigla_dre"], "DN")
        self.assertEqual(r["tipo_escola_id"], 1)
        self.assertEqual(r["sigla_tipo_escola"], "EF")

    def test_dre_none(self) -> None:
        """Verifica que dre_id e sigla None são preservados."""
        row = ("000001", "ESCOLA A", None, None, None, None, None, None)
        r = _row_to_unidade_educacional(row)
        self.assertIsNone(r["dre_id"])
        self.assertIsNone(r["sigla"])


class RowToComponenteCurricularTest(TestCase):
    """Testes para a função _row_to_componente_curricular."""

    def test_campos(self) -> None:
        """Verifica que todos os campos do componente curricular são extraídos."""
        row = (10, "MATEMATICA", datetime.date(2020, 1, 1))
        r = _row_to_componente_curricular(row)
        self.assertEqual(r["codigo"], 10)
        self.assertEqual(r["descricao"], "MATEMATICA")
        self.assertEqual(r["dt_cancelamento"], datetime.date(2020, 1, 1))

    def test_descricao_none_vira_string_vazia(self) -> None:
        """Verifica que descrição None é convertida para string vazia."""
        row = (10, None, None)
        r = _row_to_componente_curricular(row)
        self.assertEqual(r["descricao"], "")


class RowToSerieEnsinoTest(TestCase):
    """Testes para a função _row_to_serie_ensino."""

    def test_campos(self) -> None:
        """Verifica que os campos da série de ensino são extraídos corretamente."""
        row = (5, "5A")
        r = _row_to_serie_ensino(row)
        self.assertEqual(r["codigo_serie"], 5)
        self.assertEqual(r["sigla_resumida"], "5A")

    def test_sigla_none(self) -> None:
        """Verifica que sigla_resumida None é preservada."""
        row = (5, None)
        r = _row_to_serie_ensino(row)
        self.assertIsNone(r["sigla_resumida"])


class RowToTerritorioSaberTest(TestCase):
    """Testes para a função _row_to_territorio_saber."""

    def test_campos(self) -> None:
        """Verifica que os campos do território do saber são extraídos."""
        row = (1, "TERRITORIO 1")
        r = _row_to_territorio_saber(row)
        self.assertEqual(r["codigo_territorio"], 1)
        self.assertEqual(r["descricao"], "TERRITORIO 1")

    def test_descricao_none(self) -> None:
        """Verifica que descrição None é convertida para string vazia."""
        row = (1, None)
        r = _row_to_territorio_saber(row)
        self.assertEqual(r["descricao"], "")


class RowToTipoExperienciaTest(TestCase):
    """Testes para a função _row_to_tipo_experiencia."""

    def test_campos(self) -> None:
        """Verifica que os campos do tipo de experiência são extraídos."""
        row = (2, "EXPERIENCIA A")
        r = _row_to_tipo_experiencia(row)
        self.assertEqual(r["codigo_experiencia"], 2)
        self.assertEqual(r["descricao"], "EXPERIENCIA A")


class RowToGradeTest(TestCase):
    """Testes para a função _row_to_grade."""

    def test_campos(self) -> None:
        """Verifica que os campos da grade são extraídos corretamente."""
        row = (100, 5, 1)
        r = _row_to_grade(row)
        self.assertEqual(r["codigo_grade"], 100)
        self.assertEqual(r["codigo_serie_ensino"], 5)
        self.assertEqual(r["codigo_tipo_turno"], 1)


class RowToEscolaGradeTest(TestCase):
    """Testes para a função _row_to_escola_grade."""

    def test_campos(self) -> None:
        """Verifica que os campos da escola-grade são extraídos corretamente."""
        row = (50, "000001", 100)
        r = _row_to_escola_grade(row)
        self.assertEqual(r["codigo_escola_grade"], 50)
        self.assertEqual(r["codigo_escola"], "000001")
        self.assertEqual(r["grade_id"], 100)

    def test_escola_stripped(self) -> None:
        """Verifica que o código da escola tem espaços removidos."""
        row = (50, "  000001  ", 100)
        r = _row_to_escola_grade(row)
        self.assertEqual(r["codigo_escola"], "000001")


class RowToTurmaEscolaTest(TestCase):
    """Testes para a função _row_to_turma_escola."""

    def test_campos(self) -> None:
        """Verifica que os campos da turma escola são extraídos corretamente."""
        dt = datetime.date(2024, 2, 1)
        row = (9999, "000001", 2024, "TURMA A", 1, 2, 3, "A", dt, dt, None)
        r = _row_to_turma_escola(row)
        self.assertEqual(r["codigo_turma"], 9999)
        self.assertEqual(r["codigo_escola"], "000001")
        self.assertEqual(r["ano_letivo"], 2024)
        self.assertEqual(r["nome_turma"], "TURMA A")
        self.assertEqual(r["status"], "A")
        self.assertIsNone(r["dt_fim"])


class RowToSerieTurmaGradeTest(TestCase):
    """Testes para a função _row_to_serie_turma_grade."""

    def test_campos(self) -> None:
        """Verifica que os campos da série-turma-grade são extraídos."""
        row = (200, 9999, "000001", 50, datetime.date(2024, 12, 31))
        r = _row_to_serie_turma_grade(row)
        self.assertEqual(r["codigo_serie_grade"], 200)
        self.assertEqual(r["turma_id"], 9999)
        self.assertEqual(r["codigo_escola"], "000001")
        self.assertEqual(r["escola_grade_id"], 50)


class RowToTurmaEscolaGradeProgramaTest(TestCase):
    """Testes para a função _row_to_turma_escola_grade_programa."""

    def test_campos(self) -> None:
        """Verifica que os campos da turma-escola-grade-programa são extraídos."""
        row = (300, 9999, 50, None)
        r = _row_to_turma_escola_grade_programa(row)
        self.assertEqual(r["codigo"], 300)
        self.assertEqual(r["turma_id"], 9999)
        self.assertEqual(r["escola_grade_id"], 50)
        self.assertIsNone(r["dt_fim"])


class RowToTurmaGradeTerritorioTest(TestCase):
    """Testes para a função _row_to_turma_grade_territorio."""

    def test_campos(self) -> None:
        """Verifica que os campos da turma-grade-território são extraídos."""
        row = (200, 10, 1, 2, datetime.date(2024, 1, 1))
        r = _row_to_turma_grade_territorio(row)
        self.assertEqual(r["serie_grade_id"], 200)
        self.assertEqual(r["codigo_componente_curricular"], 10)
        self.assertEqual(r["territorio_saber_id"], 1)
        self.assertEqual(r["experiencia_pedagogica_id"], 2)


class RowToCargoTest(TestCase):
    """Testes para a função _row_to_cargo."""

    def test_campos(self) -> None:
        """Verifica que os campos do cargo são extraídos corretamente."""
        row = (3239, "PEB I")
        r = _row_to_cargo(row)
        self.assertEqual(r["codigo_cargo"], 3239)
        self.assertEqual(r["descricao"], "PEB I")

    def test_descricao_none(self) -> None:
        """Verifica que descrição None é convertida para string vazia."""
        row = (3239, None)
        r = _row_to_cargo(row)
        self.assertEqual(r["descricao"], "")


class RowToProfessorTest(TestCase):
    """Testes para a função _row_to_professor."""

    def test_campos(self) -> None:
        """Verifica que os campos do professor são extraídos corretamente."""
        row = ("012345", "ANA SILVA", "Ana")
        r = _row_to_professor(row)
        self.assertEqual(r["codigo_rf"], "012345")
        self.assertEqual(r["nome"], "ANA SILVA")
        self.assertEqual(r["nome_social"], "Ana")

    def test_nome_social_none(self) -> None:
        """Verifica que nome_social None é preservado."""
        row = ("012345", "ANA SILVA", None)
        r = _row_to_professor(row)
        self.assertIsNone(r["nome_social"])

    def test_rf_stripped(self) -> None:
        """Verifica que o código RF tem espaços removidos."""
        row = ("  012345  ", "ANA SILVA", None)
        r = _row_to_professor(row)
        self.assertEqual(r["codigo_rf"], "012345")


class RowToCargoBaseTest(TestCase):
    """Testes para a função _row_to_cargo_base."""

    def test_campos(self) -> None:
        """Verifica que os campos do cargo base são extraídos corretamente."""
        dt = datetime.date(2020, 1, 1)
        row = (1001, "012345", 3239, dt, None, None)
        r = _row_to_cargo_base(row)
        self.assertEqual(r["id"], 1001)
        self.assertEqual(r["professor_id"], "012345")
        self.assertEqual(r["cargo_id"], 3239)
        self.assertEqual(r["dt_posse"], dt)


class RowToLotacaoTest(TestCase):
    """Testes para a função _row_to_lotacao."""

    def test_campos(self) -> None:
        """Verifica que os campos da lotação são extraídos corretamente."""
        row = (1001, "000001", datetime.date(2020, 1, 1), None)
        r = _row_to_lotacao(row)
        self.assertEqual(r["cargo_base_id"], 1001)
        self.assertEqual(r["codigo_unidade_educacao"], "000001")
        self.assertIsNone(r["dt_fim"])


class RowToCargoSobrepostoTest(TestCase):
    """Testes para a função _row_to_cargo_sobreposto."""

    def test_campos(self) -> None:
        """Verifica que os campos do cargo sobreposto são extraídos."""
        row = (1001, 3247, "000001", datetime.date(2024, 12, 31))
        r = _row_to_cargo_sobreposto(row)
        self.assertEqual(r["cargo_base_id"], 1001)
        self.assertEqual(r["cargo_id"], 3247)
        self.assertEqual(r["codigo_unidade_local_servico"], "000001")


class RowToFuncaoAtividadeTest(TestCase):
    """Testes para a função _row_to_funcao_atividade."""

    def test_campos(self) -> None:
        """Verifica que os campos da função de atividade são extraídos."""
        row = (1001, "000001", datetime.date(2024, 6, 30))
        r = _row_to_funcao_atividade(row)
        self.assertEqual(r["cargo_base_id"], 1001)
        self.assertEqual(r["codigo_unidade_local_servico"], "000001")


class RowToLaudoTest(TestCase):
    """Testes para a função _row_to_laudo."""

    def test_campos(self) -> None:
        """Verifica que os campos do laudo médico são extraídos."""
        row = (1001,)
        r = _row_to_laudo(row)
        self.assertEqual(r["cargo_base_id"], 1001)


class RowToFuncaoExternoTest(TestCase):
    """Testes para a função _row_to_funcao_externo."""

    def test_campos(self) -> None:
        """Verifica que os campos da função externo são extraídos corretamente."""
        row = (10, "FUNCAO X", None)
        r = _row_to_funcao_externo(row)
        self.assertEqual(r["codigo_tipo_funcao"], 10)
        self.assertEqual(r["descricao"], "FUNCAO X")
        self.assertIsNone(r["dt_cancelamento"])


class RowToPessoaTest(TestCase):
    """Testes para a função _row_to_pessoa."""

    def test_campos(self) -> None:
        """Verifica que os campos da pessoa são extraídos corretamente."""
        row = (500, "123.456.789-00", "JOSE", None)
        r = _row_to_pessoa(row)
        self.assertEqual(r["codigo_pessoa"], 500)
        self.assertEqual(r["cpf"], "123.456.789-00")
        self.assertEqual(r["nome"], "JOSE")
        self.assertIsNone(r["nome_social"])


class RowToContratoExternoTest(TestCase):
    """Testes para a função _row_to_contrato_externo."""

    def test_campos(self) -> None:
        """Verifica que os campos do contrato externo são extraídos corretamente."""
        row = (800, 500, 10, "000001", None, None)
        r = _row_to_contrato_externo(row)
        self.assertEqual(r["codigo_contrato"], 800)
        self.assertEqual(r["pessoa_id"], 500)
        self.assertEqual(r["tipo_funcao_id"], 10)
        self.assertEqual(r["codigo_unidade_educacao"], "000001")


class RowToAtribuicaoAulaTest(TestCase):
    """Testes para a função _row_to_atribuicao_aula."""

    def test_campos(self) -> None:
        """Verifica que os campos da atribuição de aula são extraídos."""
        dt = datetime.date(2024, 2, 1)
        row = (9001, 1001, "000001", 9999, None, 100, 10, 200, 2024, dt, dt, None, None)
        r = _row_to_atribuicao_aula(row)
        self.assertEqual(r["id"], 9001)
        self.assertEqual(r["cargo_base_id"], 1001)
        self.assertEqual(r["codigo_turma_escola"], 9999)
        self.assertEqual(r["ano_atribuicao"], 2024)


class RowToAtribuicaoExternoTest(TestCase):
    """Testes para a função _row_to_atribuicao_externo."""

    def test_campos(self) -> None:
        """Verifica que os campos da atribuição externo são extraídos."""
        dt = datetime.date(2024, 2, 1)
        row = (9002, 800, "000001", 100, 10, 200, None, 2024, dt, dt, None, None)
        r = _row_to_atribuicao_externo(row)
        self.assertEqual(r["id"], 9002)
        self.assertEqual(r["contrato_externo_id"], 800)
        self.assertEqual(r["ano_atribuicao"], 2024)


# ---------------------------------------------------------------------------
# _params_cargo e _full_refresh
# ---------------------------------------------------------------------------


class ParamsCargoTest(TestCase):
    """Testes para a função _params_cargo."""

    def test_retorna_dict_com_indices(self) -> None:
        """Verifica que _params_cargo retorna um dicionário com índices inteiros."""
        params = _params_cargo()
        self.assertIsInstance(params, dict)
        self.assertIn(0, params)

    def test_valores_sao_cargos_professor(self) -> None:
        """Verifica que os valores correspondem à lista CARGOS_PROFESSOR."""
        from apps.professores.services import CARGOS_PROFESSOR

        params = _params_cargo()
        self.assertEqual(list(params.values()), list(CARGOS_PROFESSOR))


class FullRefreshTest(TestCase):
    """Testes para a função _full_refresh."""

    databases = ["default", "professores_db"]

    def test_lista_vazia_retorna_zero(self) -> None:
        """Verifica que _full_refresh retorna zero para lista vazia."""
        from apps.professores.models import DRE

        resultado = _full_refresh(DRE, [])
        self.assertEqual(resultado, 0)

    def test_cria_registros(self) -> None:
        """Verifica que _full_refresh cria os registros fornecidos."""
        from apps.professores.models import DRE

        objs = [DRE(codigo_dre="T01", nome="DRE TESTE")]
        resultado = _full_refresh(DRE, objs)
        self.assertEqual(resultado, 1)
        self.assertEqual(DRE.objects.using("professores_db").count(), 1)

    def test_substitui_registros_existentes(self) -> None:
        """_full_refresh substitui completamente os registros existentes."""
        from apps.professores.models import DRE

        _full_refresh(DRE, [DRE(codigo_dre="T01", nome="DRE ANTIGA")])
        resultado = _full_refresh(DRE, [DRE(codigo_dre="T02", nome="DRE NOVA")])
        self.assertEqual(resultado, 1)
        self.assertFalse(
            DRE.objects.using("professores_db").filter(codigo_dre="T01").exists()
        )
        self.assertTrue(
            DRE.objects.using("professores_db").filter(codigo_dre="T02").exists()
        )


# ---------------------------------------------------------------------------
# EtlProfessoresService
# ---------------------------------------------------------------------------

_EOL_PATCH = "apps.professores.services.EOLService"
_UPSERT_PATCH = "apps.professores.services._upsert_incremental"
_FULL_REFRESH_PATCH = "apps.professores.services._full_refresh"


def _make_eol_mock(**query_returns):  # type: ignore[no-untyped-def]
    """Cria mock de EOLService com executar_query retornando listas vazias."""
    mock = MagicMock()
    mock.executar_query.return_value = []
    return mock


class EtlProfessoresServiceFase1Test(TestCase):
    """Testes dos métodos de população da fase 1 do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    @patch(_UPSERT_PATCH, return_value=5)
    @patch(_EOL_PATCH)
    def test_popular_dre(self, mock_eol: MagicMock, mock_upsert: MagicMock) -> None:
        """Verifica que popular_dre chama upsert e retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [("001", "DRE NORTE", "DN")]
        srv = EtlProfessoresService()
        resultado = srv.popular_dre()
        self.assertEqual(resultado, 5)
        mock_upsert.assert_called_once()

    @patch(_UPSERT_PATCH, return_value=3)
    @patch(_EOL_PATCH)
    def test_popular_tipos_escola(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_tipos_escola retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [(1, "EMEF", "EF")]
        srv = EtlProfessoresService()
        resultado = srv.popular_tipos_escola()
        self.assertEqual(resultado, 3)

    @patch(_UPSERT_PATCH, return_value=10)
    @patch(_EOL_PATCH)
    def test_popular_componentes_curriculares(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_componentes_curriculares retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [(10, "MAT", None)]
        srv = EtlProfessoresService()
        resultado = srv.popular_componentes_curriculares()
        self.assertEqual(resultado, 10)

    @patch(_UPSERT_PATCH, return_value=4)
    @patch(_EOL_PATCH)
    def test_popular_series_ensino(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_series_ensino retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [(5, "5A")]
        srv = EtlProfessoresService()
        resultado = srv.popular_series_ensino()
        self.assertEqual(resultado, 4)

    @patch(_UPSERT_PATCH, return_value=2)
    @patch(_EOL_PATCH)
    def test_popular_territorios_saber(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_territorios_saber retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [(1, "TDS 1")]
        srv = EtlProfessoresService()
        resultado = srv.popular_territorios_saber()
        self.assertEqual(resultado, 2)

    @patch(_UPSERT_PATCH, return_value=1)
    @patch(_EOL_PATCH)
    def test_popular_tipos_experiencia(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_tipos_experiencia retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [(1, "EXP A")]
        srv = EtlProfessoresService()
        resultado = srv.popular_tipos_experiencia()
        self.assertEqual(resultado, 1)

    @patch(_UPSERT_PATCH, return_value=7)
    @patch(_EOL_PATCH)
    def test_popular_grades(self, mock_eol: MagicMock, mock_upsert: MagicMock) -> None:
        """Verifica que popular_grades retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [(100, 5, 1)]
        srv = EtlProfessoresService()
        resultado = srv.popular_grades()
        self.assertEqual(resultado, 7)

    @patch(_UPSERT_PATCH, return_value=2)
    @patch(_EOL_PATCH)
    def test_popular_cargos(self, mock_eol: MagicMock, mock_upsert: MagicMock) -> None:
        """Verifica que popular_cargos retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [(3239, "PEB I")]
        srv = EtlProfessoresService()
        resultado = srv.popular_cargos()
        self.assertEqual(resultado, 2)

    @patch(_UPSERT_PATCH, return_value=1)
    @patch(_EOL_PATCH)
    def test_popular_funcoes_funcionario_externo(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_funcoes_funcionario_externo retorna a contagem."""
        mock_eol.return_value.executar_query.return_value = [(10, "FUNCAO X", None)]
        srv = EtlProfessoresService()
        resultado = srv.popular_funcoes_funcionario_externo()
        self.assertEqual(resultado, 1)


class EtlProfessoresServiceFase2Test(TestCase):
    """Testes dos métodos de população da fase 2 do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    @patch(_FULL_REFRESH_PATCH, return_value=3)
    @patch(_EOL_PATCH)
    def test_popular_unidades_educacionais(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """popular_unidades_educacionais chama refresh e retorna contagem."""
        mock_eol.return_value.executar_query.return_value = [
            ("000001", "ESCOLA A", None, "001", "DRE NORTE", "DN", 1, "EF")
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_unidades_educacionais()
        self.assertEqual(resultado, 3)
        mock_refresh.assert_called_once()

    @patch(_UPSERT_PATCH, return_value=2)
    @patch(_EOL_PATCH)
    def test_popular_escola_grades(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_escola_grades retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [(50, "000001", 100)]
        srv = EtlProfessoresService()
        resultado = srv.popular_escola_grades()
        self.assertEqual(resultado, 2)

    @patch(_UPSERT_PATCH, return_value=5)
    @patch(_EOL_PATCH)
    def test_popular_turmas_escola(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_turmas_escola retorna a contagem correta."""
        dt = datetime.date(2024, 2, 1)
        mock_eol.return_value.executar_query.return_value = [
            (9999, "000001", 2024, "TURMA A", 1, 2, 3, "A", dt, dt, None)
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_turmas_escola()
        self.assertEqual(resultado, 5)

    @patch(_UPSERT_PATCH, return_value=4)
    @patch(_EOL_PATCH)
    def test_popular_professores(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_professores retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [
            ("012345", "ANA SILVA", None)
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_professores()
        self.assertEqual(resultado, 4)

    @patch(_UPSERT_PATCH, return_value=1)
    @patch(_EOL_PATCH)
    def test_popular_pessoas(self, mock_eol: MagicMock, mock_upsert: MagicMock) -> None:
        """Verifica que popular_pessoas retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [
            (500, "123.456.789-00", "JOSE", None)
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_pessoas()
        self.assertEqual(resultado, 1)


class EtlProfessoresServiceFase3Test(TestCase):
    """Testes dos métodos de população da fase 3 do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    @patch(_UPSERT_PATCH, return_value=2)
    @patch(_EOL_PATCH)
    def test_popular_serie_turma_grade(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_serie_turma_grade retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [
            (200, 9999, "000001", 50, None)
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_serie_turma_grade()
        self.assertEqual(resultado, 2)

    @patch(_UPSERT_PATCH, return_value=1)
    @patch(_EOL_PATCH)
    def test_popular_turma_escola_grade_programa(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_turma_escola_grade_programa retorna a contagem."""
        mock_eol.return_value.executar_query.return_value = [(300, 9999, 50, None)]
        srv = EtlProfessoresService()
        resultado = srv.popular_turma_escola_grade_programa()
        self.assertEqual(resultado, 1)

    @patch(_UPSERT_PATCH, return_value=10)
    @patch(_EOL_PATCH)
    def test_popular_cargos_base(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_cargos_base retorna a contagem correta."""
        dt = datetime.date(2020, 1, 1)
        mock_eol.return_value.executar_query.return_value = [
            (1001, "012345", 3239, dt, None, None)
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_cargos_base()
        self.assertEqual(resultado, 10)

    @patch(_UPSERT_PATCH, return_value=3)
    @patch(_EOL_PATCH)
    def test_popular_contratos_externos(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_contratos_externos retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [
            (800, 500, 10, "000001", None, None)
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_contratos_externos()
        self.assertEqual(resultado, 3)


class EtlProfessoresServiceFase4Test(TestCase):
    """Testes dos métodos de população da fase 4 do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    @patch(_FULL_REFRESH_PATCH, return_value=2)
    @patch(_EOL_PATCH)
    def test_popular_turma_grade_territorio_experiencia(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica que popular_turma_grade_territorio_experiencia retorna contagem."""
        mock_eol.return_value.executar_query.return_value = [
            (200, 10, 1, 2, datetime.date(2024, 1, 1))
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_turma_grade_territorio_experiencia()
        self.assertEqual(resultado, 2)

    @patch(_FULL_REFRESH_PATCH, return_value=5)
    @patch(_EOL_PATCH)
    def test_popular_lotacoes(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica que popular_lotacoes retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [
            (1001, "000001", datetime.date(2020, 1, 1), None)
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_lotacoes()
        self.assertEqual(resultado, 5)

    @patch(_FULL_REFRESH_PATCH, return_value=3)
    @patch(_EOL_PATCH)
    def test_popular_cargos_sobrepostos(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica que popular_cargos_sobrepostos retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [
            (1001, 3247, "000001", datetime.date(2024, 12, 31))
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_cargos_sobrepostos()
        self.assertEqual(resultado, 3)

    @patch(_FULL_REFRESH_PATCH, return_value=4)
    @patch(_EOL_PATCH)
    def test_popular_funcoes_atividade(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica que popular_funcoes_atividade retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [
            (1001, "000001", datetime.date(2024, 6, 30))
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_funcoes_atividade()
        self.assertEqual(resultado, 4)

    @patch(_FULL_REFRESH_PATCH, return_value=1)
    @patch(_EOL_PATCH)
    def test_popular_laudos(self, mock_eol: MagicMock, mock_refresh: MagicMock) -> None:
        """Verifica que popular_laudos retorna a contagem correta."""
        mock_eol.return_value.executar_query.return_value = [(1001,)]
        srv = EtlProfessoresService()
        resultado = srv.popular_laudos()
        self.assertEqual(resultado, 1)

    @patch(_UPSERT_PATCH, return_value=20)
    @patch(_EOL_PATCH)
    def test_popular_atribuicoes_aula(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_atribuicoes_aula retorna a contagem correta."""
        dt = datetime.date(2024, 2, 1)
        mock_eol.return_value.executar_query.return_value = [
            (9001, 1001, "000001", 9999, None, 100, 10, 200, 2024, dt, dt, None, None)
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_atribuicoes_aula()
        self.assertEqual(resultado, 20)

    @patch(_UPSERT_PATCH, return_value=8)
    @patch(_EOL_PATCH)
    def test_popular_atribuicoes_externo(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_atribuicoes_externo retorna a contagem correta."""
        dt = datetime.date(2024, 2, 1)
        mock_eol.return_value.executar_query.return_value = [
            (9002, 800, "000001", 100, 10, 200, None, 2024, dt, dt, None, None)
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_atribuicoes_externo()
        self.assertEqual(resultado, 8)


class EtlProfessoresServiceExecutarTest(TestCase):
    """Testes para o método executar do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    def _make_service_com_populares_mockados(
        self, retorno: int = 0
    ) -> EtlProfessoresService:
        """Cria serviço com todos os métodos popular_* mockados."""
        with patch(_EOL_PATCH):
            srv = EtlProfessoresService()
        metodos_popular = [m for m in dir(srv) if m.startswith("popular_")]
        for nome in metodos_popular:
            setattr(srv, nome, MagicMock(return_value=retorno))
        return srv

    def test_executar_fase1_completa_todas_as_fases(self) -> None:
        """Verifica que executar com fase_inicial=1 completa todas as fases."""
        srv = self._make_service_com_populares_mockados(1)
        resultado = srv.executar(fase_inicial=1)
        self.assertEqual(srv.ultima_fase_concluida, 4)
        self.assertIn("dre", resultado)
        self.assertIn("atribuicao_aula", resultado)

    def test_executar_fase2_pula_fase1(self) -> None:
        """Verifica que executar com fase_inicial=2 pula os dados da fase 1."""
        srv = self._make_service_com_populares_mockados(1)
        resultado = srv.executar(fase_inicial=2)
        self.assertEqual(srv.ultima_fase_concluida, 4)
        self.assertNotIn("dre", resultado)
        self.assertIn("unidade_educacional", resultado)

    def test_executar_fase3_pula_fases_1_e_2(self) -> None:
        """Verifica que executar com fase_inicial=3 pula as fases 1 e 2."""
        srv = self._make_service_com_populares_mockados(1)
        resultado = srv.executar(fase_inicial=3)
        self.assertNotIn("dre", resultado)
        self.assertNotIn("unidade_educacional", resultado)
        self.assertIn("cargo_base_servidor", resultado)

    def test_executar_fase4_somente_ultima_fase(self) -> None:
        """Verifica que executar com fase_inicial=4 executa apenas a última fase."""
        srv = self._make_service_com_populares_mockados(1)
        resultado = srv.executar(fase_inicial=4)
        self.assertNotIn("cargo_base_servidor", resultado)
        self.assertIn("atribuicao_aula", resultado)
        self.assertEqual(srv.ultima_fase_concluida, 4)

    def test_executar_retorna_soma_de_registros(self) -> None:
        """Verifica que executar retorna a soma correta de registros por tabela."""
        srv = self._make_service_com_populares_mockados(3)
        resultado = srv.executar(fase_inicial=1)
        self.assertTrue(all(v == 3 for v in resultado.values()))
