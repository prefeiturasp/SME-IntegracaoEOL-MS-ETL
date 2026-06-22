"""Motor de processamento e auditoria para serviços de ETL."""

from __future__ import annotations

import io
import logging
import os
import random
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from queue import Empty, Queue
from threading import Thread
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.core.libs.base_etl_fase import BaseEtlFase
from uuid import UUID

from django.conf import settings
from django.db import DatabaseError, connections, transaction
from psycopg import sql

from apps.core.libs.thread_processor import ThreadPoolProcessor, calcular_hash

logger = logging.getLogger(__name__)


_SENTINEL = object()


def _chunked(lst: list[str], n: int) -> Iterator[list[str]]:
    """Divide uma lista em fatias de tamanho n."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def _fmt_num(n: int) -> str:
    """Formata números para exibição amigável em logs."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    return f"{n / 1_000:.0f}k" if n >= 1_000 else str(n)


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Acessa atributo de dict ou objeto arbitrário."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _resolve_model(fase_meta: Any) -> Any:
    """Resolve classe do Model a partir de meta de fase."""
    if hasattr(fase_meta, "resolver_model"):
        return fase_meta.resolver_model()
    return _get_attr(fase_meta, "model_class")


def _resolver_batch_size() -> int:
    """Lê ETL_BULK_BATCH_SIZE do ambiente."""
    try:
        return int(os.getenv("ETL_BULK_BATCH_SIZE", "5000"))
    except ValueError:
        return 5000


def _resolver_chunk_size() -> int:
    """Lê CHUNKED_HASHES do ambiente com fallback para 10000."""
    try:
        return int(os.getenv("CHUNKED_HASHES", "10_000"))
    except ValueError:
        return 10_000


_BATCH_SIZE = _resolver_batch_size()
_CHUNK_SIZE = _resolver_chunk_size()


class StageTimer:
    """Temporizador simples para logs de estágio."""

    def __init__(self, name: str):
        self.name = name
        self.start = time.perf_counter()
        self.end = 0.0

    def stop(self) -> float:
        self.end = time.perf_counter() - self.start
        return self.end


def retry_deadlock(
    max_retries: int = 3, backoff: float = 0.5
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Executa retry em caso de deadlock ou timeout de banco."""

    def decorator(
        func: Callable[..., Any],
    ) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_err: Exception = RuntimeError("retry_deadlock")

            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except DatabaseError as exc:
                    msg = str(exc).lower()

                    if "deadlock" not in msg and "lock timeout" not in msg:
                        raise

                    last_err = exc

                    wait = backoff * (2**i) + random.uniform(0, 0.1)

                    logger.warning(
                        "Deadlock detectado. Tentativa %d/%d (espera %.2fs)",
                        i + 1,
                        max_retries,
                        wait,
                    )

                    time.sleep(wait)

            raise last_err

        return wrapper

    return decorator


@dataclass(frozen=True)
class PhaseConfig:
    """Configuração estável de uma fase do ETL."""

    nome: str
    sql: str
    table_name: str
    pk_field: str | list[str]
    update_fields: tuple[str, ...]
    unique_fields: tuple[str, ...]
    model_class: Any
    dto_in: Any
    source_table: str = ""
    truncate_on_full_sync: bool = False
    suporta_bulk_insert: bool = False
    modo_escrita: str = "upsert"

    def to_meta(
        self,
        dominio: str,
        db_alias: str,
        id_execucao: str | None,
        numero_fase: int,
        total_fases: int,
        options: dict[str, Any],
    ) -> BaseEtlFase:
        """Gera metadados de fase do Celery."""
        from apps.core.libs.base_etl_fase import BaseEtlFase

        m_path = (
            f"{self.model_class.__module__}.{self.model_class.__name__}"
            if self.model_class
            else "mock.Model"
        )
        d_path = (
            f"{self.dto_in.__module__}.{self.dto_in.__name__}"
            if self.dto_in
            else "mock.Dto"
        )

        return BaseEtlFase(
            nome=self.nome,
            sql=self.sql,
            table_name=self.table_name,
            source_table=self.source_table or self.table_name,
            model_path=m_path,
            dto_in_path=d_path,
            pk_field=self.pk_field,
            update_fields=list(self.update_fields),
            unique_fields=list(self.unique_fields),
            db_alias=db_alias,
            primeiro_run=options.get("primeiro_run", False),
            suporta_bulk_insert=self.suporta_bulk_insert,
            id_execucao=id_execucao,
            numero_fase=numero_fase,
            total_fases=total_fases,
            dominio=dominio,
            task_processamento_path=options.get("task_processamento_path", ""),
            task_callback_path=options.get("task_callback_path", ""),
        )


@dataclass
class PipelineMetrics:
    """Métricas de execução de uma fase."""

    total_lidos: int = 0
    total_escritos: int = 0
    total_ignorados: int = 0
    erros: list[str] = field(default_factory=list)


class PostgresUpsertEngine:
    """Motor de baixa escala para controle de auditoria e upserts."""

    @retry_deadlock()
    def upsert_bulk(
        self,
        table_name: str,
        rows: list[tuple[str, str]],
        batch_id: str = "batch",
    ) -> int:
        """Executa upsert massivo na tabela de auditoria."""
        if not rows:
            return 0
        rows.sort(key=lambda x: x[0])
        buf = io.StringIO()
        for r in rows:
            buf.write(f"{r[0]}\t{r[1]}\n")

        with (
            transaction.atomic(using="default"),
            connections["default"].cursor() as cursor,
        ):
            cursor.execute("SET LOCAL synchronous_commit = off")
            tmp = f"temp_audit_{str(batch_id).replace('-', '_')}"
            cursor.execute(
                sql.SQL(
                    "CREATE TEMP TABLE IF NOT EXISTS {} "
                    "(id_destino text, hash_controle text) ON COMMIT DROP"
                ).format(sql.Identifier(tmp))
            )

            raw = cursor.cursor
            with raw.copy(
                sql.SQL(
                    "COPY {} (id_destino, hash_controle) FROM STDIN"
                ).format(sql.Identifier(tmp))
            ) as cp:
                cp.write(buf.getvalue())

            cursor.execute(
                sql.SQL(
                    "INSERT INTO {table}"
                    " (id_destino, hash_controle, atualizado_em) "
                    "SELECT id_destino, hash_controle, NOW()"
                    " FROM {tmp} "
                    "ON CONFLICT (id_destino) DO UPDATE SET "
                    "hash_controle = EXCLUDED.hash_controle,"
                    " atualizado_em = NOW() "
                    "WHERE {table}.hash_controle <> EXCLUDED.hash_controle"
                ).format(
                    table=sql.Identifier(table_name), tmp=sql.Identifier(tmp)
                )
            )
            return int(cursor.rowcount or 0)

    def buscar_hashes(self, ids: list[str]) -> dict[str, str]:
        """Busca hashes em sub-lotes conforme _CHUNK_SIZE."""
        if not ids:
            return {}
        resultado: dict[str, str] = {}
        for sub_ids in _chunked(ids, _CHUNK_SIZE):
            resultado.update(self._buscar_sub_lote(sub_ids))
        return resultado

    def _buscar_sub_lote(self, ids: list[str]) -> dict[str, str]:
        """Busca hashes de um sub-lote."""
        with (
            transaction.atomic(using="default"),
            connections["default"].cursor() as cursor,
        ):
            cursor.execute(
                "SELECT id_destino, hash_controle "
                "FROM etl_auditoria_linha "
                "WHERE id_destino = ANY(%s)",
                [ids],
            )
            return dict(cursor.fetchall())

    def sincronizar_lote(
        self,
        processed: list[tuple[str, str, Any]],
        fase_meta: Any,
        batch_num: int = 0,
    ) -> tuple[int, int]:
        """Sincroniza um lote processado no banco de destino."""
        if not processed:
            return 0, 0

        total = len(processed)
        dedup = {pk: (h, obj) for pk, h, obj in processed}
        del processed

        tn = _get_attr(fase_meta, "table_name", "")
        db = _get_attr(fase_meta, "db_alias", "default")
        primeiro_run = _get_attr(fase_meta, "primeiro_run", False)
        modo = _get_attr(fase_meta, "modo_escrita", "upsert")

        if modo == "full_refresh":
            objs = [item[1] for item in dedup.values()]
            self._persistir(
                objs, _resolve_model(fase_meta), [], [], db, fast=True
            )
            return len(objs), total - len(objs)

        truncate_sync = _get_attr(fase_meta, "truncate_on_full_sync", False)
        if primeiro_run or truncate_sync:
            pendentes = [(pk, h, obj) for pk, (h, obj) in dedup.items()]
        else:
            full_ids = [f"{tn}:{pk}" for pk in dedup]
            existentes = self.buscar_hashes(full_ids)
            pendentes = [
                (pk, h, obj)
                for pk, (h, obj) in dedup.items()
                if existentes.get(f"{tn}:{pk}") != h
            ]

        if not pendentes:
            return 0, total

        objs = [p[2] for p in pendentes]
        hashes = [(f"{tn}:{p[0]}", p[1]) for p in pendentes]
        del pendentes

        uf = list(_get_attr(fase_meta, "update_fields") or [])
        unique = list(_get_attr(fase_meta, "unique_fields") or [])

        self._persistir(objs, _resolve_model(fase_meta), uf, unique, db)
        del objs

        escritos = len(hashes)
        self.upsert_bulk(
            "etl_auditoria_linha", hashes, batch_id=f"{tn}-{batch_num}"
        )
        del hashes

        return escritos, total - escritos

    def _persistir(
        self,
        objs: list,
        model_class: Any,
        update_fields: list[str],
        unique_fields: list[str],
        db_alias: str,
        fast: bool = False,
    ) -> None:
        """Salva objetos no banco de dados de destino."""
        if not objs:
            return
        mgr = model_class.objects.using(db_alias)
        with transaction.atomic(using=db_alias):
            with connections[db_alias].cursor() as cur:
                cur.execute("SET LOCAL synchronous_commit = off")
            if fast:
                mgr.bulk_create(objs, batch_size=_BATCH_SIZE)
            else:
                mgr.bulk_create(
                    objs,
                    update_conflicts=True,
                    unique_fields=unique_fields,
                    update_fields=update_fields,
                    batch_size=_BATCH_SIZE,
                )


class BaseEtlService:
    """Base para serviços de ETL do domínio."""

    _dominio: str = "ETL"

    def __init__(
        self,
        db_alias: str,
        id_execucao: UUID | None = None,
        repositorio_auditoria: Any | None = None,
        primeiro_run: bool = False,
        fases: list[str] | None = None,
    ) -> None:
        self.db_alias = db_alias
        self.id_execucao = id_execucao
        self.auditor = repositorio_auditoria
        self.primeiro_run = primeiro_run
        self.pg_engine = PostgresUpsertEngine()
        self._max_workers = getattr(settings, "THREAD_POOL_MAX_WORKERS", 4)
        self.ultima_fase_concluida = 0
        self._fases: list[PhaseConfig] = []
        self._fases_selecionadas: list[str] | None = fases
        self._thread_processor: ThreadPoolProcessor | None = None
        self.ultimo_token: str | None = None
        self._ultimo_audit_count = 0

    def get_meta(
        self,
        config: PhaseConfig,
        numero: int,
        total: int,
        id_execucao: Any = None,
    ) -> Any:
        """Cria metadados de fase para o Celery."""
        from apps.core.tasks import finalizar_fase, processar_chunk

        opts = {
            "primeiro_run": self.primeiro_run,
            "task_processamento_path": (
                f"{processar_chunk.__module__}.{processar_chunk.__name__}"
            ),
            "task_callback_path": (
                f"{finalizar_fase.__module__}.{finalizar_fase.__name__}"
            ),
        }
        return config.to_meta(
            dominio=self._dominio,
            db_alias=self.db_alias,
            id_execucao=str(id_execucao or self.id_execucao),
            numero_fase=numero,
            total_fases=total,
            options=opts,
        )

    def _iter_chunks(self, sql: str) -> Iterator[list[tuple]]:
        """Lê os dados brutos da origem (MSSQL) em chunks."""
        raise NotImplementedError()

    def sync_batch(
        self,
        processed_data: list[tuple[str, str, Any]],
        fase_meta: Any,
        batch_num: int = 0,
    ) -> tuple[int, int]:
        """Sincroniza um lote delegando para o motor de upsert."""
        return self.pg_engine.sincronizar_lote(
            processed_data, fase_meta, batch_num
        )

    def _processar_batch(
        self, config: PhaseConfig, chunk: list, **kwargs: Any
    ) -> tuple[int, int]:
        """Transforma e sincroniza um lote de dados."""
        transform = kwargs.get("transform") or (lambda x: x)
        tp = self._thread_processor
        lote_transformado = (
            tp.processar(chunk, transform)
            if tp is not None
            else [transform(r) for r in chunk]
        )
        meta = self._get_batch_meta(config)
        return self.sync_batch(
            lote_transformado, meta, batch_num=kwargs.get("batch_num", 0)
        )

    def _get_batch_meta(self, cfg: PhaseConfig | None, **kwargs: Any) -> dict:
        """Monta dicionário de metadados da fase."""
        return {
            "primeiro_run": self.primeiro_run,
            "db_alias": self.db_alias,
            "table_name": (cfg.table_name if cfg else None)
            or kwargs.get("table_name"),
            "update_fields": list(
                (cfg.update_fields if cfg else None)
                or kwargs.get("update_fields", [])
            ),
            "unique_fields": list(
                (cfg.unique_fields if cfg else None)
                or kwargs.get("unique_fields", ["id"])
            ),
            "model_class": (cfg.model_class if cfg else None)
            or kwargs.get("model_class"),
            "modo_escrita": (cfg.modo_escrita if cfg else None)
            or kwargs.get("modo_escrita", "upsert"),
            "truncate_on_full_sync": (
                cfg.truncate_on_full_sync if cfg else False
            )
            or kwargs.get("truncate_on_full_sync", False),
        }

    def _executar_fase(
        self, config: PhaseConfig, numero_fase: int = 0
    ) -> PipelineMetrics:
        queue: Queue = Queue(maxsize=self._max_workers)
        metrics: PipelineMetrics = PipelineMetrics()
        erros: list[Exception] = []

        if (
            config.modo_escrita == "full_refresh"
            and config.truncate_on_full_sync
        ):
            self._truncar_tabela(config.table_name)

        self._ultimo_audit_count = 0
        thread = self._iniciar_producer(config, queue, erros)

        trans = self._criar_transform(config)
        bn, start = 0, time.perf_counter()

        erro_execucao: BaseException | None = None
        try:
            with ThreadPoolProcessor(
                max_workers=self._max_workers, prefixo_log=self._dominio
            ) as tp:
                self._thread_processor = tp
                try:
                    while True:
                        chunk = self._get_next_chunk(queue, thread, erros)
                        if chunk is None:
                            break

                        esc, ign = self._processar_batch(
                            batch_num=bn,
                            chunk=chunk,
                            transform=trans,
                            config=config,
                        )
                        self._atualizar_metricas(metrics, len(chunk), esc, ign)
                        bn += 1
                        self._log_progresso(bn, metrics, start, config)
                        queue.task_done()
                finally:
                    self._thread_processor = None
        except BaseException as exc:
            erro_execucao = exc
            raise
        finally:
            try:
                self._finalizar_threads(thread, erros)
            except Exception:
                if erro_execucao is None:
                    raise
                logger.exception(
                    "[%s] Erro adicional ao finalizar Producer",
                    self._dominio,
                )

        self._registrar_auditoria_fase(
            config,
            metrics,
            numero_fase=numero_fase,
            total_fases=len(self._fases),
            ultimo_lote=bn,
        )
        return metrics

    def _iniciar_producer(
        self, config: PhaseConfig, queue: Queue, erros: list[Exception]
    ) -> Thread:
        def producer() -> None:
            try:
                for chunk in self._iter_chunks(config.sql):
                    queue.put(chunk)
                queue.put(None)
            except Exception as e:
                erros.append(e)
                queue.put(None)

        thread = Thread(target=producer, daemon=True)
        thread.start()
        return thread

    def _get_next_chunk(
        self,
        queue: Queue,
        producer_thread: Thread | None = None,
        erros: list[Exception] | None = None,
    ) -> list[Any] | None:
        timeout = getattr(settings, "THREAD_POOL_CHUNK_TIMEOUT", 30) or 0
        if timeout <= 0:
            chunk_sem_timeout: list | None = queue.get()
            return chunk_sem_timeout

        max_espera = getattr(settings, "PRODUCER_MAX_WAIT_SECONDS", 600)
        tempo_espera = 0.0
        while True:
            try:
                chunk: list | None = queue.get(timeout=timeout)
                return chunk
            except Empty as err:
                self._validar_estado_producer(producer_thread, erros, err)
                tempo_espera += timeout
                self._log_espera_producer(tempo_espera)
                self._validar_timeout_producer(max_espera, tempo_espera, err)

    def _validar_estado_producer(
        self,
        producer_thread: Thread | None,
        erros: list[Exception] | None,
        causa: Empty,
    ) -> None:
        """Propaga erro ou encerramento inesperado do Producer."""
        if erros:
            raise erros[0] from causa
        if producer_thread is not None and not producer_thread.is_alive():
            raise RuntimeError(
                "Producer thread finished without signaling completion"
            ) from causa

    def _log_espera_producer(self, tempo_espera: float) -> None:
        """Registra espera por novo chunk do Producer."""
        logger.warning(
            "[%s] Aguardando Producer ha %.0fs sem novo chunk",
            self._dominio,
            tempo_espera,
        )

    def _validar_timeout_producer(
        self,
        max_espera: float,
        tempo_espera: float,
        causa: Empty,
    ) -> None:
        """Aborta a fase quando o Producer fica tempo demais sem resposta."""
        if max_espera <= 0 or tempo_espera < max_espera:
            return
        raise TimeoutError(
            f"[{self._dominio}] Producer não produziu chunk"
            f" após {tempo_espera:.0f}s — abortando fase"
        ) from causa

    def _atualizar_metricas(
        self, metrics: PipelineMetrics, lidos: int, esc: int, ign: int
    ) -> None:
        metrics.total_lidos += lidos
        metrics.total_escritos += esc
        metrics.total_ignorados += ign
        self.ultimo_token = str(metrics.total_lidos)

    def _log_progresso(
        self,
        bn: int,
        metrics: PipelineMetrics,
        start: float,
        config: PhaseConfig,
    ) -> None:
        if bn % 10 == 0 or bn == 1:
            duracao = time.perf_counter() - start
            rate = int(metrics.total_lidos / (duracao or 1))
            logger.info(
                "[%s] throughput: %d itens em %.2fs (%s reg/s)",
                self._dominio,
                metrics.total_lidos,
                duracao,
                _fmt_num(rate),
            )

        intervalo = getattr(settings, "EOL_CHUNK_SIZE", 50_000)
        if metrics.total_lidos - self._ultimo_audit_count > intervalo:
            self._registrar_progresso_parcial(config)
            self._ultimo_audit_count = metrics.total_lidos

    def _registrar_progresso_parcial(self, config: PhaseConfig) -> None:
        """Atualiza checkpoint intermediário para retomada em caso de falha.

        Não grava em EtlExecucaoTabelaLida — o registro definitivo
        é feito exclusivamente por _registrar_auditoria_fase ao final.
        """
        if not (self.auditor and self.id_execucao):
            return

        token = self.ultimo_token or "0"
        self.auditor.atualizar_checkpoint_dominio(
            dominio=self._dominio.lower(),
            ultimo_id_execucao=self.id_execucao,
            ultima_pagina=self.ultima_fase_concluida + 1,
            token_parada=token,
            indice_sincronizacao=f"{config.nome}:offset:{token}",
            ultima_situacao="em_execucao",
            sucesso=False,
        )

    def _finalizar_threads(self, thread: Thread, erros: list) -> None:
        thread.join(timeout=30)
        if thread.is_alive():
            logger.warning(
                "[%s] Producer thread não finalizou após 30s"
                " (possivelmente bloqueada em I/O de rede)",
                self._dominio,
            )
        if erros:
            raise erros[0]

    def _registrar_auditoria_fase(
        self,
        config: PhaseConfig,
        metrics: PipelineMetrics,
        numero_fase: int = 0,
        total_fases: int = 0,
        ultimo_lote: int = 0,
    ) -> None:
        """Registra métricas da fase e atualiza o checkpoint de progresso."""
        if not (self.auditor and self.id_execucao):
            return

        if config.source_table:
            self.auditor.registrar_tabela_lida(
                id_execucao=self.id_execucao,
                tabela_origem=config.source_table,
                numero_pagina=ultimo_lote,
                linhas_lidas=metrics.total_lidos,
            )
        self.auditor.registrar_tabela_escrita(
            id_execucao=self.id_execucao,
            tabela_destino=config.table_name,
            linhas_escritas=metrics.total_escritos,
            modo_escrita=config.modo_escrita,
        )

        is_ultima = numero_fase > 0 and numero_fase == total_fases
        token = self.ultimo_token or "0"

        self.auditor.atualizar_checkpoint_dominio(
            dominio=self._dominio.lower(),
            ultimo_id_execucao=self.id_execucao,
            ultima_pagina=numero_fase or self.ultima_fase_concluida,
            token_parada=token,
            indice_sincronizacao=f"{config.nome}:offset:{token}",
            ultima_situacao="concluido" if is_ultima else "em_execucao",
            sucesso=is_ultima,
        )

    def _truncar_tabela(self, tn: str) -> None:
        """Limpa a tabela de destino antes do Full Sync."""
        with connections[self.db_alias].cursor() as cur:
            cur.execute(
                sql.SQL("TRUNCATE TABLE {} CASCADE").format(sql.Identifier(tn))
            )

    def _criar_transform(self, config: PhaseConfig) -> Callable:
        """Cria função de transformação de linha MSSQL para objeto Model."""
        hf, pkf = sorted(config.update_fields), config.pk_field
        din, mc = config.dto_in, config.model_class

        def _pk(d: Any) -> str:
            if isinstance(pkf, list):
                return "-".join(str(getattr(d, f)) for f in pkf)
            return str(getattr(d, pkf))

        def transform(row: tuple) -> tuple[str, str, Any]:
            d = din(*row)
            obj = mc(**d.to_domain())
            return _pk(d), calcular_hash(obj, hf), obj

        return transform

    def executar(self, fase_inicial: int = 1) -> dict[str, int]:
        """Executa todas as fases do serviço sequencialmente."""
        res = {}
        total = len(self._fases)
        for i, config in enumerate(self._fases, 1):
            if i < fase_inicial:
                continue
            if (
                self._fases_selecionadas is not None
                and config.nome not in self._fases_selecionadas
            ):
                logger.info(
                    "Fase %d/%d ignorada (não selecionada): %s",
                    i,
                    total,
                    config.nome,
                )
                continue
            logger.info("Executando fase %d/%d: %s", i, total, config.nome)
            m = self._executar_fase(config, numero_fase=i)
            res[config.nome] = m.total_escritos
            self.ultima_fase_concluida = i
        return res

    def _buscar_hashes_por_copy(self, ids: list[str]) -> dict[str, str]:
        """Busca hashes via PostgresUpsertEngine."""
        return self.pg_engine.buscar_hashes(ids)
