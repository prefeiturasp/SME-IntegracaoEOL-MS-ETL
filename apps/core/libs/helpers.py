from datetime import date, datetime
from typing import Any


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
