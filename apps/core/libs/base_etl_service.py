"""Motor de processamento e auditoria para serviços de ETL.

Responsabilidade:
    - Gerenciar o ciclo de vida do Upsert Incremental.
    - Orquestrar a Auditoria via SHA-256 com comparação dentro do Postgres.
    - Oferecer pipeline Producer-Consumer para overlap MSSQL↔Postgres.
    - Escrita via COPY + staging para máxima throughput no Postgres.
"""

import io
import logging
import queue
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from functools import partial
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import connections, transaction

from apps.controle_auditoria.models import EtlAuditoriaLinha
from apps.core.libs.thread_processor import (
    ThreadPoolProcessor,
    calcular_hash,
    decorar_para_hash,
)

logger = logging.getLogger(__name__)

# Sentinela imutável para sinalizar fim de fila aos consumers.
_SENTINEL = object()


@dataclass
class StageTimer:
    """Cronômetro para fases do ETL."""

    name: str
    start: float = field(default_factory=time.monotonic)
    end: float = 0.0

    def stop(self) -> float:
        """Para o cronômetro e retorna o tempo decorrido em segundos."""
        self.end = time.monotonic()
        return self.end - self.start


@dataclass
class PipelineMetrics:
    """Métricas de execução do pipeline."""

    total_lidos: int = 0
    total_escritos: int = 0
    total_ignorados: int = 0
    erros: list = field(default_factory=list)


class PostgresUpsertEngine:
    """Motor de baixa latência para escrita de hashes de auditoria no Postgres.

    Todos os escritas são direcionadas ao banco ``default``, onde a tabela
    de auditoria centralizada ``etl_auditoria_linha`` reside.
    """

    def upsert_bulk(
        self,
        table_name: str,
        rows: list[tuple[str, str]],
        batch_id: str = "batch",
    ) -> int:
        """Executa upsert de hashes de auditoria via COPY + Temp Table.

        Args:
            table_name: Nome da tabela de destino no banco ``default``.
            rows: Lista de tuplas ``(id_destino, hash_controle)``.
            batch_id: Identificador do lote (compõe o nome da temp table).

        Returns:
            Número de linhas afetadas pelo upsert.
        """
        if not rows:
            return 0

        buffer = io.StringIO()
        for id_dest, h in rows:
            buffer.write(f"{id_dest}\t{h}\n")
        buffer.seek(0)

        with (
            transaction.atomic(using="default"),
            connections["default"].cursor() as cursor,
        ):
            temp_table = f"temp_audit_{batch_id.replace('-', '_')}"
            cursor.execute(
                f"CREATE TEMP TABLE {temp_table} "
                "(id_destino text, hash_controle text) ON COMMIT DROP"
            )

            raw_cursor = cursor.cursor
            if hasattr(raw_cursor, "copy"):
                with raw_cursor.copy(
                    f"COPY {temp_table} (id_destino, hash_controle)"
                    " FROM STDIN"
                ) as copy:
                    copy.write(buffer.getvalue())
            else:
                buffer.seek(0)
                raw_cursor.copy_from(
                    buffer,
                    temp_table,
                    columns=("id_destino", "hash_controle"),
                )

            cursor.execute(
                f"""
                    INSERT INTO {table_name}
                        (id_destino, hash_controle, atualizado_em)
                    SELECT id_destino, hash_controle, NOW()
                    FROM {temp_table}
                    ON CONFLICT (id_destino) DO UPDATE
                    SET hash_controle = EXCLUDED.hash_controle,
                        atualizado_em = NOW()
                    WHERE {table_name}.hash_controle
                        <> EXCLUDED.hash_controle
                """
            )
            return int(cursor.rowcount or 0)


class BaseEtlService:
    """Base para serviços de ETL orquestrados (High Performance)."""

    def __init__(
        self,
        db_alias: str,
        id_execucao: UUID | None = None,
        repositorio_auditoria: Any | None = None,
        id_min: int | None = None,
        id_max: int | None = None,
        primeiro_run: bool = False,
    ) -> None:
        self.db_alias = db_alias
        self.id_execucao = id_execucao
        self.auditor = repositorio_auditoria
        self.id_min = id_min
        self.id_max = id_max
        self.primeiro_run = primeiro_run
        self.pg_engine = PostgresUpsertEngine()
        self._max_workers: int = settings.THREAD_POOL_MAX_WORKERS
        self._n_consumers: int = getattr(settings, "THREAD_POOL_MAX_WORKERS", 4)

    def create_transformer(
        self,
        dto_in: Any,
        dto_out: Any,
        model_class: Any,
        pk_field: str | list[str],
    ) -> Callable[[tuple], tuple[Any, Any]]:
        """Gera transformador para o pipeline."""

        def transform(row: tuple) -> tuple[Any, Any]:
            dto = dto_in(*row)
            if isinstance(pk_field, list):
                pk = "-".join(str(getattr(dto, f)) for f in pk_field)
            else:
                pk = getattr(dto, pk_field)
            return pk, model_class(**dto_out.to_dict(dto))

        return transform

    def _get_partition_sql(self, base_sql: str, id_column: str) -> str:
        """Injeta limites de partição na query base."""
        if self.id_min is None or self.id_max is None:
            return base_sql
        if "WHERE" in base_sql.upper():
            return (
                f"{base_sql} AND {id_column}"
                f" BETWEEN {self.id_min} AND {self.id_max}"
            )
        return (
            f"{base_sql} WHERE {id_column}"
            f" BETWEEN {self.id_min} AND {self.id_max}"
        )

    def _get_union_partition_sql(self, union_sql: str, id_column: str) -> str:
        """Injeta filtro de partição em cada membro de um UNION ALL.

        Necessário para queries com ``UNION ALL``, onde um ``WHERE``
        simples no final seria aplicado apenas ao último ``SELECT``,
        deixando os demais sem filtro e causando full scan.
        """
        if self.id_min is None or self.id_max is None:
            return union_sql
        partes = union_sql.split("UNION ALL")
        partes_filtradas = [
            self._get_partition_sql(p.strip(), id_column) for p in partes
        ]
        return "\nUNION ALL\n".join(partes_filtradas)

    def sync_table(
        self,
        db_table: str,
        update_fields: list[str],
        extractor_iterator: Iterator[list[tuple]],
        transform_func: Callable,
        unique_fields: list[str],
        model_class: Any,
    ) -> PipelineMetrics:
        """Pipeline Producer-Consumer para sincronização de alto volume.

        O producer extrai lotes do MSSQL e calcula hashes em paralelo
        via ``ThreadPoolProcessor`` reutilizado entre lotes. Os consumers
        (``ETL_N_CONSUMERS``) fazem o filtro diferencial e a escrita no
        Postgres concorrentemente.

        Quando ``primeiro_run=True``, a consulta de hashes existentes é
        suprimida e todos os registros são escritos diretamente.

        Args:
            db_table: Nome da tabela de destino.
            update_fields: Campos a atualizar no upsert.
            extractor_iterator: Iterador de lotes de linhas do MSSQL.
            transform_func: Converte linha bruta em ``(pk, objeto)``.
            unique_fields: Campos que formam a chave única.
            model_class: Classe do modelo Django de destino.

        Returns:
            Métricas de execução do pipeline.
        """
        metrics = PipelineMetrics()
        metrics_lock = threading.Lock()
        hash_queue: queue.Queue = queue.Queue(maxsize=100)

        def _hash_wrapper(row: Any) -> tuple[str, str, Any]:
            val_id, obj = transform_func(row)
            return (
                f"{db_table}:{val_id}",
                calcular_hash(obj, update_fields),
                obj,
            )

        def producer() -> None:
            """Extrai do MSSQL e calcula hashes com pool reutilizado."""
            try:
                with ThreadPoolProcessor(
                    max_workers=self._max_workers,
                    prefixo_log=f"ETL {db_table.upper()}",
                ) as processor:
                    for batch_num, linhas in enumerate(extractor_iterator):
                        if not linhas:
                            continue
                        resultados_hash = processor.processar(
                            linhas, _hash_wrapper
                        )
                        # total_lidos é atualizado apenas pelo producer
                        # (thread única), sem necessidade de lock.
                        metrics.total_lidos += len(linhas)
                        hash_queue.put((batch_num, resultados_hash))
                        if batch_num % 10 == 0:
                            logger.info(
                                "[%s] Producer: %d lidos...",
                                db_table,
                                metrics.total_lidos,
                            )
            except Exception as exc:
                logger.exception("Erro no Producer de %s: %s", db_table, exc)
                with metrics_lock:
                    metrics.erros.append(exc)
            finally:
                for _ in range(self._n_consumers):
                    hash_queue.put(_SENTINEL)

        def consumer() -> None:
            """Consome hashes, aplica filtro diferencial e persiste.

            Acumula contadores locais durante o processamento (zero
            contenção no hot path) e faz um único merge atômico em
            ``metrics`` ao final, via ``metrics_lock``.
            """
            escritos_local = 0
            ignorados_local = 0
            erros_local: list = []

            try:
                while True:
                    item = hash_queue.get()
                    try:
                        if item is _SENTINEL:
                            break
                        batch_num, batch_data = item
                        escritos, ignorados = _processar_batch(
                            batch_num, batch_data
                        )
                        escritos_local += escritos
                        ignorados_local += ignorados
                    except Exception as exc:
                        logger.exception(
                            "Erro no Consumer de %s: %s", db_table, exc
                        )
                        erros_local.append(exc)
                    finally:
                        hash_queue.task_done()
            except Exception as exc:
                logger.exception(
                    "Falha inesperada no Consumer de %s: %s", db_table, exc
                )
                erros_local.append(exc)
            finally:
                # Merge atômico: uma única aquisição de lock por consumer.
                with metrics_lock:
                    metrics.total_escritos += escritos_local
                    metrics.total_ignorados += ignorados_local
                    metrics.erros.extend(erros_local)

        def _processar_batch(
            batch_num: int,
            batch_data: list[tuple[str, str, Any]],
        ) -> tuple[int, int]:
            """Filtra, escreve no domínio e atualiza auditoria.

            Returns:
                Tupla ``(escritos, ignorados)`` do lote processado.
            """
            if self.primeiro_run:
                objs_para_pg = [obj for _, _, obj in batch_data]
                hashes_para_pg = [(id_dest, h) for id_dest, h, _ in batch_data]
                ignorados = 0
            else:
                ids_dest = [r[0] for r in batch_data]
                hashes_existentes = dict(
                    EtlAuditoriaLinha.objects.filter(
                        id_destino__in=ids_dest
                    ).values_list("id_destino", "hash_controle")
                )
                objs_para_pg = []
                hashes_para_pg = []
                ignorados = 0
                for id_dest, h, obj in batch_data:
                    if hashes_existentes.get(id_dest) != h:
                        objs_para_pg.append(obj)
                        hashes_para_pg.append((id_dest, h))
                    else:
                        ignorados += 1

            if not objs_para_pg:
                return 0, ignorados

            with transaction.atomic(using=self.db_alias):
                model_class.objects.using(self.db_alias).bulk_create(
                    objs_para_pg,
                    update_conflicts=True,
                    unique_fields=unique_fields,
                    update_fields=update_fields,
                    batch_size=len(objs_para_pg),
                )

            batch_id = f"{db_table}_{batch_num}"
            if self.auditor and hasattr(self.auditor, "upsert_bulk_hashes"):
                self.auditor.upsert_bulk_hashes(hashes_para_pg, batch_id)
            else:
                self.pg_engine.upsert_bulk(
                    "etl_auditoria_linha", hashes_para_pg, batch_id
                )
            return len(objs_para_pg), ignorados

        t_prod = threading.Thread(target=producer, daemon=True)
        consumers = [
            threading.Thread(target=consumer, daemon=True)
            for _ in range(self._n_consumers)
        ]

        t_prod.start()
        for t in consumers:
            t.start()

        t_prod.join()
        for t in consumers:
            t.join()

        self._registrar_auditoria(db_table, metrics)
        return metrics

    def _registrar_auditoria(
        self, tabela: str, metrics: PipelineMetrics
    ) -> None:
        """Registrar metricas finais da tabela via auditor injetado."""
        if not self.auditor or not self.id_execucao:
            return
        try:
            self.auditor.registrar_tabela_lida(
                self.id_execucao, tabela, 0, metrics.total_lidos
            )
            self.auditor.registrar_tabela_escrita(
                self.id_execucao,
                tabela,
                metrics.total_escritos,
                "upsert_turbo",
            )
        except Exception as exc:
            logger.warning(
                "Erro ao registrar auditoria final para %s: %s", tabela, exc
            )

    # --- Métodos de compatibilidade (Legacy Bridge) ---

    def _upsert(
        self,
        model_class: Any,
        tabela: str,
        objs: list,
        update_fields: list[str],
        unique_fields: list[str] | None = None,
        numero_pagina: int = 1,
    ) -> int:
        """Ponte legada para upsert incremental com hash.

        Mantém compatibilidade com código anterior à migração para
        ``sync_table``.
        """
        linhas_lidas = len(objs)
        linhas_escritas = upsert_incremental(
            model_class=model_class,
            tabela=tabela,
            objs=objs,
            update_fields=update_fields,
            using_db=self.db_alias,
            unique_fields=unique_fields,
        )

        if self.auditor and self.id_execucao:
            self.auditor.registrar_tabela_lida(
                self.id_execucao, tabela, numero_pagina, linhas_lidas
            )
            self.auditor.registrar_tabela_escrita(
                self.id_execucao, tabela, linhas_escritas, "upsert_legacy"
            )

        return linhas_escritas


def upsert_incremental(
    model_class: Any,
    tabela: str,
    objs: list,
    update_fields: list[str],
    using_db: str,
    unique_fields: list[str] | None = None,
) -> int:
    """Upsert incremental com controle de hash (implementação legada).

    Calcula hashes em paralelo, filtra registros não alterados e persiste
    apenas as diferenças. Utilizado via ``_upsert`` na bridge de legado.
    """
    if not objs:
        return 0

    pk_name = unique_fields[0] if unique_fields else model_class._meta.pk.name

    processor = ThreadPoolProcessor(prefixo_log=f"ETL {tabela[:6].upper()}")
    func = partial(decorar_para_hash, tabela, update_fields)
    linhas_com_hash = processor.processar(
        [(getattr(o, pk_name), o) for o in objs], func
    )

    ids_dest = [r[0] for r in linhas_com_hash]
    hashes_existentes = dict(
        EtlAuditoriaLinha.objects.filter(id_destino__in=ids_dest).values_list(
            "id_destino", "hash_controle"
        )
    )

    para_salvar = []
    novos_hashes = []
    for id_dest, h, obj in linhas_com_hash:
        if hashes_existentes.get(id_dest) != h:
            para_salvar.append(obj)
            novos_hashes.append(
                EtlAuditoriaLinha(id_destino=id_dest, hash_controle=h)
            )

    if para_salvar:
        model_class.objects.using(using_db).bulk_create(
            para_salvar,
            update_conflicts=True,
            unique_fields=unique_fields or [pk_name],
            update_fields=update_fields,
        )
        EtlAuditoriaLinha.objects.bulk_create(
            novos_hashes,
            update_conflicts=True,
            unique_fields=["id_destino"],
            update_fields=["hash_controle"],
        )

    return len(para_salvar)
