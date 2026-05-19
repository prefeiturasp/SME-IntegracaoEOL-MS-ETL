"""Testes de _row_to_*, _full_refresh e EtlProfessoresService."""

import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.professores.queries import CARGOS_PROFESSOR
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
)


class RowToProfessorTest(TestCase):
    """Testes para a função _row_to_professor."""

    def test_campos(self) -> None:
        """Verifica que os campos do professor são extraídos corretamente."""
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
        """Verifica que os campos do cargo base são extraídos corretamente."""
        dt = datetime.date(2020, 1, 1)
        row = (
            1001, "012345", 3239, "PROF DE EDUC BASICA I", 6, dt, None, None
        )
        r = _row_to_cargo_base(row)
        self.assertEqual(r["id"], 1001)
        self.assertEqual(r["professor_id"], "012345")
        self.assertEqual(r["codigo_cargo"], 3239)
        self.assertEqual(r["descricao_cargo"], "PROF DE EDUC BASICA I")
        self.assertEqual(r["situacao_funcional"], 6)
        self.assertEqual(r["dt_posse"], dt)

    def test_descricao_cargo_none(self) -> None:
        """Verifica que dc_cargo None resulta em descricao_cargo None."""
        dt = datetime.date(2020, 1, 1)
        row = (1002, "012346", 3247, None, 6, dt, None, None)
        r = _row_to_cargo_base(row)
        self.assertIsNone(r["descricao_cargo"])

    def test_situacao_funcional_none(self) -> None:
        """Verifica que situacao_funcional None é preservado."""
        dt = datetime.date(2020, 1, 1)
        row = (1002, "012346", 3247, "PROF BASICA II", None, dt, None, None)
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
            5555,
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
        self.assertEqual(r["codigo_turma_escola"], 5555)
        self.assertEqual(r["ano_atribuicao"], 2024)

    def test_codigo_turma_escola_none(self) -> None:
        """Verifica que codigo_turma_escola None é preservado."""
        dt = datetime.date(2024, 2, 1)
        row = (
            9003,
            801,
            "000002",
            None,
            101,
            11,
            201,
            None,
            2024,
            dt,
            dt,
            None,
            None,
        )
        r = _row_to_atribuicao_externo(row)
        self.assertIsNone(r["codigo_turma_escola"])


class ParamsCargoTest(TestCase):
    """Testes para a função _params_cargo."""

    def test_retorna_lista(self) -> None:
        """Verifica que _params_cargo retorna uma lista."""
        params = _params_cargo()
        self.assertIsInstance(params, list)
        self.assertTrue(len(params) > 0)

    def test_valores_sao_cargos_professor(self) -> None:
        """Verifica que os valores correspondem à lista CARGOS_PROFESSOR."""
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


_EOL_PATCH = "apps.professores.services.EOLService"
_UPSERT_PATCH = "apps.professores.services._upsert_incremental"
_FULL_REFRESH_PATCH = "apps.professores.services._full_refresh_por_lote"


class EtlProfessoresServiceFase1Test(TestCase):
    """Testes dos métodos de população da fase 1 do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    @patch(_UPSERT_PATCH, return_value=4)
    @patch(_EOL_PATCH)
    def test_popular_professores(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_professores retorna a contagem correta."""
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

    @patch(_UPSERT_PATCH, return_value=10)
    @patch(_EOL_PATCH)
    def test_popular_cargos_base(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_cargos_base retorna a contagem correta."""
        dt = datetime.date(2020, 1, 1)
        mock_eol.return_value.iter_query.return_value = [
            [
                (
                    1001, "012345", 3239, "PROF DE EDUC BASICA I",
                    6, dt, None, None,
                )
            ]
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
                    5555,
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
        self.assertIn("professor", resultado)
        self.assertIn("atribuicao_aula", resultado)

    def test_executar_fase2_pula_fase1(self) -> None:
        """Verifica que executar com fase_inicial=2 pula os dados da fase 1."""
        srv = self._make_service_com_populares_mockados(1)
        resultado = srv.executar(fase_inicial=2)
        self.assertEqual(srv.ultima_fase_concluida, 3)
        self.assertNotIn("professor", resultado)
        self.assertIn("cargo_base_servidor", resultado)

    def test_executar_fase3_pula_fases_1_e_2(self) -> None:
        """Verifica que executar com fase_inicial=3 pula as fases 1 e 2."""
        srv = self._make_service_com_populares_mockados(1)
        resultado = srv.executar(fase_inicial=3)
        self.assertNotIn("professor", resultado)
        self.assertNotIn("cargo_base_servidor", resultado)
        self.assertIn("atribuicao_aula", resultado)

    def test_executar_retorna_soma_de_registros(self) -> None:
        """Verifica que executar retorna a soma de registros por tabela."""
        srv = self._make_service_com_populares_mockados(3)
        resultado = srv.executar(fase_inicial=1)
        self.assertTrue(all(v == 3 for v in resultado.values()))

    def test_iter_lotes_aplica_offset_e_callback(self) -> None:
        """Verifica offset e callback de lote na iteracao rastreada."""
        srv = self._make_service_com_populares_mockados()
        original = MagicMock(return_value=iter([["lote-1"], ["lote-2"]]))
        lotes: list[tuple[str, int]] = []
        contador = [1]

        resultado = list(
            srv._iter_lotes(
                "select 1",
                None,
                original,
                1,
                "professor",
                contador,
                lambda tabela, lote: lotes.append((tabela, lote)),
            )
        )

        self.assertEqual(resultado, [["lote-2"]])
        self.assertEqual(lotes, [("professor", 2)])

    def test_executar_com_lote_inicial_rastreia_iter_query(self) -> None:
        """Retomada por lote substitui iter_query durante a tabela."""
        srv = self._make_service_com_populares_mockados(0)
        srv.eol.iter_query = MagicMock(return_value=iter([[1], [2]]))
        lotes: list[tuple[str, int]] = []
        tabelas: list[tuple[str, int]] = []

        def popular_professores() -> int:
            return sum(len(chunk) for chunk in srv.eol.iter_query("sql"))

        srv.popular_professores = popular_professores  # type: ignore[method-assign]

        resultado = srv.executar(
            fase_inicial=1,
            lote_inicial=1,
            on_lote=lambda tabela, lote: lotes.append((tabela, lote)),
            on_tabela_concluida=lambda tabela, linhas: tabelas.append(
                (tabela, linhas)
            ),
        )

        self.assertEqual(resultado["professor"], 1)
        self.assertIn(("professor", 2), lotes)
        self.assertIn(("professor", 1), tabelas)
        self.assertIsInstance(srv.eol.iter_query, MagicMock)

    def test_executar_pula_ate_tabela_informada(self) -> None:
        """Retomada por tabela pula ate a tabela concluida."""
        srv = self._make_service_com_populares_mockados(1)

        resultado = srv.executar(fase_inicial=1, pular_ate="professor")

        self.assertNotIn("professor", resultado)
        self.assertIn("pessoa", resultado)
