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


def parse_date(val: Any) -> date | None:
    """Converte valor para date, tratando strings ISO (com ou sem tempo)."""
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
