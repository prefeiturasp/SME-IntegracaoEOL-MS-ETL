"""Filtros de formatacao para templates de auditoria."""

import json
from decimal import Decimal, InvalidOperation
from typing import Any

from django import template

register = template.Library()


@register.filter(name="numero_br")
def numero_br(value: Any) -> Any:
    """Formata numeros com separador de milhar no padrao brasileiro."""
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return value

    if number != number.to_integral_value():
        return value

    return f"{int(number):,}".replace(",", ".")


@register.filter(name="json_bruto")
def json_bruto(value: Any) -> str:
    """Serializa valor para JSON seguro em blocos de diagnóstico."""
    return json.dumps(value or {}, ensure_ascii=False, default=str)
