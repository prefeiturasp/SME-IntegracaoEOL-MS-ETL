"""Tasks Celery genéricas para orquestração de ETL."""

import logging
import os
from typing import Any
from uuid import UUID

from celery import Task, chord, group, shared_task

from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)
from apps.core.libs.base_etl_chunck import BaseEtlChunk
from apps.core.libs.base_etl_fase import BaseEtlFase
from apps.core.libs.base_etl_service import PostgresUpsertEngine
from apps.core.libs.thread_processor import ThreadPoolProcessor

logger = logging.getLogger(__name__)


def _resolver_rate_limit() -> str | None:
    """Lê ETL_RATE_LIMIT do ambiente com fallback para '100/m'."""
    val = os.getenv("ETL_RATE_LIMIT", "100/m")
    return val if val else None


@shared_task(
    bind=True,
    name="etl.core.processar_chunk",
    queue="fila_etl_padrao",
    max_retries=3,
    acks_late=True,
    prefetch_multiplier=1,
    rate_limit=_resolver_rate_limit(),
)

def processar_chunk(
    self: Task,
    chunk: list[tuple],
    fase_meta_dict: dict[str, Any],
) -> tuple[int, int]:
    """Processa chunk do domínio, transformando e persistindo dados."""
    try:
        fase_meta = BaseEtlFase.from_dict(fase_meta_dict)
        transform = fase_meta.get_transformer()

        processor = ThreadPoolProcessor()
        processed = processor.processar(chunk, transform)
        del chunk

        upsert = PostgresUpsertEngine()
        escritos, ignorados = upsert.sincronizar_lote(processed, fase_meta)
        del processed

        return escritos, ignorados

    except Exception as exc:
        logger.error(
            "[%s] Erro no processamento do chunk: %s",
            fase_meta_dict.get("dominio", "ETL").upper(),
            exc,
        )
        raise self.retry(exc=exc, countdown=30) from exc


@shared_task(
    name="etl.core.finalizar_fase",
    queue="fila_etl_padrao",
)
def finalizar_fase(
    resultados: list[tuple[int, int]],
    fase_meta_dict: dict[str, Any],
    todas_fases_dict: list[dict[str, Any]],
) -> None:
    """Agrega resultados, registra auditoria e lança a próxima fase."""
    fase_meta = BaseEtlFase.from_dict(fase_meta_dict)
    total_escritos = sum(r[0] for r in resultados)
    total_lidos = sum(r[0] + r[1] for r in resultados)

    logger.info(
        "[%s] Fase %d (%s) concluída. %d alterados / %d lidos.",
        fase_meta.dominio.upper(),
        fase_meta.numero_fase,
        fase_meta.nome,
        total_escritos,
        total_lidos,
    )

    repositorio = RepositorioAuditoriaPostgres()

    is_ultima_fase = fase_meta.numero_fase == fase_meta.total_fases

    if fase_meta.id_execucao:
        id_exec = UUID(fase_meta.id_execucao)
        repositorio.registrar_tabela_lida(
            id_execucao=id_exec,
            tabela_origem=fase_meta.source_table,
            numero_pagina=fase_meta.numero_fase,
            linhas_lidas=total_lidos,
        )
        repositorio.registrar_tabela_escrita(
            id_execucao=id_exec,
            tabela_destino=fase_meta.table_name,
            linhas_escritas=total_escritos,
            modo_escrita="upsert",
        )

    repositorio.atualizar_checkpoint_dominio(
        dominio=fase_meta.dominio,
        ultimo_id_execucao=(
            UUID(fase_meta.id_execucao) if fase_meta.id_execucao else None
        ),
        ultima_pagina=fase_meta.numero_fase,
        token_parada=str(total_escritos),
        indice_sincronizacao=f"{fase_meta.nome}:offset:{total_escritos}",
        ultima_situacao="concluido" if is_ultima_fase else "em_execucao",
        sucesso=is_ultima_fase,
    )

    if not is_ultima_fase:
        _lancar_fase_seguinte(fase_meta, todas_fases_dict)
    elif fase_meta.id_execucao:
        repositorio.finalizar_execucao(
            UUID(fase_meta.id_execucao), situacao="concluido"
        )
        logger.info(
            "[%s] Execução %s finalizada com sucesso.",
            fase_meta.dominio.upper(),
            fase_meta.id_execucao,
        )


def _lancar_fase_seguinte(
    fase_atual: BaseEtlFase, todas_fases: list[dict[str, Any]]
) -> None:
    """Dispara o chord da próxima fase utilizando o motor genérico."""
    proxima_meta_dict = todas_fases[fase_atual.numero_fase]
    proxima_meta = BaseEtlFase.from_dict(proxima_meta_dict)

    task_proc = proxima_meta.resolver_task_processamento()
    task_callback = proxima_meta.resolver_task_callback()

    if not task_proc or not task_callback:
        logger.error(
            "[%s] Falha ao resolver tasks para fase %d.",
            proxima_meta.dominio.upper(),
            proxima_meta.numero_fase,
        )
        return

    leitor = BaseEtlChunk(task_processamento=task_proc)
    tasks = leitor.criar_grupo(proxima_meta)

    if not tasks:
        logger.warning(
            "[%s] Fase %d sem chunks — pulando.",
            proxima_meta.dominio.upper(),
            proxima_meta.numero_fase,
        )
        task_callback.apply_async(args=[[], proxima_meta_dict, todas_fases])
        return

    callback = task_callback.s(proxima_meta_dict, todas_fases)
    chord(group(tasks))(callback)
    logger.info(
        "[%s] Próxima fase (%d/%d) lançada via chord.",
        proxima_meta.dominio.upper(),
        proxima_meta.numero_fase,
        proxima_meta.total_fases,
    )
