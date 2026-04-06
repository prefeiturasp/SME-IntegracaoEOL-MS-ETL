"""Testes de string representation dos modelos institucionais."""

from django.test import TestCase

from apps.institucional.models import (
    DRE,
    SubPrefeitura,
    TipoEscola,
    UnidadeEducacional,
)


class InstitucionalModelsTest(TestCase):
    """Testes para garantir cobertura dos métodos __str__ dos modelos."""

    def test_dre_str(self) -> None:
        """Verifica representação string de DRE."""
        dre = DRE(codigo_dre="123", nome="DRE TESTE", sigla="DT")
        self.assertEqual(str(dre), "123 - DT")

        dre2 = DRE(codigo_dre="456", nome="DRE SEM SIGLA", sigla=None)
        self.assertEqual(str(dre2), "456 - DRE SEM SIGLA")

    def test_tipo_escola_str(self) -> None:
        """Verifica representação string de TipoEscola."""
        tipo = TipoEscola(codigo_tipo_escola=10, descricao="EMEF")
        self.assertEqual(str(tipo), "10 - EMEF")

    def test_subprefeitura_str(self) -> None:
        """Verifica representação string de SubPrefeitura."""
        sub = SubPrefeitura(nome="SÉ")
        self.assertEqual(str(sub), "SÉ")

    def test_unidade_educacional_str(self) -> None:
        """Verifica representação string de UnidadeEducacional."""
        ue = UnidadeEducacional(codigo_ue="098765", nome="ESC TESTE")
        self.assertEqual(str(ue), "098765 - ESC TESTE")

    def test_institucional_consulta_log_str(self) -> None:
        """Verifica representação string de InstitucionalConsultaLog."""
        from apps.institucional.models import InstitucionalConsultaLog

        log = InstitucionalConsultaLog(offset_inicial=100, limite=50)
        self.assertEqual(str(log), "offset=100 limite=50")
