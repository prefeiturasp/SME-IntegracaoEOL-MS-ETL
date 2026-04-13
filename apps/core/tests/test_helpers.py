"""Testes para utilitários de saneamento de strings."""

from django.test import SimpleTestCase

from apps.core.libs.helpers import strip_str


class StripStrTest(SimpleTestCase):
    """Valida strip_str nos casos de borda relevantes."""

    def test_none_retorna_none(self) -> None:
        self.assertIsNone(strip_str(None))

    def test_string_com_espacos_e_removida(self) -> None:
        self.assertEqual(strip_str("  texto  "), "texto")

    def test_string_vazia_retorna_none(self) -> None:
        self.assertIsNone(strip_str("   "))

    def test_nulo_unicode_removido(self) -> None:
        self.assertEqual(strip_str("abc\x00def"), "abcdef")

    def test_inteiro_convertido(self) -> None:
        self.assertEqual(strip_str(42), "42")
