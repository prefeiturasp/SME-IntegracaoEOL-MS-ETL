"""Utilitários de saneamento de strings para pipelines de ETL."""

from typing import Any


def strip_str(val: Any) -> str | None:
    r"""Remove espaços e caracteres nulos (\x00), aceita qualquer tipo."""
    if val is None:
        return None
    sanitized = str(val).strip().replace("\x00", "")
    return sanitized if sanitized else None
