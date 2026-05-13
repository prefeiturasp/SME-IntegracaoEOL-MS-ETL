"""Utilitários de saneamento para pipelines de ETL."""

from datetime import date, datetime
from typing import Any, cast

from django.utils import timezone


def strip_str(val: Any) -> str | None:
    r"""Remove espaços e caracteres nulos (\x00), aceita qualquer tipo."""
    if val is None:
        return None
    sanitized = str(val).strip().replace("\x00", "")
    return sanitized if sanitized else None


def int_or_none(value: Any) -> int | None:
    """Converta valor para int, preservando None."""
    return int(value) if value is not None else None


def str_or_none(value: Any) -> str | None:
    """Converta valor truthy para str; valores vazios viram None."""
    return str(value) if value else None


def str_value_or_none(value: Any) -> str | None:
    """Converta valor para str, preservando apenas None."""
    return str(value) if value is not None else None


def strip_or_none(value: Any) -> str | None:
    """Aplica strip_str apenas quando há valor truthy."""
    return strip_str(value) if value else None


def parse_date(val: Any) -> date | None:
    """Converta valor para date, tratando strings ISO."""
    if val is None:
        return None

    if isinstance(val, datetime):
        return val.date()

    if isinstance(val, date):
        return val

    if isinstance(val, str):
        try:
            # Tenta YYYY-MM-DD
            return date.fromisoformat(val[:10])
        except (ValueError, TypeError):
            return None

    return None


def make_aware(dt: str | datetime | None) -> datetime | None:
    """Garante que o datetime seja timezone-aware, tolerando None e strings."""
    if dt is None:
        return None

    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)

    if timezone.is_naive(dt):
        return cast(
            datetime, timezone.make_aware(dt, timezone.get_current_timezone())
        )

    return dt


def aware_or_none(value: str | datetime | None) -> datetime | None:
    """Aplica make_aware apenas quando há valor truthy."""
    return make_aware(value) if value else None
