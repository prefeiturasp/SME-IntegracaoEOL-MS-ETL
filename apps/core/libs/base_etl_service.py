"""Motor de processamento e auditoria para serviços de ETL.

Responsabilidade:
    - Gerenciar o ciclo de vida do Upsert Incremental.
    - Orquestrar a Auditoria via SHA-256 com comparação dentro do Postgres.
    - Oferecer pipeline Producer-Consumer para overlap MSSQL↔Postgres.
    - Escrita via COPY + staging para máxima throughput no Postgres.
"""

import io
import logging
import random
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from queue import Empty, Queue
from threading import Thread
from typing import Any, Union
from uuid import UUID

from django.conf import settings
from django.db import connections, transaction

from apps.core.libs.thread_processor import ThreadPoolProcessor, calcular_hash

logger = logging.getLogger(__name__)

_SENTINEL = object()


def _fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def retry_deadlock(max_retries: int = 3, backoff: float = 0.5) -> Callable:
    """Decorador para repetir operações em caso de Lock/Deadlock do banco."""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_err: Exception = RuntimeError(
                "retry_deadlock chamado com max_retries=0"
            )
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    msg = str(exc).lower()
                    if "deadlock" not in msg and "lock timeout" not in msg:
                        raise
                    last_err = exc
                    wait = backoff * (2**i) + random.uniform(0, 0.1)
                    logger.warning(
                        "Deadlock detectado. Tentativa %d/%d"
                        " (espera %.2fs)",
                        i + 1,
                        max_retries,
                        wait,
                    )
                    time.sleep(wait)
            raise last_err

        return wrapper

    return decorator


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


@dataclass(frozen=True)
class PhaseConfig:
    """Configuração de uma fase do pipeline ETL.

    Centraliza todos os metadados de uma fase: SQL de extração, modelo
    de destino, DTOs, campos de PK/hash e tabela de origem para auditoria.
    Imutável para evitar mutações acidentais durante a execução.

    Quando ``dto_out`` for ``None``, o pipeline usa ``dto_in.to_domain()``
    (padrão Adapter). Quando fornecido, usa ``dto_out.to_dict(dto)``
    para compatibilidade com apps que ainda não foram migrados.
    """

    nome: str
    sql: str
    table_name: str
    model_class: Any
    dto_in: Any
    pk_field: str | list[str]
    update_fields: tuple[str, ...]
    unique_fields: tuple[str, ...]
    dto_out: Any = None
    source_table: str = ""
    truncate_on_full_sync: bool = False
    audit_flush_size: int = 0
    suporta_bulk_insert: bool = False


class PostgresUpsertEngine:
    """Motor de baixa latência para escrita de hashes de auditoria no Postgres.

    Todos os escritas são direcionadas ao banco ``default``, onde a tabela
    de auditoria centralizada ``etl_auditoria_linha``.
    """

    @retry_deadlock()
    def upsert_bulk(self, *args: Any, **kwargs: Any) -> int:
        """Versão com retry de upsert_bulk."""
        return self._upsert_bulk_full(*args, **kwargs)

    def _upsert_bulk_full(
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

        rows.sort(key=lambda x: x[0])

        buffer = io.StringIO()
        try:
            for id_dest, h in rows:
                buffer.write(f"{id_dest}\t{h}\n")
            conteudo = buffer.getvalue()
        finally:
            buffer.close()

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
                    copy.write(conteudo)
            else:
                raw_cursor.copy_from(
                    io.StringIO(conteudo),
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
    """Base para serviços de ETL orquestrados (High Performance).

    Subclasses devem:
        - Definir ``_dominio`` como atributo de classe.
        - Implementar ``_iter_chunks(sql)`` para apontar à conexão de origem.
        - Popular ``self._fases`` em ``__init__`` com a lista de
          ``PhaseConfig`` do domínio.

    Com isso herdam automaticamente o pipeline Producer-Consumer com
    ThreadPool, auditoria por fase e controle de checkpoint.
    """

    _dominio: str = "ETL"

    def __init__(
        self,
        db_alias: str,
        id_execucao: UUID | None = None,
        repositorio_auditoria: Any | None = None,
        id_min: int | None = None,
        id_max: int | None = None,
        particao: int = 0,
        total_particoes: int = 1,
        primeiro_run: bool = False,
    ) -> None:
        self.db_alias = db_alias
        self.id_execucao = id_execucao
        self.auditor = repositorio_auditoria
        self.id_min = id_min
        self.id_max = id_max
        self.particao = particao
        self.total_particoes = total_particoes
        self.primeiro_run = primeiro_run
        self.pg_engine = PostgresUpsertEngine()
        self._max_workers: int = settings.THREAD_POOL_MAX_WORKERS
        self._n_consumers: int = getattr(settings, "ETL_N_CONSUMERS", 2)
        self.ultima_fase_concluida: int = 0
        self.ultimo_token: str | None = None
        self._fases: list[PhaseConfig] = []


    def _iter_chunks(self, sql: str) -> Iterator[list[tuple]]:
        """Itera chunks da fonte de origem."""
        raise NotImplementedError(
            f"{self.__class__.__name__} deve implementar _iter_chunks"
        )


    def _get_partition_sql(self, sql: str, coluna_id: str) -> str:
        """Adapta a query para particionamento horizontal.

        Suporta dois modos:
            - Range (id_min/id_max): scan direcionado, sem full scan.
            - Módulo (total_particoes > 1): divisão uniforme por hash do ID.

        Insere o filtro antes do ORDER BY quando presente.
        """
        if self.id_min is not None and self.id_max is not None:
            filtro = (
                f"({coluna_id} BETWEEN {self.id_min} AND {self.id_max})"
            )
        elif self.total_particoes > 1:
            filtro = (
                f"(ABS({coluna_id}) % {self.total_particoes}"
                f" = {self.particao})"
            )
        else:
            return sql

        sql_lower = sql.lower()
        order_idx = sql_lower.rfind("order by")
        if order_idx >= 0:
            before = sql[:order_idx]
            after = sql[order_idx:]
            conj = "AND" if "where" in sql_lower[:order_idx] else "WHERE"
            return f"{before} {conj} {filtro} {after}"

        conj = "AND" if "where" in sql_lower else "WHERE"
        return f"{sql} {conj} {filtro}"

    def _get_union_partition_sql(self, union_sql: str, id_column: str) -> str:
        """Aplica filtro de partição em todas as partes de um UNION ALL."""
        if self.id_min is None or self.id_max is None:
            return union_sql
        partes = union_sql.split("UNION ALL")
        partes_filtradas = [
            self._get_partition_sql(p.strip(), id_column) for p in partes
        ]
        return "\nUNION ALL\n".join(partes_filtradas)


    def _criar_transform(
        self, config: PhaseConfig
    ) -> Callable[[tuple], tuple[str, str, Any]]:
        """Factory de função transform para uma fase do pipeline.

        Elimina overhead de isinstance e sorted em cada linha.

        Suporta dois caminhos:
            - ``dto_out`` fornecido: caminho legado via ``dto_out.to_dict()``.
            - ``dto_out`` ausente: caminho novo via ``dto_in.to_domain()``.
        """
        hash_fields = sorted(config.update_fields)
        pk_field = config.pk_field
        dto_in = config.dto_in
        model_class = config.model_class

        if isinstance(pk_field, list):
            def _extrair_pk(dto: Any) -> str:
                return "-".join(str(getattr(dto, f)) for f in pk_field)
        else:
            def _extrair_pk(dto: Any) -> str:
                return str(getattr(dto, pk_field))

        if config.dto_out is not None:
            dto_out = config.dto_out

            def transform(row: tuple) -> tuple[str, str, Any]:
                dto = dto_in(*row)
                obj = model_class(**dto_out.to_dict(dto))
                return _extrair_pk(dto), calcular_hash(obj, hash_fields), obj
        else:
            def transform(row: tuple) -> tuple[str, str, Any]:
                dto = dto_in(*row)
                obj = model_class(**dto.to_domain())
                return _extrair_pk(dto), calcular_hash(obj, hash_fields), obj

        return transform

    def _truncar_tabela(self, table_name: str) -> None:
        """Trunca a tabela de destino antes do full-sync.

        Usado apenas quando ``PhaseConfig.truncate_on_full_sync=True`` e
        ``primeiro_run=True``. O nome da tabela é definido em código
        (PhaseConfig), nunca vem de entrada externa.
        """
        with connections[self.db_alias].cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {table_name} CASCADE")  # noqa: S608
        logger.info(
            "[%s] Tabela %s truncada para full-sync.",
            self._dominio,
            table_name,
        )

    def _executar_fase(self, config: PhaseConfig) -> PipelineMetrics:
        """Executa fase com padrão Producer-Consumer."""
        if config.truncate_on_full_sync and self.primeiro_run:
            self._truncar_tabela(config.table_name)

        self._fase_suporta_bulk_insert = config.suporta_bulk_insert
        queue: Queue[list[tuple] | None] = Queue(
            maxsize=getattr(settings, "THREAD_POOL_MAX_WORKERS", 4)
        )
        metrics = PipelineMetrics()
        transform_func = self._criar_transform(config)
        erros: list[Exception] = []

        thread = Thread(
            target=self._producer, args=(config, queue, erros), daemon=True
        )
        thread.start()

        self._consumir_pedacos(config, queue, transform_func, metrics, erros)

        thread.join(timeout=settings.THREAD_POOL_CHUNK_TIMEOUT)
        if thread.is_alive():
            raise RuntimeError(f"[{config.nome}] Producer não encerrou.")
        if erros:
            raise erros[0]

        return metrics

    def _producer(self, config: PhaseConfig, queue: Queue, erros: list) -> None:
        """Busca pedaços da origem e alimenta a queue."""
        try:
            for chunk in self._iter_chunks(config.sql):
                queue.put(chunk)
            queue.put(None)
        except Exception as exc:
            erros.append(exc)
            queue.put(None)

    def _consumir_pedacos(
        self,
        config: PhaseConfig,
        queue: Queue,
        transform: Callable,
        metrics: PipelineMetrics,
        erros: list,
    ) -> None:
        """Transforma e sincroniza pedaços da queue."""
        timeout = settings.THREAD_POOL_CHUNK_TIMEOUT
        batch_num = 0
        processor = ThreadPoolProcessor(
            max_workers=settings.THREAD_POOL_MAX_WORKERS,
            timeout=timeout,
            prefixo_log=f"{self._dominio}/{config.nome}",
        )

        with processor:
            while True:
                try:
                    chunk = queue.get(timeout=timeout)
                except Empty:
                    raise RuntimeError(f"[{config.nome}] Producer Timeout.")

                if chunk is None:
                    break
                if erros:
                    raise erros[0]

                t0 = time.monotonic()
                lote = processor.processar(chunk, transform)
                escritos, ignorados = self._sync_batch(
                    processed_data=lote,
                    model_class=config.model_class,
                    table_name=config.table_name,
                    update_fields=list(config.update_fields),
                    unique_fields=list(config.unique_fields),
                    batch_num=batch_num,
                )

                metrics.total_lidos += len(chunk)
                metrics.total_escritos += escritos
                metrics.total_ignorados += ignorados
                if lote:
                    self.ultimo_token = str(lote[-1][0])

                elapsed = time.monotonic() - t0
                throughput = len(chunk) / elapsed if elapsed > 0 else 0
                logger.info(
                    "[%s] %s | LOTE: %d | Lidos: %s | Sync: %s | %.0f reg/s",
                    self._dominio,
                    config.table_name,
                    batch_num,
                    _fmt_num(metrics.total_lidos),
                    _fmt_num(escritos),
                    throughput,
                )
                batch_num += 1

    def _registrar_auditoria_fase(
        self, config: PhaseConfig, metrics: PipelineMetrics
    ) -> None:
        """Registra leitura da fase em ``etl_execucao_tabela_lida``."""
        if not self.auditor or not self.id_execucao:
            return
        if not config.source_table:
            return
        self.auditor.registrar_tabela_lida(
            id_execucao=self.id_execucao,
            tabela_origem=config.source_table,
            numero_pagina=self.ultima_fase_concluida,
            linhas_lidas=metrics.total_lidos,
        )

    def executar(self, fase_inicial: int = 1) -> dict[str, int]:
        """Executa o pipeline em fases, registrando auditoria de leitura."""
        resultados: dict[str, int] = {}
        logger.info(
            "[%s] Início Execução %s (Partição %d/%d) | full_sync=%s",
            self._dominio,
            self.id_execucao,
            self.particao,
            self.total_particoes,
            self.primeiro_run,
        )

        for i, config in enumerate(self._fases, 1):
            if i < fase_inicial:
                continue

            logger.info(
                "[%s] Início Fase %d: %s", self._dominio, i, config.nome
            )
            metrics = self._executar_fase(config)
            resultados[config.nome] = metrics.total_escritos
            self.ultima_fase_concluida = i
            self._registrar_auditoria_fase(config, metrics)

        return resultados

    # ------------------------------------------------------------------
    # Escrita no destino
    # ------------------------------------------------------------------

    def create_transformer(
        self,
        dto_in: Any,
        dto_out: Any,
        model_class: Any,
        pk_field: str | list[str],
    ) -> Callable[[tuple], tuple[Any, Any]]:
        """Factory de transformadores otimizados para DTOs.

        Args:
            dto_in: Classe DTO de entrada (In-Bound).
            dto_out: Classe DTO de saída (Out-Bound).
            model_class: Classe do modelo Django.
            pk_field: Nome(s) do(s) campo(s) que compõe(m) a PK.

        Returns:
            Função transformadora ``(row) -> (pk, model_instance)``.
        """

        def transform(row: tuple) -> tuple[Any, Any]:
            dto = dto_in(*row)
            if isinstance(pk_field, list):
                val_pk = "-".join(str(getattr(dto, f)) for f in pk_field)
            else:
                val_pk = getattr(dto, pk_field)
            return val_pk, model_class(**dto_out.to_dict(dto))

        return transform

    def sync_table(self, *args: Any, **kwargs: Any) -> None:
        """Método depreciado e removido. Use _execute_pipeline em seu lugar."""
        raise NotImplementedError(
            "sync_table foi removido. Use o novo padrão de pipeline explícito."
        )

    @retry_deadlock()
    def _sync_batch(
        self,
        processed_data: list[tuple[str, str, Any]],
        model_class: Any,
        table_name: str,
        update_fields: list[str] | None = None,
        unique_fields: list[str] | None = None,
        batch_num: int = 0,
    ) -> tuple[int, int]:
        """Helper para sincronizar um lote processado com o banco de destino."""
        return self._processar_batch(
            batch_num=batch_num,
            batch_data=processed_data,
            model_class=model_class,
            db_table=table_name,
            update_fields=update_fields,
            unique_fields=unique_fields,
        )

    def _processar_batch(
        self,
        batch_num: int,
        batch_data: list[tuple[str, str, Any]],
        model_class: Any,
        db_table: str,
        update_fields: list[str] | None = None,
        unique_fields: list[str] | None = None,
    ) -> tuple[int, int]:
        """Filtra, escreve no domínio e atualiza auditoria."""
        if not batch_data:
            return 0, 0

        dedup = {id_dest: (h, obj) for id_dest, h, obj in batch_data}
        dedup_data = sorted(
            [(k, v[0], v[1]) for k, v in dedup.items()], key=lambda x: x[0]
        )
        ignorados = len(batch_data) - len(dedup_data)

        objs, hashes = self._obter_dados_pendentes(
            dedup_data, db_table, batch_num
        )
        ignorados += len(dedup_data) - len(objs)

        if objs:
            self._persistir_batch(
                objs, hashes, model_class, db_table, batch_num,
                update_fields, unique_fields
            )

        return len(objs), ignorados

    def _obter_dados_pendentes(
        self, dedup_data: list, db_table: str, batch_num: int
    ) -> tuple[list, list]:
        """Identifica quais registros realmente mudaram."""
        if self.primeiro_run:
            return (
                [obj for _, _, obj in dedup_data],
                [(f"{db_table}:{r[0]}", r[1]) for r in dedup_data],
            )

        ids_audit = [f"{db_table}:{r[0]}" for r in dedup_data]
        existentes = self._buscar_hashes_por_copy(
            ids_audit, f"{db_table}_{batch_num}"
        )

        objs, hashes = [], []
        for id_dest, h, obj in dedup_data:
            id_audit = f"{db_table}:{id_dest}"
            if existentes.get(id_audit) != h:
                objs.append(obj)
                hashes.append((id_audit, h))

        return objs, hashes

    def _persistir_batch(
        self,
        objs: list,
        hashes: list,
        model_class: Any,
        db_table: str,
        batch_num: int,
        update_fields: list | None,
        unique_fields: list | None,
    ) -> None:
        """Executa a persistência no domínio e na auditoria."""
        usar_bulk = self.primeiro_run and getattr(
            self, "_fase_suporta_bulk_insert", False
        )
        with transaction.atomic(using=self.db_alias):
            if usar_bulk:
                model_class.objects.using(self.db_alias).bulk_create(objs)
            else:
                v_unique = unique_fields or getattr(
                    model_class, "unique_fields", ["id"]
                )
                v_update = update_fields or [
                    f.name
                    for f in model_class._meta.fields
                    if not f.primary_key and f.name != "id"
                ]
                model_class.objects.using(self.db_alias).bulk_create(
                    objs,
                    update_conflicts=True,
                    unique_fields=v_unique,
                    update_fields=v_update,
                )

        batch_id = f"{db_table}_{batch_num}"
        if self.auditor:
            self.auditor.upsert_bulk_hashes(hashes, batch_id)
        else:
            self.pg_engine.upsert_bulk(
                "etl_auditoria_linha", hashes, batch_id
            )

    def _buscar_hashes_por_copy(
        self,
        ids_audit: list[str],
        batch_id: str,
    ) -> dict[str, str]:
        """Busca hashes via COPY + JOIN, evitando IN (N ids).

        Clausulas IN com 100k IDs forçam o Postgres a alocar ~15 MB de
        shared memory por query. Com 4 partições × 4 consumers rodando
        em paralelo, isso esgota o limite do container. A substituição
        por COPY + temp table + INNER JOIN usa memória local (work_mem)
        e elimina o risco de "No space left on device".
        """
        if not ids_audit:
            return {}

        buffer = io.StringIO()
        try:
            for id_dest in ids_audit:
                buffer.write(f"{id_dest}\n")
            conteudo = buffer.getvalue()
        finally:
            buffer.close()

        safe_id = batch_id.replace("-", "_")
        temp_table = f"temp_lookup_{safe_id}"

        with (
            transaction.atomic(using="default"),
            connections["default"].cursor() as cursor,
        ):
            cursor.execute(
                f"CREATE TEMP TABLE {temp_table} "
                "(id_destino text) ON COMMIT DROP"
            )
            raw_cursor = cursor.cursor
            if hasattr(raw_cursor, "copy"):
                with raw_cursor.copy(
                    f"COPY {temp_table} (id_destino) FROM STDIN"
                ) as copy:
                    copy.write(conteudo)
            else:
                raw_cursor.copy_from(
                    io.StringIO(conteudo),
                    temp_table,
                    columns=("id_destino",),
                )
            cursor.execute(  # noqa: S608
                f"""
                SELECT al.id_destino, al.hash_controle
                FROM etl_auditoria_linha al
                INNER JOIN {temp_table} tl
                    ON al.id_destino = tl.id_destino
                """
            )
            return dict(cursor.fetchall())
