"""Testes para compat/base.py — ResultadoCompatibilidade."""

import datetime
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

from django.test import TestCase

from apps.professores.compat.base import (
    ResultadoCompatibilidade,
    VerificadorBase,
    _formatar_data,
)

# ---------------------------------------------------------------------------
# ResultadoCompatibilidade
# ---------------------------------------------------------------------------


class ResultadoCompatibilidadeTaxaTest(TestCase):
    """Testes para a propriedade taxa_correspondencia."""

    def _make(self, **kwargs: object) -> ResultadoCompatibilidade:
        return ResultadoCompatibilidade(
            verificador="V", consulta="C", **kwargs  # type: ignore[arg-type]
        )

    def test_taxa_zero_quando_sem_origem(self) -> None:
        """Verifica taxa_correspondencia = 0.0 quando total_origem é 0."""
        r = self._make(total_origem=0, correspondencias=0)
        self.assertEqual(r.taxa_correspondencia, 0.0)

    def test_taxa_calcula_fracao_correta(self) -> None:
        """Se a taxa é calculada como correspondencias/total_origem."""
        r = self._make(total_origem=4, correspondencias=3)
        self.assertAlmostEqual(r.taxa_correspondencia, 0.75)

    def test_taxa_100_porcento(self) -> None:
        """Verifica taxa de 100% quando tudo corresponde."""
        r = self._make(total_origem=10, correspondencias=10)
        self.assertAlmostEqual(r.taxa_correspondencia, 1.0)


class ResultadoCompatibilidadeAprovadoTest(TestCase):
    """Testes para a propriedade aprovado."""

    def _make(self, **kwargs: Any) -> ResultadoCompatibilidade:
        return ResultadoCompatibilidade(
            verificador="V",
            consulta="C",
            **kwargs,
        )

    def test_aprovado_quando_taxa_igual_limiar(self) -> None:
        """Verifica aprovação exata no limiar de 80%."""
        r = self._make(total_origem=10, correspondencias=8)
        self.assertTrue(r.aprovado)

    def test_aprovado_quando_taxa_acima_limiar(self) -> None:
        """Verifica aprovação acima de 80%."""
        r = self._make(total_origem=10, correspondencias=9)
        self.assertTrue(r.aprovado)

    def test_reprovado_quando_taxa_abaixo_limiar(self) -> None:
        """Verifica reprovação com taxa abaixo de 80%."""
        r = self._make(total_origem=10, correspondencias=7)
        self.assertFalse(r.aprovado)

    def test_aprovado_quando_ignorado(self) -> None:
        """Verifica que ignorado sempre retorna aprovado=True."""
        r = self._make(total_origem=0, ignorado=True)
        self.assertTrue(r.aprovado)

    def test_aprovado_quando_erro(self) -> None:
        """Verifica que erro sempre retorna aprovado=True."""
        r = self._make(total_origem=0, erro="falha grave")
        self.assertTrue(r.aprovado)


class ResultadoCompatibilidadeRotuloTest(TestCase):
    """Testes para o método rotulo."""

    def _make(self, **kwargs: Any) -> ResultadoCompatibilidade:
        return ResultadoCompatibilidade(
            verificador="V",
            consulta="C",
            **kwargs,
        )

    def test_rotulo_ok(self) -> None:
        """Verifica rótulo 'OK' quando aprovado e sem erro/ignorado."""
        r = self._make(total_origem=10, correspondencias=10)
        self.assertIn("OK", r.rotulo())

    def test_rotulo_falha(self) -> None:
        """Verifica rótulo 'FALHA' quando reprovado."""
        r = self._make(total_origem=10, correspondencias=0)
        self.assertEqual(r.rotulo(), "FALHA")

    def test_rotulo_ignorado(self) -> None:
        """Verifica rótulo 'IGNORADO' quando ignorado=True."""
        r = self._make(ignorado=True)
        self.assertEqual(r.rotulo(), "IGNORADO")

    def test_rotulo_erro(self) -> None:
        """Verifica rótulo 'ERRO' quando campo erro preenchido."""
        r = self._make(erro="timeout de conexão")
        self.assertEqual(r.rotulo(), "ERRO")


class ResultadoCompatibilidadeStrTest(TestCase):
    """Testes para o método __str__."""

    def _make(self, **kwargs: Any) -> ResultadoCompatibilidade:
        return ResultadoCompatibilidade(
            verificador="V",
            consulta="C",
            **kwargs,
        )

    def test_str_com_erro_inclui_mensagem(self) -> None:
        """Verifica que __str__ com erro inclui o texto do erro."""
        r = self._make(erro="timeout")
        s = str(r)
        self.assertIn("ERRO", s)
        self.assertIn("timeout", s)

    def test_str_com_ignorado_inclui_motivo(self) -> None:
        """Verifica que __str__ com ignorado inclui o motivo."""
        r = self._make(ignorado=True, motivo_ignorado="sem dados na origem")
        s = str(r)
        self.assertIn("IGNORADO", s)
        self.assertIn("sem dados na origem", s)

    def test_str_normal_inclui_contagem(self) -> None:
        """Verifica que __str__ normal inclui correspondencias/total_origem."""
        r = self._make(total_origem=5, correspondencias=5, total_destino=5)
        s = str(r)
        self.assertIn("5/5", s)

    def test_str_normal_inclui_porcentagem(self) -> None:
        """Verifica que __str__ inclui porcentagem formatada."""
        r = self._make(total_origem=4, correspondencias=3, total_destino=4)
        s = str(r)
        self.assertIn("75%", s)


# ---------------------------------------------------------------------------
# _formatar_data
# ---------------------------------------------------------------------------


class FormatarDataTest(TestCase):
    """Testes para _formatar_data."""

    def test_none_retorna_none(self) -> None:
        """Verifica que None retorna None."""
        self.assertIsNone(_formatar_data(None))

    def test_datetime_retorna_apenas_data(self) -> None:
        """Verifica que datetime retorna apenas a parte de data em ISO."""
        dt = datetime.datetime(2024, 3, 15, 10, 30, 0)
        self.assertEqual(_formatar_data(dt), "2024-03-15")

    def test_date_retorna_iso(self) -> None:
        """Verifica que date retorna string ISO."""
        d = datetime.date(2024, 3, 15)
        self.assertEqual(_formatar_data(d), "2024-03-15")

    def test_string_retorna_primeiros_10_caracteres(self) -> None:
        """Verifica que string retorna os primeiros 10 caracteres."""
        self.assertEqual(_formatar_data("2024-03-15T00:00:00"), "2024-03-15")

    def test_datetime_midnight_nao_confunde_com_date(self) -> None:
        """Verifica que datetime à meia-noite retorna só a data."""
        dt = datetime.datetime(2023, 1, 5, 0, 0, 0)
        self.assertEqual(_formatar_data(dt), "2023-01-05")


# ---------------------------------------------------------------------------
# VerificadorBase.executar
# ---------------------------------------------------------------------------


def _make_verificador(
    linhas_origem: list,
    linhas_destino: list,
    chave_fn: Callable[[dict], tuple[object, ...]] | None = None,
    raise_origem: Exception | None = None,
    raise_destino: Exception | None = None,
) -> VerificadorBase:
    """Cria subclasse concreta de VerificadorBase para uso nos testes."""

    class V(VerificadorBase):
        nome = "Teste"
        nome_consulta = "ConsultaTeste"
        limite = 10

        def buscar_origem(self, eol: object, limite: int) -> list:
            if raise_origem:
                raise raise_origem  # type: ignore[misc]
            return linhas_origem

        def buscar_destino(self, lo: list) -> list:
            if raise_destino:
                raise raise_destino  # type: ignore[misc]
            return linhas_destino

        def chave_comparacao(self, linha: dict) -> tuple:
            if chave_fn:
                return chave_fn(linha)
            return (linha.get("id"),)

    return V()


class VerificadorBaseErroOrigemTest(TestCase):
    """Testa captura de erro em buscar_origem."""

    def test_erro_de_conexao_e_capturado(self) -> None:
        """Se exception em buscar_origem é capturada em resultado."""
        v = _make_verificador([], [], raise_origem=RuntimeError("conn falhou"))
        r = v.executar(MagicMock())
        self.assertIn("origem", r.erro)
        self.assertIn("conn falhou", r.erro)

    def test_erro_nao_propaga_excecao(self) -> None:
        """Verifica que o erro não vaza como exceção não tratada."""
        v = _make_verificador([], [], raise_origem=ValueError("db error"))
        try:
            v.executar(MagicMock())
        except Exception:  # noqa: BLE001
            self.fail("executar não deveria propagar exceção")


class VerificadorBaseOrigemVaziaTest(TestCase):
    """Testa comportamento quando origem não retorna dados."""

    def test_ignorado_quando_origem_vazia(self) -> None:
        """Verifica que resultado.ignorado=True quando origem é vazia."""
        v = _make_verificador(linhas_origem=[], linhas_destino=[])
        r = v.executar(MagicMock())
        self.assertTrue(r.ignorado)
        self.assertEqual(r.motivo_ignorado, "sem dados na origem")

    def test_total_origem_zero(self) -> None:
        """Verifica total_origem=0 quando origem vazia."""
        v = _make_verificador(linhas_origem=[], linhas_destino=[])
        r = v.executar(MagicMock())
        self.assertEqual(r.total_origem, 0)


class VerificadorBaseErroDestinoTest(TestCase):
    """Testa captura de erro em buscar_destino."""

    def test_erro_destino_capturado(self) -> None:
        """Verifica que exception em buscar_destino é capturada."""
        v = _make_verificador(
            linhas_origem=[{"id": 1}],
            linhas_destino=[],
            raise_destino=ConnectionError("db down"),
        )
        r = v.executar(MagicMock())
        self.assertIn("destino", r.erro)
        self.assertIn("db down", r.erro)

    def test_erro_destino_nao_propaga(self) -> None:
        """Verifica que erro no destino não vaza como exceção."""
        v = _make_verificador(
            linhas_origem=[{"id": 1}],
            linhas_destino=[],
            raise_destino=RuntimeError("crash"),
        )
        try:
            v.executar(MagicMock())
        except Exception:  # noqa: BLE001
            self.fail("executar não deveria propagar exceção de destino")


class VerificadorBaseComparacaoTest(TestCase):
    """Testa o fluxo de comparação origem x destino."""

    def test_todas_linhas_correspondidas(self) -> None:
        """Verifica resultado com correspondência total."""
        linhas = [{"id": i} for i in range(1, 6)]
        v = _make_verificador(linhas_origem=linhas, linhas_destino=linhas)
        r = v.executar(MagicMock())
        self.assertEqual(r.total_origem, 5)
        self.assertEqual(r.correspondencias, 5)
        self.assertEqual(len(r.divergencias), 0)
        self.assertTrue(r.aprovado)

    def test_nenhuma_correspondencia(self) -> None:
        """Verifica resultado sem correspondências."""
        linhas_o = [{"id": 1}, {"id": 2}]
        linhas_d = [{"id": 10}, {"id": 20}]
        v = _make_verificador(linhas_origem=linhas_o, linhas_destino=linhas_d)
        r = v.executar(MagicMock())
        self.assertEqual(r.correspondencias, 0)
        self.assertFalse(r.aprovado)

    def test_divergencias_limitadas_a_cinco(self) -> None:
        """Verifica que no máximo 5 exemplos de divergência são armazenados."""
        linhas_o = [{"id": i} for i in range(1, 11)]  # 10 sem correspondência
        linhas_d: list = []
        v = _make_verificador(linhas_origem=linhas_o, linhas_destino=linhas_d)
        r = v.executar(MagicMock())
        self.assertLessEqual(len(r.divergencias), 5)

    def test_total_destino_preenchido(self) -> None:
        """Se total_destino reflete o número de linhas do destino."""
        linhas_o = [{"id": 1}]
        linhas_d = [{"id": 1}, {"id": 2}]
        v = _make_verificador(linhas_origem=linhas_o, linhas_destino=linhas_d)
        r = v.executar(MagicMock())
        self.assertEqual(r.total_destino, 2)

    def test_limite_customizado_passado_para_buscar_origem(self) -> None:
        """Se o limite passado a executar é repassado a buscar_origem."""
        chamadas: list = []

        class V(VerificadorBase):
            nome = "T"
            nome_consulta = "Q"
            limite = 10

            def buscar_origem(self, eol: object, limite: int) -> list:
                chamadas.append(limite)
                return []

            def buscar_destino(self, lo: list) -> list:
                return []

            def chave_comparacao(self, linha: dict) -> tuple:
                return (linha.get("id"),)

        V().executar(MagicMock(), limite=99)
        self.assertEqual(chamadas[0], 99)

    def test_limite_padrao_da_classe_usado_quando_nao_passado(self) -> None:
        """Verifica que o limite padrão da classe é usado sem argumento."""
        chamadas: list = []

        class V(VerificadorBase):
            nome = "T"
            nome_consulta = "Q"
            limite = 42

            def buscar_origem(self, eol: object, limite: int) -> list:
                chamadas.append(limite)
                return []

            def buscar_destino(self, lo: list) -> list:
                return []

            def chave_comparacao(self, linha: dict) -> tuple:
                return (linha.get("id"),)

        V().executar(MagicMock())
        self.assertEqual(chamadas[0], 42)

    def test_nome_e_consulta_no_resultado(self) -> None:
        """Se nome e consulta do verificador aparecem no resultado."""
        v = _make_verificador(linhas_origem=[], linhas_destino=[])
        r = v.executar(MagicMock())
        self.assertEqual(r.verificador, "Teste")
        self.assertEqual(r.consulta, "ConsultaTeste")
