"""Testes de _row_to_*, _full_refresh e EtlProfessoresService."""

import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.professores.services import (
    EtlProfessoresService,
    _full_refresh,
    _params_cargo,
    _row_to_atribuicao_aula,
    _row_to_atribuicao_externo,
    _row_to_cargo_base,
    _row_to_cargo_sobreposto,
    _row_to_contrato_externo,
    _row_to_funcao_atividade,
    _row_to_laudo,
    _row_to_lotacao,
    _row_to_pessoa,
    _row_to_professor,
    _row_to_serie_turma_grade,
    _row_to_turma_escola,
    _row_to_turma_escola_grade_programa,
    _row_to_turma_grade_territorio,
    _row_to_unidade_educacional,
)

# ---------------------------------------------------------------------------
# Transformadores
# ---------------------------------------------------------------------------


class RowToUnidadeEducacionalTest(TestCase):
    """Testes para a função _row_to_unidade_educacional."""

    def test_campos_completos(self) -> None:
        """Verifica que os IDs da unidade educacional são extraídos."""
        row = ("000001", "001", 1)
        r = _row_to_unidade_educacional(row)
        self.assertEqual(r["codigo_ue"], "000001")
        self.assertEqual(r["codigo_dre"], "001")
        self.assertEqual(r["codigo_tipo_escola"], 1)

    def test_dre_none(self) -> None:
        """Verifica que dre None é preservado."""
        row = ("000001", None, None)
        r = _row_to_unidade_educacional(row)
        self.assertIsNone(r["codigo_dre"])
        self.assertIsNone(r["codigo_tipo_escola"])

    def test_codigo_stripped(self) -> None:
        """Verifica que o código da UE tem espaços removidos."""
        row = ("  000001  ", "001", 1)
        r = _row_to_unidade_educacional(row)
        self.assertEqual(r["codigo_ue"], "000001")


class RowToTurmaEscolaTest(TestCase):
    """Testes para a função _row_to_turma_escola."""

    def test_campos(self) -> None:
        """Verifica que os campos da turma escola são extraídos corretamente.

        Ordem das colunas (após adição de tipo_turma e dt_inicio_turma):
            cd_turma_escola, cd_escola, an_letivo, st_turma_escola,
            cd_tipo_turma, dt_inicio_turma, dt_fim_turma, dt_fim
        """
        dt_inicio = datetime.date(2024, 2, 1)
        dt_fim = datetime.date(2024, 12, 20)
        row = (9999, "000001", 2024, "A", 1, dt_inicio, dt_fim, None)
        r = _row_to_turma_escola(row)
        self.assertEqual(r["codigo_turma"], 9999)
        self.assertEqual(r["codigo_escola"], "000001")
        self.assertEqual(r["ano_letivo"], 2024)
        self.assertEqual(r["status"], "A")
        self.assertEqual(r["tipo_turma"], 1)
        self.assertEqual(r["dt_inicio_turma"], dt_inicio)
        self.assertEqual(r["dt_fim_turma"], dt_fim)
        self.assertIsNone(r["dt_fim"])

    def test_tipo_turma_programa(self) -> None:
        """Verifica tipo_turma=3 (Programa) é extraído corretamente."""
        row = (1111, "000002", 2025, "O", 3, None, None, None)
        r = _row_to_turma_escola(row)
        self.assertEqual(r["tipo_turma"], 3)
        self.assertIsNone(r["dt_inicio_turma"])


class RowToSerieTurmaGradeTest(TestCase):
    """Testes para a função _row_to_serie_turma_grade."""

    def test_campos(self) -> None:
        """Verifica que os campos da série-turma-grade são extraídos."""
        row = (200, 9999, "000001", 50, datetime.date(2024, 12, 31))
        r = _row_to_serie_turma_grade(row)
        self.assertEqual(r["codigo_serie_grade"], 200)
        self.assertEqual(r["codigo_turma"], 9999)
        self.assertEqual(r["codigo_escola"], "000001")
        self.assertEqual(r["codigo_escola_grade"], 50)


class RowToTurmaEscolaGradeProgramaTest(TestCase):
    """Testes para a função _row_to_turma_escola_grade_programa."""

    def test_campos(self) -> None:
        """Verifica campos da turma-escola-grade-programa extraídos."""
        row = (300, 9999, 50, None)
        r = _row_to_turma_escola_grade_programa(row)
        self.assertEqual(r["codigo"], 300)
        self.assertEqual(r["codigo_turma"], 9999)
        self.assertEqual(r["codigo_escola_grade"], 50)
        self.assertIsNone(r["dt_fim"])


class RowToTurmaGradeTerritorioTest(TestCase):
    """Testes para a função _row_to_turma_grade_territorio."""

    def test_campos(self) -> None:
        """Verifica que os campos da turma-grade-território são extraídos."""
        row = (200, 10, 1, 2, datetime.date(2024, 1, 1))
        r = _row_to_turma_grade_territorio(row)
        self.assertEqual(r["codigo_serie_grade"], 200)
        self.assertEqual(r["codigo_componente_curricular"], 10)
        self.assertEqual(r["codigo_territorio_saber"], 1)
        self.assertEqual(r["codigo_experiencia_pedagogica"], 2)


class RowToProfessorTest(TestCase):
    """Testes para a função _row_to_professor."""

    def test_campos(self) -> None:
        """Verifica que os campos do professor são extraídos corretamente.

        Ordem das colunas (após adição de cd_cpf_pessoa):
            cd_registro_funcional, nm_pessoa, nm_social, cd_cpf_pessoa
        """
        row = ("012345", "ANA SILVA", "Ana", "123.456.789-00")
        r = _row_to_professor(row)
        self.assertEqual(r["codigo_rf"], "012345")
        self.assertEqual(r["nome"], "ANA SILVA")
        self.assertEqual(r["nome_social"], "Ana")
        self.assertEqual(r["cpf"], "123.456.789-00")

    def test_nome_social_none(self) -> None:
        """Verifica que nome_social None é preservado."""
        row = ("012345", "ANA SILVA", None, None)
        r = _row_to_professor(row)
        self.assertIsNone(r["nome_social"])
        self.assertIsNone(r["cpf"])

    def test_rf_stripped(self) -> None:
        """Verifica que o código RF tem espaços removidos."""
        row = ("  012345  ", "ANA SILVA", None, None)
        r = _row_to_professor(row)
        self.assertEqual(r["codigo_rf"], "012345")


class RowToCargoBaseTest(TestCase):
    """Testes para a função _row_to_cargo_base."""

    def test_campos(self) -> None:
        """Verifica que os campos do cargo base são extraídos corretamente.

        Ordem das colunas (após adição de cd_situacao_funcional):
            cd_cargo_base_servidor, cd_registro_funcional, cd_cargo,
            cd_situacao_funcional, dt_posse, dt_fim_nomeacao,
            dt_cancelamento
        """
        dt = datetime.date(2020, 1, 1)
        row = (1001, "012345", 3239, 6, dt, None, None)
        r = _row_to_cargo_base(row)
        self.assertEqual(r["id"], 1001)
        self.assertEqual(r["professor_id"], "012345")
        self.assertEqual(r["codigo_cargo"], 3239)
        self.assertEqual(r["situacao_funcional"], 6)
        self.assertEqual(r["dt_posse"], dt)

    def test_situacao_funcional_none(self) -> None:
        """Verifica que situacao_funcional None é preservado."""
        dt = datetime.date(2020, 1, 1)
        row = (1002, "012346", 3247, None, dt, None, None)
        r = _row_to_cargo_base(row)
        self.assertIsNone(r["situacao_funcional"])


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
        self.assertEqual(r["codigo_cargo"], 3247)
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
        """Verifica que os campos do contrato externo são extraídos."""
        row = (800, 500, 10, "000001", None, None)
        r = _row_to_contrato_externo(row)
        self.assertEqual(r["codigo_contrato"], 800)
        self.assertEqual(r["pessoa_id"], 500)
        self.assertEqual(r["codigo_tipo_funcao"], 10)
        self.assertEqual(r["codigo_unidade_educacao"], "000001")


class RowToAtribuicaoAulaTest(TestCase):
    """Testes para a função _row_to_atribuicao_aula."""

    def test_campos(self) -> None:
        """Verifica que os campos da atribuição de aula são extraídos."""
        dt = datetime.date(2024, 2, 1)
        row = (
            9001,
            1001,
            "000001",
            9999,
            None,
            100,
            10,
            200,
            2024,
            dt,
            dt,
            None,
            None,
        )
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
        row = (
            9002,
            800,
            "000001",
            100,
            10,
            200,
            None,
            2024,
            dt,
            dt,
            None,
            None,
        )
        r = _row_to_atribuicao_externo(row)
        self.assertEqual(r["id"], 9002)
        self.assertEqual(r["contrato_externo_id"], 800)
        self.assertEqual(r["ano_atribuicao"], 2024)


# ---------------------------------------------------------------------------
# _params_cargo e _full_refresh
# ---------------------------------------------------------------------------


class ParamsCargoTest(TestCase):
    """Testes para a função _params_cargo."""

    def test_retorna_lista(self) -> None:
        """Verifica que _params_cargo retorna uma lista."""
        params = _params_cargo()
        self.assertIsInstance(params, list)
        self.assertTrue(len(params) > 0)

    def test_valores_sao_cargos_professor(self) -> None:
        """Verifica que os valores correspondem à lista CARGOS_PROFESSOR."""
        from apps.professores.services import CARGOS_PROFESSOR

        params = _params_cargo()
        self.assertEqual(params, list(CARGOS_PROFESSOR))


class FullRefreshTest(TestCase):
    """Testes para a função _full_refresh."""

    databases = ["default", "professores_db"]

    def test_lista_vazia_retorna_zero(self) -> None:
        """Verifica que _full_refresh retorna zero para lista vazia."""
        from apps.professores.models import Professor

        resultado = _full_refresh(Professor, [])
        self.assertEqual(resultado, 0)

    def test_cria_registros(self) -> None:
        """Verifica que _full_refresh cria os registros fornecidos."""
        from apps.professores.models import Professor

        objs = [Professor(codigo_rf="T01", nome="TESTE")]
        resultado = _full_refresh(Professor, objs)
        self.assertEqual(resultado, 1)
        self.assertEqual(Professor.objects.using("professores_db").count(), 1)

    def test_substitui_registros_existentes(self) -> None:
        """_full_refresh substitui completamente os registros existentes."""
        from apps.professores.models import Professor

        _full_refresh(Professor, [Professor(codigo_rf="T01", nome="ANTIGA")])
        resultado = _full_refresh(
            Professor, [Professor(codigo_rf="T02", nome="NOVA")]
        )
        self.assertEqual(resultado, 1)
        self.assertFalse(
            Professor.objects.using("professores_db")
            .filter(codigo_rf="T01")
            .exists()
        )
        self.assertTrue(
            Professor.objects.using("professores_db")
            .filter(codigo_rf="T02")
            .exists()
        )


# ---------------------------------------------------------------------------
# EtlProfessoresService
# ---------------------------------------------------------------------------

_EOL_PATCH = "apps.professores.services.EOLService"
_UPSERT_PATCH = "apps.professores.services._upsert_incremental"
_FULL_REFRESH_PATCH = "apps.professores.services._full_refresh_por_lote"


class EtlProfessoresServiceFase1Test(TestCase):
    """Testes dos métodos de população da fase 1 do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    @patch(_UPSERT_PATCH, return_value=3)
    @patch(_EOL_PATCH)
    def test_popular_unidades_educacionais(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """popular_unidades_educacionais chama upsert e retorna contagem."""
        mock_eol.return_value.iter_query.return_value = [
            [("000001", "001", 1)]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_unidades_educacionais()
        self.assertEqual(resultado, 3)
        mock_upsert.assert_called_once()

    @patch(_UPSERT_PATCH, return_value=5)
    @patch(_EOL_PATCH)
    def test_popular_turmas_escola(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_turmas_escola retorna a contagem correta.

        Colunas: cd_turma_escola, cd_escola, an_letivo, st_turma_escola,
                 cd_tipo_turma, dt_inicio_turma, dt_fim_turma, dt_fim
        """
        dt = datetime.date(2024, 2, 1)
        mock_eol.return_value.iter_query.return_value = [
            [(9999, "000001", 2024, "A", 1, dt, None, None)]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_turmas_escola()
        self.assertEqual(resultado, 5)

    @patch(_UPSERT_PATCH, return_value=4)
    @patch(_EOL_PATCH)
    def test_popular_professores(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_professores retorna a contagem correta.

        Colunas: cd_registro_funcional, nm_pessoa, nm_social, cd_cpf_pessoa
        """
        mock_eol.return_value.iter_query.return_value = [
            [("012345", "ANA SILVA", None, "123.456.789-00")]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_professores()
        self.assertEqual(resultado, 4)

    @patch(_UPSERT_PATCH, return_value=1)
    @patch(_EOL_PATCH)
    def test_popular_pessoas(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_pessoas retorna a contagem correta."""
        mock_eol.return_value.iter_query.return_value = [
            [(500, "123.456.789-00", "JOSE", None)]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_pessoas()
        self.assertEqual(resultado, 1)


class EtlProfessoresServiceFase2Test(TestCase):
    """Testes dos métodos de população da fase 2 do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    @patch(_UPSERT_PATCH, return_value=2)
    @patch(_EOL_PATCH)
    def test_popular_serie_turma_grade(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_serie_turma_grade retorna contagem correta."""
        mock_eol.return_value.iter_query.return_value = [
            [(200, 9999, "000001", 50, None)]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_serie_turma_grade()
        self.assertEqual(resultado, 2)

    @patch(_UPSERT_PATCH, return_value=1)
    @patch(_EOL_PATCH)
    def test_popular_turma_escola_grade_programa(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica popular_turma_escola_grade_programa retorna contagem."""
        mock_eol.return_value.iter_query.return_value = [
            [(300, 9999, 50, None)]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_turma_escola_grade_programa()
        self.assertEqual(resultado, 1)

    @patch(_UPSERT_PATCH, return_value=10)
    @patch(_EOL_PATCH)
    def test_popular_cargos_base(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_cargos_base retorna a contagem correta.

        Colunas: cd_cargo_base_servidor, cd_registro_funcional, cd_cargo,
                 cd_situacao_funcional, dt_posse, dt_fim_nomeacao,
                 dt_cancelamento
        """
        dt = datetime.date(2020, 1, 1)
        mock_eol.return_value.iter_query.return_value = [
            [(1001, "012345", 3239, 6, dt, None, None)]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_cargos_base()
        self.assertEqual(resultado, 10)

    @patch(_UPSERT_PATCH, return_value=3)
    @patch(_EOL_PATCH)
    def test_popular_contratos_externos(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_contratos_externos retorna contagem correta."""
        mock_eol.return_value.iter_query.return_value = [
            [(800, 500, 10, "000001", None, None)]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_contratos_externos()
        self.assertEqual(resultado, 3)


class EtlProfessoresServiceFase3Test(TestCase):
    """Testes dos métodos de população da fase 3 do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    @patch(_FULL_REFRESH_PATCH, return_value=2)
    @patch(_EOL_PATCH)
    def test_popular_turma_grade_territorio_experiencia(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica popular_turma_grade_territorio_experiencia."""
        srv = EtlProfessoresService()
        resultado = srv.popular_turma_grade_territorio_experiencia()
        self.assertEqual(resultado, 2)

    @patch(_FULL_REFRESH_PATCH, return_value=5)
    @patch(_EOL_PATCH)
    def test_popular_lotacoes(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica que popular_lotacoes retorna a contagem correta."""
        srv = EtlProfessoresService()
        resultado = srv.popular_lotacoes()
        self.assertEqual(resultado, 5)

    @patch(_FULL_REFRESH_PATCH, return_value=3)
    @patch(_EOL_PATCH)
    def test_popular_cargos_sobrepostos(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica que popular_cargos_sobrepostos retorna contagem correta."""
        srv = EtlProfessoresService()
        resultado = srv.popular_cargos_sobrepostos()
        self.assertEqual(resultado, 3)

    @patch(_FULL_REFRESH_PATCH, return_value=4)
    @patch(_EOL_PATCH)
    def test_popular_funcoes_atividade(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica que popular_funcoes_atividade retorna contagem correta."""
        srv = EtlProfessoresService()
        resultado = srv.popular_funcoes_atividade()
        self.assertEqual(resultado, 4)

    @patch(_FULL_REFRESH_PATCH, return_value=1)
    @patch(_EOL_PATCH)
    def test_popular_laudos(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica que popular_laudos retorna a contagem correta."""
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
        mock_eol.return_value.iter_query.return_value = [
            [
                (
                    9001,
                    1001,
                    "000001",
                    9999,
                    None,
                    100,
                    10,
                    200,
                    2024,
                    dt,
                    dt,
                    None,
                    None,
                )
            ]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_atribuicoes_aula()
        self.assertEqual(resultado, 20)

    @patch(_UPSERT_PATCH, return_value=8)
    @patch(_EOL_PATCH)
    def test_popular_atribuicoes_externo(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica popular_atribuicoes_externo retorna contagem correta."""
        dt = datetime.date(2024, 2, 1)
        mock_eol.return_value.iter_query.return_value = [
            [
                (
                    9002,
                    800,
                    "000001",
                    100,
                    10,
                    200,
                    None,
                    2024,
                    dt,
                    dt,
                    None,
                    None,
                )
            ]
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
        self.assertEqual(srv.ultima_fase_concluida, 3)
        self.assertIn("unidade_educacional", resultado)
        self.assertIn("atribuicao_aula", resultado)

    def test_executar_fase2_pula_fase1(self) -> None:
        """Verifica que executar com fase_inicial=2 pula os dados da fase 1."""
        srv = self._make_service_com_populares_mockados(1)
        resultado = srv.executar(fase_inicial=2)
        self.assertEqual(srv.ultima_fase_concluida, 3)
        self.assertNotIn("unidade_educacional", resultado)
        self.assertIn("serie_turma_grade", resultado)

    def test_executar_fase3_pula_fases_1_e_2(self) -> None:
        """Verifica que executar com fase_inicial=3 pula as fases 1 e 2."""
        srv = self._make_service_com_populares_mockados(1)
        resultado = srv.executar(fase_inicial=3)
        self.assertNotIn("unidade_educacional", resultado)
        self.assertNotIn("cargo_base_servidor", resultado)
        self.assertIn("atribuicao_aula", resultado)

    def test_executar_retorna_soma_de_registros(self) -> None:
        """Verifica que executar retorna a soma de registros por tabela."""
        srv = self._make_service_com_populares_mockados(3)
        resultado = srv.executar(fase_inicial=1)
        self.assertTrue(all(v == 3 for v in resultado.values()))
