"""Registra gerações de dados e integridade das cargas de professores."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

from django.db import transaction

from apps.professores.models import ControleCargaProfessores

_BANCO = "professores_db"
logger = logging.getLogger(__name__)


def _iniciar(token: str, completa: bool, amostral: bool) -> None:
    with transaction.atomic(using=_BANCO):
        estados = ControleCargaProfessores.objects.using(_BANCO)
        estados.get_or_create(pk=1)
        estado = estados.select_for_update().get(pk=1)
        if amostral:
            estado.falha = True
        elif completa and not estado.cargas_ativas:
            estado.falha = False
        estado.cargas_ativas = [*estado.cargas_ativas, token]
        estado.geracao = uuid4()
        estado.save(using=_BANCO)


def _finalizar(token: str, falhou: bool) -> None:
    with transaction.atomic(using=_BANCO):
        estado = (
            ControleCargaProfessores.objects.using(_BANCO)
            .select_for_update()
            .get(pk=1)
        )
        if token not in estado.cargas_ativas:
            raise RuntimeError("Registro da carga não encontrado.")
        estado.cargas_ativas = [
            atual for atual in estado.cargas_ativas if atual != token
        ]
        estado.falha = estado.falha or falhou
        estado.geracao = uuid4()
        estado.save(using=_BANCO)


@contextmanager
def registrar_carga(
    *,
    completa: bool,
    amostral: bool = False,
) -> Iterator[None]:
    """Registra uma carga e mantém sua situação até a conclusão.

    Args:
        completa: Indica uma recarga de todas as fontes do domínio.
        amostral: Indica uma carga limitada que deixa as fontes incompletas.

    Yields:
        Execução protegida pelo registro persistente da carga.
    """
    token = str(uuid4())
    _iniciar(token, completa, amostral)
    try:
        yield
    except BaseException:
        try:
            _finalizar(token, falhou=True)
        except Exception:
            logger.error(
                "Falha ao finalizar o registro da carga interrompida."
            )
        raise
    else:
        _finalizar(token, falhou=False)
