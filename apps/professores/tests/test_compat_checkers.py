"""Testes para compat/checkers/ — todos verificadores."""

import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.professores.compat.checkers.atribuicao_aula import (
    VerificadorAtribuicaoAula,
    VerificadorPerfilProfServidor,
    VerificadorTitularServidor,
)
from apps.professores.compat.checkers.atribuicao_externo import (
    VerificadorAtribuicaoExterno,
    VerificadorPerfilProfExterno,
    VerificadorTitularExterno,
)
from apps.professores.compat.checkers.cargo_base import (
    VerificadorCargoBaseAtivo,
    VerificadorValidadeProf,
)

_DT = datetime.date(2024, 2, 1)
_DT_STR = "2024-02-01"

_MOD_AA = "apps.professores.compat.checkers.atribuicao_aula"
_MOD_AE = "apps.professores.compat.checkers.atribuicao_externo"
_MOD_CB = "apps.professores.compat.checkers.cargo_base"


class VerificadorAtribuicaoAulaBuscarOrigemTest(TestCase):
    """Testes para VerificadorAtribuicaoAula.buscar_origem."""

    def _row(self) -> tuple:
        return (
            9001,
            " 012345 ",
            " 000001 ",
            200,
            10,
            2024,
            _DT,
            _DT,
            None,
            None,
        )

    def test_mapeamento_de_campos(self) -> None:
        """Verifica que os campos da row são mapeados corretamente."""
        eol = MagicMock()
        eol.executar_query.return_value = [self._row()]
        v = VerificadorAtribuicaoAula()
        result = v.buscar_origem(eol, 10)
        self.assertEqual(len(result), 1)
        r = result[0]
        self.assertEqual(r["id"], 9001)
        self.assertEqual(r["codigo_rf"], "012345")
        self.assertEqual(r["codigo_ue"], "000001")
        self.assertEqual(r["codigo_serie_grade"], 200)
        self.assertEqual(r["codigo_componente"], 10)
        self.assertEqual(r["ano_atribuicao"], 2024)
        self.assertEqual(r["dt_atribuicao"], _DT_STR)

    def test_dt_cancelamento_nulo_mapeado(self) -> None:
        """Verifica que dt_cancelamento None é mapeado como None."""
        eol = MagicMock()
        eol.executar_query.return_value = [self._row()]
        v = VerificadorAtribuicaoAula()
        result = v.buscar_origem(eol, 10)
        self.assertIsNone(result[0]["dt_cancelamento"])

    def test_lista_vazia_quando_sem_rows(self) -> None:
        """Verifica retorno de lista vazia quando query não retorna linhas."""
        eol = MagicMock()
        eol.executar_query.return_value = []
        v = VerificadorAtribuicaoAula()
        self.assertEqual(v.buscar_origem(eol, 10), [])


class VerificadorAtribuicaoAulaBuscarDestinoTest(TestCase):
    """Testes para VerificadorAtribuicaoAula.buscar_destino."""

    @patch(f"{_MOD_AA}.AtribuicaoAula")
    def test_busca_por_pks_e_mapeia(self, mock_model: MagicMock) -> None:
        """Verifica mapeamento de campos no destino."""
        qs = mock_model.objects.using.return_value.filter.return_value
        qs.values.return_value = [
            {
                "id": 9001,
                "cargo_base__professor_id": "012345",
                "codigo_unidade_educacao": "000001",
                "codigo_serie_grade": 200,
                "codigo_componente_curricular": 10,
                "ano_atribuicao": 2024,
                "dt_atribuicao_aula": _DT,
                "dt_cancelamento": None,
            }
        ]
        v = VerificadorAtribuicaoAula()
        linhas = [
            {
                "id": 9001,
                "codigo_rf": "012345",
                "codigo_ue": "000001",
                "codigo_serie_grade": 200,
                "codigo_componente": 10,
                "ano_atribuicao": 2024,
                "dt_atribuicao": _DT_STR,
                "dt_cancelamento": None,
            }
        ]
        result = v.buscar_destino(linhas)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 9001)
        self.assertEqual(result[0]["codigo_rf"], "012345")
        self.assertEqual(result[0]["dt_atribuicao"], _DT_STR)


class VerificadorAtribuicaoAulaChaveTest(TestCase):
    """Testes para VerificadorAtribuicaoAula.chave_comparacao."""

    def test_chave_contem_campos_corretos(self) -> None:
        """Verifica que a chave contém id, rf, serie_grade, componente, ano."""
        linha = {
            "id": 9001,
            "codigo_rf": "012345",
            "codigo_serie_grade": 200,
            "codigo_componente": 10,
            "ano_atribuicao": 2024,
        }
        chave = VerificadorAtribuicaoAula().chave_comparacao(linha)
        self.assertEqual(chave, (9001, "012345", 200, 10, 2024))


class VerificadorTitularServidorTest(TestCase):
    """Testes para VerificadorTitularServidor."""

    def test_buscar_origem_mapeamento(self) -> None:
        """Verifica mapeamento da row de titular servidor."""
        eol = MagicMock()
        eol.executar_query.return_value = [
            (9001, " 012345 ", 200, 10, 2024, 300)
        ]
        v = VerificadorTitularServidor()
        result = v.buscar_origem(eol, 10)
        self.assertEqual(result[0]["id"], 9001)
        self.assertEqual(result[0]["codigo_rf"], "012345")
        self.assertEqual(result[0]["codigo_serie_grade"], 200)
        self.assertEqual(result[0]["id_tegp"], 300)

    def test_chave_sem_id_tegp(self) -> None:
        """Verifica que a chave inclui id, rf, serie_grade, componente."""
        linha = {
            "id": 9001,
            "codigo_rf": "012345",
            "codigo_serie_grade": 200,
            "codigo_componente": 10,
        }
        chave = VerificadorTitularServidor().chave_comparacao(linha)
        self.assertEqual(chave, (9001, "012345", 200, 10))

    @patch(f"{_MOD_AA}.AtribuicaoAula")
    def test_buscar_destino_filtra_disponibilizacao_nula(
        self, mock_model: MagicMock
    ) -> None:
        """Verifica filtro dt_disponibilizacao_aulas__isnull."""
        qs = mock_model.objects.using.return_value.filter.return_value
        qs.values.return_value = []

        v = VerificadorTitularServidor()

        entrada = [{"id": 1}]
        v.buscar_destino(entrada)

        filtros = mock_model.objects.using.return_value.filter.call_args[1]

        self.assertTrue(filtros["dt_disponibilizacao_aulas__isnull"])


class VerificadorPerfilProfServidorTest(TestCase):
    """Testes para VerificadorPerfilProfServidor."""

    def test_buscar_origem_mapeamento(self) -> None:
        """Verifica mapeamento da row de perfil prof servidor."""
        eol = MagicMock()
        eol.executar_query.return_value = [
            (" 012345 ", " 000001 ", 9999, 2024, 200, 10, None)
        ]
        v = VerificadorPerfilProfServidor()
        result = v.buscar_origem(eol, 10)
        self.assertEqual(result[0]["codigo_rf"], "012345")
        self.assertEqual(result[0]["codigo_escola"], "000001")
        self.assertEqual(result[0]["codigo_turma"], 9999)
        self.assertEqual(result[0]["ano_letivo"], 2024)

    def test_chave_rf_escola_turma_ano(self) -> None:
        """Verifica que a chave inclui rf, escola, turma, ano."""
        linha = {
            "codigo_rf": "012345",
            "codigo_escola": "000001",
            "codigo_turma": 9999,
            "ano_letivo": 2024,
        }
        chave = VerificadorPerfilProfServidor().chave_comparacao(linha)
        self.assertEqual(chave, ("012345", "000001", 9999, 2024))

    @patch(f"{_MOD_AA}.AtribuicaoAula")
    def test_buscar_destino_mapeia_campos(
        self, mock_aa: MagicMock
    ) -> None:
        """Verifica mapeamento de campos via AtribuicaoAula no destino."""
        aa_qs = mock_aa.objects.using.return_value.filter.return_value
        aa_qs.values.return_value = [
            {
                "cargo_base__professor_id": "012345",
                "codigo_unidade_educacao": "000001",
                "codigo_turma_escola": 9999,
                "codigo_serie_grade": 200,
                "ano_atribuicao": 2024,
            }
        ]
        v = VerificadorPerfilProfServidor()
        linhas = [
            {
                "codigo_rf": "012345",
                "codigo_escola": "000001",
                "codigo_turma": 9999,
                "ano_letivo": 2024,
                "codigo_serie_grade": 200,
                "codigo_componente": 10,
            }
        ]
        result = v.buscar_destino(linhas)
        self.assertEqual(len(result), 1)
        esperado = result[0]
        self.assertEqual(esperado["codigo_rf"], "012345")
        self.assertEqual(esperado["codigo_turma"], 9999)

    @patch(f"{_MOD_AA}.AtribuicaoAula")
    def test_buscar_destino_codigo_turma_escola_none(
        self, mock_aa: MagicMock
    ) -> None:
        """Verifica que codigo_turma_escola None é preservado no resultado."""
        aa_qs = mock_aa.objects.using.return_value.filter.return_value
        aa_qs.values.return_value = [
            {
                "cargo_base__professor_id": "012345",
                "codigo_unidade_educacao": "000001",
                "codigo_turma_escola": None,
                "codigo_serie_grade": 999,
                "ano_atribuicao": 2024,
            }
        ]
        v = VerificadorPerfilProfServidor()
        linhas = [
            {
                "codigo_rf": "012345",
                "codigo_escola": "000001",
                "codigo_turma": None,
                "ano_letivo": 2024,
                "codigo_serie_grade": 999,
                "codigo_componente": 10,
            }
        ]
        result = v.buscar_destino(linhas)
        self.assertEqual(len(result), 1)
        esperado = result[0]
        self.assertIsNone(esperado["codigo_turma"])
        self.assertEqual(esperado["codigo_escola"], "000001")


class VerificadorAtribuicaoExternoTest(TestCase):
    """Testes para VerificadorAtribuicaoExterno."""

    def _row(self) -> tuple:
        return (
            9002,
            " 123.456.789-00 ",
            " 000002 ",
            201,
            11,
            2024,
            _DT,
            _DT,
            None,
            None,
        )

    def test_buscar_origem_mapeamento(self) -> None:
        """Verifica mapeamento de campos da row de atribuição externo."""
        eol = MagicMock()
        eol.executar_query.return_value = [self._row()]
        v = VerificadorAtribuicaoExterno()
        result = v.buscar_origem(eol, 10)
        self.assertEqual(result[0]["id"], 9002)
        self.assertEqual(result[0]["cpf_pessoa"], "123.456.789-00")
        self.assertEqual(result[0]["codigo_ue"], "000002")
        self.assertEqual(result[0]["codigo_serie_grade"], 201)

    def test_buscar_origem_cpf_none(self) -> None:
        """Verifica que cpf_pessoa None é preservado."""
        eol = MagicMock()
        row = (9002, None, " 000002 ", 201, 11, 2024, _DT, _DT, None, None)
        eol.executar_query.return_value = [row]
        v = VerificadorAtribuicaoExterno()
        result = v.buscar_origem(eol, 10)
        self.assertIsNone(result[0]["cpf_pessoa"])

    def test_chave_id_cpf_serie_componente_ano(self) -> None:
        """Verifica que chave inclui id, cpf, serie_grade, componente, ano."""
        linha = {
            "id": 9002,
            "cpf_pessoa": "123.456.789-00",
            "codigo_serie_grade": 201,
            "codigo_componente": 11,
            "ano_atribuicao": 2024,
        }
        chave = VerificadorAtribuicaoExterno().chave_comparacao(linha)
        self.assertEqual(chave, (9002, "123.456.789-00", 201, 11, 2024))

    @patch(f"{_MOD_AE}.AtribuicaoExterno")
    def test_buscar_destino_mapeamento(self, mock_model: MagicMock) -> None:
        """Verifica que buscar_destino mapeia campos corretamente."""
        qs = mock_model.objects.using.return_value.filter.return_value

        qs.values.return_value = [
            {
                "id": 9002,
                "contrato_externo__pessoa__cpf": "123.456.789-00",
                "codigo_unidade_educacao": "000002",
                "codigo_serie_grade": 201,
                "codigo_componente_curricular": 11,
                "ano_atribuicao": 2024,
                "dt_atribuicao": _DT,
                "dt_cancelamento": None,
            }
        ]

        v = VerificadorAtribuicaoExterno()

        result = v.buscar_destino([{"id": 9002}])

        esperado = result[0]

        self.assertEqual(esperado["cpf_pessoa"], "123.456.789-00")
        self.assertEqual(esperado["dt_atribuicao"], _DT_STR)


class VerificadorTitularExternoTest(TestCase):
    """Testes para VerificadorTitularExterno."""

    def test_buscar_origem_mapeamento(self) -> None:
        """Verifica mapeamento da row de titular externo."""
        eol = MagicMock()
        eol.executar_query.return_value = [
            (9002, " 123.456.789-00 ", 201, 11, 2024, 400)
        ]
        v = VerificadorTitularExterno()
        result = v.buscar_origem(eol, 10)
        self.assertEqual(result[0]["id"], 9002)
        self.assertEqual(result[0]["cpf_pessoa"], "123.456.789-00")
        self.assertEqual(result[0]["id_tegp"], 400)

    def test_chave_id_cpf_serie_componente(self) -> None:
        """Verifica chave sem id_tegp."""
        linha = {
            "id": 9002,
            "cpf_pessoa": "123.456.789-00",
            "codigo_serie_grade": 201,
            "codigo_componente": 11,
        }
        chave = VerificadorTitularExterno().chave_comparacao(linha)
        self.assertEqual(chave, (9002, "123.456.789-00", 201, 11))

    @patch(f"{_MOD_AE}.AtribuicaoExterno")
    def test_buscar_destino_filtra_disponibilizacao_nula(
        self, mock_model: MagicMock
    ) -> None:
        """Verifica filtro dt_disponibilizacao__isnull."""
        qs = mock_model.objects.using.return_value.filter.return_value
        qs.values.return_value = []

        v = VerificadorTitularExterno()

        v.buscar_destino([{"id": 1}])

        filtros = mock_model.objects.using.return_value.filter.call_args[1]

        self.assertTrue(filtros["dt_disponibilizacao__isnull"])


class VerificadorPerfilProfExternoTest(TestCase):
    """Testes para VerificadorPerfilProfExterno."""

    def test_buscar_origem_mapeamento(self) -> None:
        """Verifica mapeamento da row de perfil prof externo."""
        eol = MagicMock()
        eol.executar_query.return_value = [
            (" 123.456.789-00 ", " 000001 ", 9999, 2024, 200, 10)
        ]
        v = VerificadorPerfilProfExterno()
        result = v.buscar_origem(eol, 10)
        self.assertEqual(result[0]["cpf_pessoa"], "123.456.789-00")
        self.assertEqual(result[0]["codigo_escola"], "000001")
        self.assertEqual(result[0]["codigo_turma"], 9999)

    def test_buscar_origem_cpf_none(self) -> None:
        """Verifica que cpf None é preservado."""
        eol = MagicMock()
        eol.executar_query.return_value = [
            (None, " 000001 ", 9999, 2024, 200, 10)
        ]
        v = VerificadorPerfilProfExterno()
        result = v.buscar_origem(eol, 10)
        self.assertIsNone(result[0]["cpf_pessoa"])

    def test_chave_cpf_escola_turma_ano(self) -> None:
        """Verifica que a chave inclui cpf, escola, turma, ano."""
        linha = {
            "cpf_pessoa": "123.456.789-00",
            "codigo_escola": "000001",
            "codigo_turma": 9999,
            "ano_letivo": 2024,
        }
        chave = VerificadorPerfilProfExterno().chave_comparacao(linha)
        self.assertEqual(chave, ("123.456.789-00", "000001", 9999, 2024))

    @patch(f"{_MOD_AE}.AtribuicaoExterno")
    def test_buscar_destino_mapeia_campos(
        self, mock_ae: MagicMock
    ) -> None:
        """Verifica mapeamento de campos via AtribuicaoExterno no destino."""
        ae_qs = mock_ae.objects.using.return_value.filter.return_value
        ae_qs.values.return_value = [
            {
                "contrato_externo__pessoa__cpf": "123.456.789-00",
                "codigo_unidade_educacao": "000001",
                "codigo_turma_escola": 9999,
                "codigo_serie_grade": 200,
                "ano_atribuicao": 2024,
            }
        ]
        v = VerificadorPerfilProfExterno()
        linhas = [
            {
                "cpf_pessoa": "123.456.789-00",
                "codigo_escola": "000001",
                "codigo_turma": 9999,
                "ano_letivo": 2024,
                "codigo_serie_grade": 200,
                "codigo_componente": 10,
            }
        ]
        result = v.buscar_destino(linhas)
        self.assertEqual(len(result), 1)
        esperado = result[0]
        self.assertEqual(esperado["cpf_pessoa"], "123.456.789-00")
        self.assertEqual(esperado["codigo_turma"], 9999)


class VerificadorCargoBaseAtivoTest(TestCase):
    """Testes para VerificadorCargoBaseAtivo."""

    def test_buscar_origem_mapeamento(self) -> None:
        """Verifica mapeamento da row de cargo base ativo."""
        eol = MagicMock()
        eol.executar_query.return_value = [
            (1001, " 012345 ", 3239, 6, _DT, None)
        ]
        v = VerificadorCargoBaseAtivo()
        result = v.buscar_origem(eol, 10)
        self.assertEqual(result[0]["id_cargo_base"], 1001)
        self.assertEqual(result[0]["codigo_rf"], "012345")
        self.assertEqual(result[0]["codigo_cargo"], 3239)
        self.assertEqual(result[0]["situacao_funcional"], 6)
        self.assertEqual(result[0]["dt_posse"], _DT_STR)
        self.assertIsNone(result[0]["dt_fim_nomeacao"])

    def test_chave_id_rf_cargo_posse(self) -> None:
        """Verifica que a chave inclui id_cargo_base, rf, cargo, dt_posse."""
        linha = {
            "id_cargo_base": 1001,
            "codigo_rf": "012345",
            "codigo_cargo": 3239,
            "dt_posse": _DT_STR,
        }
        chave = VerificadorCargoBaseAtivo().chave_comparacao(linha)
        self.assertEqual(chave, (1001, "012345", 3239, _DT_STR))

    @patch(f"{_MOD_CB}.CargoBaseServidor")
    def test_buscar_destino_mapeamento(self, mock_model: MagicMock) -> None:
        """Verifica mapeamento de campos do destino."""
        qs = mock_model.objects.using.return_value.filter.return_value

        qs.values.return_value = [
            {
                "id": 1001,
                "professor_id": "012345",
                "codigo_cargo": 3239,
                "situacao_funcional": 6,
                "dt_posse": _DT,
                "dt_fim_nomeacao": None,
            }
        ]

        v = VerificadorCargoBaseAtivo()

        result = v.buscar_destino([{"id_cargo_base": 1001}])

        esperado = result[0]

        self.assertEqual(esperado["id_cargo_base"], 1001)
        self.assertEqual(esperado["codigo_rf"], "012345")
        self.assertEqual(esperado["dt_posse"], _DT_STR)


class VerificadorValidadeProfTest(TestCase):
    """Testes para VerificadorValidadeProf."""

    def test_buscar_origem_mapeamento(self) -> None:
        """Verifica mapeamento da row de validade prof."""
        eol = MagicMock()
        eol.executar_query.return_value = [(1001, " 012345 ", 6, 1)]
        v = VerificadorValidadeProf()
        result = v.buscar_origem(eol, 10)
        self.assertEqual(result[0]["id_cargo_base"], 1001)
        self.assertEqual(result[0]["codigo_rf"], "012345")
        self.assertEqual(result[0]["situacao_funcional"], 6)
        self.assertTrue(result[0]["sem_laudo"])

    def test_buscar_origem_sem_laudo_false(self) -> None:
        """Verifica que sem_laudo=0 vira False."""
        eol = MagicMock()
        eol.executar_query.return_value = [(1001, " 012345 ", 6, 0)]
        v = VerificadorValidadeProf()
        result = v.buscar_origem(eol, 10)
        self.assertFalse(result[0]["sem_laudo"])

    def test_chave_id_situacao_sem_laudo(self) -> None:
        """Verifica que a chave inclui id_cargo_base, situacao, sem_laudo."""
        linha = {
            "id_cargo_base": 1001,
            "situacao_funcional": 6,
            "sem_laudo": True,
        }
        chave = VerificadorValidadeProf().chave_comparacao(linha)
        self.assertEqual(chave, (1001, 6, True))

    @patch(f"{_MOD_CB}.LaudoMedico")
    @patch(f"{_MOD_CB}.CargoBaseServidor")
    def test_buscar_destino_sem_laudo(
        self, mock_cbs: MagicMock, mock_laudo: MagicMock
    ) -> None:
        """Verifica buscar_destino quando cargo não tem laudo médico."""
        cbs_qs = mock_cbs.objects.using.return_value.filter.return_value
        laudo_qs = mock_laudo.objects.using.return_value.filter.return_value

        cbs_qs.values.return_value = [
            {
                "id": 1001,
                "professor_id": "012345",
                "situacao_funcional": 6,
            }
        ]

        laudo_qs.values_list.return_value = []

        v = VerificadorValidadeProf()

        result = v.buscar_destino([{"id_cargo_base": 1001}])

        self.assertTrue(result[0]["sem_laudo"])

    @patch(f"{_MOD_CB}.LaudoMedico")
    @patch(f"{_MOD_CB}.CargoBaseServidor")
    def test_buscar_destino_com_laudo(
        self, mock_cbs: MagicMock, mock_laudo: MagicMock
    ) -> None:
        """Verifica buscar_destino quando cargo tem laudo médico."""
        cbs_qs = mock_cbs.objects.using.return_value.filter.return_value
        laudo_qs = mock_laudo.objects.using.return_value.filter.return_value

        cbs_qs.values.return_value = [
            {
                "id": 1001,
                "professor_id": "012345",
                "situacao_funcional": 6,
            }
        ]

        laudo_qs.values_list.return_value = [1001]

        v = VerificadorValidadeProf()

        result = v.buscar_destino([{"id_cargo_base": 1001}])

        self.assertFalse(result[0]["sem_laudo"])
