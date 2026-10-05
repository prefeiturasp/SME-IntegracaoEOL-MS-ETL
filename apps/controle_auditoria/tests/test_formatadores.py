"""Testes dos filtros de template de auditoria."""

from django.test import SimpleTestCase

from apps.controle_auditoria.templatetags.formatadores import numero_br


class NumeroBrFilterTestCase(SimpleTestCase):
    """Valida formatacao numerica em padrao brasileiro."""

    def test_formata_inteiros_com_separador_de_milhar(self) -> None:
        """Numeros inteiros devem usar ponto como separador de milhar."""
        self.assertEqual(numero_br(1000), "1.000")
        self.assertEqual(numero_br("1500000"), "1.500.000")

    def test_preserva_valores_nao_numericos(self) -> None:
        """Valores nao numericos nao devem ser alterados."""
        self.assertEqual(numero_br("abc"), "abc")
        self.assertEqual(numero_br("10.5"), "10.5")
