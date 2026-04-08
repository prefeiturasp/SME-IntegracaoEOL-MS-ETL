"""Processador paralelo de chunks via ThreadPoolExecutor.

Responsabilidades:
- Receber uma lista de itens e uma função de transformação.
- Executar em paralelo com ``ThreadPoolExecutor(max_workers=...)``.
- Preservar a ordem dos resultados (índice → resultado).
- Isolar erros por thread: logar ``[prefixo_log] Erro na thread N: <exc>``
  e re-raise após todas concluírem.
- Registrar throughput ao final:
  ``[prefixo_log] throughput: N itens em Xs (M itens/s)``.
- Respeitar ``timeout``: se excedido, logar e lançar ``TimeoutError``.
"""

import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from functools import partial
from typing import Any, Callable, List, TypeVar

from django.conf import settings

logger = logging.getLogger(__name__)
T = TypeVar("T")

class ThreadPoolProcessor:
    """Executa transformações locais em paralelo via ThreadPoolExecutor.

    Projetado para uso dentro de Celery Workers — controla o paralelismo
    local no processamento de chunks sem impactar o broker ou os bancos.
    """

    def __init__(
        self,
        max_workers: int | None = None,
        timeout: int | None = None,
        prefixo_log: str = "ETL",
    ) -> None:
        self.max_workers = max_workers or settings.THREAD_POOL_MAX_WORKERS
        self.timeout = timeout or settings.THREAD_POOL_CHUNK_TIMEOUT
        self.prefixo_log = prefixo_log
    
    def processar(self, items: list[Any], func: Callable[[Any], T]) -> List[T]:
        """Processa itens em paralelo preservando a ordem.

        Erros individuais são logados e isolados; a primeira exceção
        encontrada é relançada após todas as futures concluírem ou
        cancelarem. Se o timeout for excedido, um ``TimeoutError`` é
        lançado.
        """

        if not items:
            return []
        
        resultados: list[T | None] = [None] * len(items)
        erro_caputurado: Exception | None = None
        inicio = time.monotonic()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(func, item): idx for idx, item in enumerate(items)}

            try:
                for future in as_completed(futures, timeout=self.timeout):
                    idx = futures[future]
                    try:
                        resultados[idx] = future.result()
                    except Exception as exc:
                        logger.exception(
                            "[%s] Erro na thread %d: %s", self.prefixo_log, idx, exc
                        )
                        if erro_caputurado is None:
                            erro_caputurado = exc
            except TimeoutError:
                for future in futures:
                    future.cancel()
                msg = (
                    f"[{self.prefixo_log}] Timeout após {self.timeout}s "
                    f"processando {len(items)} itens"
                )
                logger.error(msg)
                raise TimeoutError(msg)

        elapsed = time.monotonic() - inicio
        self._log_throughput(len(items), elapsed)

        if erro_caputurado is not None:
            raise erro_caputurado
        
        return resultados  # type: ignore[return-value]
    
    def _log_throughput(self, total: int, elapsed: float) -> None:
        taxa = total / elapsed if elapsed > 0 else float("inf")
        logger.info(
            "[%s] throughput: %d itens em %.2fs (%.2f itens/s)",
            self.prefixo_log,
            total,
            elapsed,
            taxa,
        )


def calcular_hash(obj: Any, update_fields: list[str]) -> str:
    """Calcula SHA-256 dos campos de atualização para controle incremental.

    Aceita instâncias Django (via ``getattr``) ou dicts (via ``.get``).
    """
    if isinstance(obj, dict):
        data = {f: obj.get(f) for f in update_fields}
    else:
        data = {f: getattr(obj, f) for f in update_fields}
    conteudo = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(conteudo).hexdigest()


def decorar_para_hash(tabela: str, update_fields: list[str], item: tuple) -> tuple:
    """Transforma ``(pk, obj)`` em ``(id_destino, hash, obj)``.

    Função utilitária compartilhada entre os services de todos os
    domínios. Use com ``functools.partial`` para fixar ``tabela`` e
    ``update_fields``::

        func = partial(decorar_para_hash, tabela, update_fields)
        linhas = processor.processar(items, func)
    """
    pk_val, obj = item
    return (f"{tabela}:{pk_val}", calcular_hash(obj, update_fields), obj)