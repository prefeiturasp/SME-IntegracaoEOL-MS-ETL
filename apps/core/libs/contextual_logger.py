"""Adaptador de logger com contexto fixo para correlação de execuções ETL."""

import logging
from typing import Any


class ContextualLogger(logging.LoggerAdapter):
    """LoggerAdapter que injeta contexto ETL fixo em cada linha de log.

    O contexto fixo (execution_id, dominio, job_name) é propagado automaticamente
    para todas as chamadas de log sem necessidade de repeti-lo em cada chamada.
    """

    def __init__(self, logger: logging.Logger, extra: dict | None = None) -> None:
        if extra is None:
            extra = {}
        elif not isinstance(extra, dict):
            raise ValueError("extra precisa ser um dicionário")
        super().__init__(logger, extra)

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        """Combina o contexto fixo da execução com o contexto extra por chamada.

        O contexto fixo tem menor precedência: campos passados por chamada
        sobrescrevem campos de mesmo nome no contexto fixo.
        """
        additional_context = kwargs.pop("extra", {})
        if not isinstance(additional_context, dict):
            raise ValueError("extra precisa ser um dicionário")
        kwargs["extra"] = {**self.extra, **additional_context}
        return msg, kwargs

    def update_context(self, **new_context: object) -> None:
        """Atualiza o contexto fixo com novos campos ou valores modificados."""
        self.extra.update(new_context)
        for key in self.extra:
            if not isinstance(key, str):
                raise ValueError("Todas as chaves do contexto devem ser strings")

    @classmethod
    def get_etl_logger(cls, name: str, **kwargs: Any) -> "ContextualLogger":
        """Retorna um ContextualLogger com prefixo 'etl_' no nome do logger."""
        logger = logging.getLogger(f"etl_{name}")
        context = {k: v for k, v in kwargs.items() if v is not None}
        return cls(logger, context)
