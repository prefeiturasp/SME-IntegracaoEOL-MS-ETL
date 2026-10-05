"""Adaptador de logger com contexto fixo para correlação de execuções ETL."""

import logging
from collections.abc import MutableMapping
from typing import Any


class ContextualLogger(logging.LoggerAdapter):
    """LoggerAdapter que injeta contexto ETL fixo em cada linha de log.

    O contexto fixo (execution_id, dominio, job_name) é propagado
    automaticamente para todas as chamadas de log sem necessidade de
    repeti-lo em cada chamada.
    """

    def __init__(
        self, logger: logging.Logger, extra: dict[str, Any] | None = None
    ) -> None:
        _extra: dict[str, Any] = extra or {}
        if extra is not None and not isinstance(extra, dict):
            raise ValueError("extra precisa ser um dicionário")
        super().__init__(logger, _extra)
        self._ctx: dict[str, Any] = _extra

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        """Combina o contexto fixo da execução com o extra por chamada.

        O contexto fixo tem menor precedência: campos passados por chamada
        sobrescrevem campos de mesmo nome no contexto fixo.
        """
        additional_context = kwargs.pop("extra", {})
        if not isinstance(additional_context, dict):
            raise ValueError("extra precisa ser um dicionário")
        kwargs["extra"] = {**self._ctx, **additional_context}
        return msg, kwargs

    def update_context(self, **new_context: object) -> None:
        """Atualiza o contexto fixo com novos campos ou valores modificados."""
        self._ctx.update(new_context)
        for key in self._ctx:
            if not isinstance(key, str):
                raise ValueError(
                    "Todas as chaves do contexto devem ser strings"
                )

    @classmethod
    def get_etl_logger(cls, name: str, **kwargs: Any) -> "ContextualLogger":
        """Retorna um ContextualLogger com prefixo 'etl_' no nome do logger."""
        logger = logging.getLogger(f"etl_{name}")
        context = {k: kwargs[k] for k in kwargs if kwargs[k] is not None}
        return cls(logger, context)
