from datetime import date, datetime

from django.test import SimpleTestCase
from django.utils import timezone

from apps.core.libs.helpers import (
    make_aware,
    parse_date,
    strip_str,
)


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


class ParseDateTest(SimpleTestCase):
    """Valida parse_date seguindo o contrato de saneamento de ETL."""

    def test_iso_string_com_tempo(self) -> None:
        self.assertEqual(
            parse_date("2025-04-13T10:00:00"), date(2025, 4, 13)
        )

    def test_iso_string_apenas_data(self) -> None:
        self.assertEqual(parse_date("2025-04-13"), date(2025, 4, 13))

    def test_objeto_date_retorna_igual(self) -> None:
        d = date(2025, 4, 13)
        self.assertIs(parse_date(d), d)

    def test_objeto_datetime_converte(self) -> None:
        dt = datetime(2025, 4, 13, 10, 0, 0)
        self.assertEqual(parse_date(dt), date(2025, 4, 13))

    def test_none_retorna_none(self) -> None:
        self.assertIsNone(parse_date(None))

    def test_string_invalida_retorna_none(self) -> None:
        self.assertIsNone(parse_date("invalido"))

    def test_tipo_invalido_retorna_none(self) -> None:
        self.assertIsNone(parse_date(123))


class MakeAwareTest(SimpleTestCase):
    """Valida make_aware para os ramos de None, str, naive e aware."""

    def test_none_retorna_none(self) -> None:
        self.assertIsNone(make_aware(None))

    def test_string_iso_retorna_aware(self) -> None:
        result = make_aware("2025-01-01T10:00:00")
        self.assertFalse(timezone.is_naive(result))

    def test_naive_datetime_retorna_aware(self) -> None:
        naive = datetime(2025, 1, 1, 12, 0, 0)
        result = make_aware(naive)
        self.assertFalse(timezone.is_naive(result))

    def test_aware_datetime_retorna_mesmo_objeto(self) -> None:
        aware = timezone.make_aware(
            datetime(2025, 1, 1, 12, 0, 0),
            timezone.get_current_timezone(),
        )
        self.assertIs(make_aware(aware), aware)




