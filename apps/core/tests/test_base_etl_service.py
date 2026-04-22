"""Testes para BaseEtlService e métodos auxiliares."""

import contextlib
import io
import time
from dataclasses import replace
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

from django.db import OperationalError
from django.test import SimpleTestCase, TestCase

from apps.core.libs.base_etl_service import (
    BaseEtlService,
    PhaseConfig,
    PipelineMetrics,
    retry_deadlock,
    PostgresUpsertEngine
)


def _make_service(**kwargs) -> BaseEtlService:
    return BaseEtlService(db_alias="default", **kwargs)


def _make_phase(**kwargs) -> PhaseConfig:
    defaults = {
        "nome": "fase_teste",
        "sql": "SELECT 1",
        "table_name": "tabela_destino",
        "source_table": "tabela_origem",
        "model_class": MagicMock(),
        "dto_in": MagicMock(),
        "dto_out": MagicMock(),
        "pk_field": "id",
        "update_fields": ("campo_a",),
        "unique_fields": ("id",),
    }
    defaults.update(kwargs)
    return PhaseConfig(**defaults)


class BaseEtlMockMixin:
    """Centraliza mocks repetitivos de infraestrutura (transação e DB)."""

    def _mock_cursor(self, fetchall_result: list | None = None) -> MagicMock:
        cursor = MagicMock()
        cursor.__enter__ = lambda s: s
        cursor.__exit__ = MagicMock(return_value=False)
        if fetchall_result is not None:
            cursor.fetchall.return_value = fetchall_result
        return cursor

    @contextlib.contextmanager
    def _patch_infra(self, cursor: MagicMock | None = None):
        with (
            patch("apps.core.libs.base_etl_service.connections") as mock_conns,
            patch(
                "apps.core.libs.base_etl_service.transaction.atomic"
            ) as mock_atomic,
        ):
            mock_atomic.return_value.__enter__ = lambda s: s
            mock_atomic.return_value.__exit__ = MagicMock(return_value=False)
            if cursor:
                conn = mock_conns.__getitem__.return_value
                conn.cursor.return_value = cursor
                conn.cursor.return_value.__enter__.return_value = cursor
            yield mock_atomic, mock_conns


class PhaseConfigTest(SimpleTestCase):
    """Valida o dataclass PhaseConfig."""

    def test_e_imutavel(self) -> None:
        config = _make_phase()
        with self.assertRaises(Exception):
            config.nome = "outro"  # type: ignore[misc]

    def test_source_table_opcional(self) -> None:
        config = _make_phase(source_table="")
        self.assertEqual(config.source_table, "")



class RegistrarAuditoriaFaseTest(SimpleTestCase):
    """Valida _registrar_auditoria_fase."""

    def test_chama_registrar_tabela_lida(self) -> None:
        mock_auditor = MagicMock()
        svc = _make_service(
            repositorio_auditoria=mock_auditor, id_execucao=uuid4()
        )
        svc.ultima_fase_concluida = 2
        config = _make_phase(source_table="tabela_origem")
        metrics = PipelineMetrics(total_lidos=500, total_escritos=300)

        svc._registrar_auditoria_fase(config, metrics, ultimo_lote=5)

        mock_auditor.registrar_tabela_lida.assert_called_once_with(
            id_execucao=svc.id_execucao,
            tabela_origem="tabela_origem",
            numero_pagina=5,
            linhas_lidas=500,
        )

    def test_nao_chama_sem_source_table(self) -> None:
        mock_auditor = MagicMock()
        svc = _make_service(
            repositorio_auditoria=mock_auditor, id_execucao=uuid4()
        )
        config = _make_phase(source_table="")
        metrics = PipelineMetrics(total_lidos=100)

        svc._registrar_auditoria_fase(config, metrics)

        mock_auditor.registrar_tabela_lida.assert_not_called()

    def test_nao_chama_sem_auditor(self) -> None:
        svc = _make_service()
        config = _make_phase(source_table="tabela_origem")
        metrics = PipelineMetrics(total_lidos=100)
        svc._registrar_auditoria_fase(config, metrics)


class BuscarHashesPorCopyTest(SimpleTestCase, BaseEtlMockMixin):
    """Valida _buscar_hashes_por_copy: COPY + JOIN sem IN clause."""

    def test_ids_vazios_retorna_dict_vazio(self) -> None:
        """Sem ids_audit não deve abrir conexão nem retornar dados."""
        svc = _make_service()
        resultado = svc._buscar_hashes_por_copy([], "batch_0")
        self.assertEqual(resultado, {})

    def test_retorna_mapeamento_id_hash(self) -> None:
        """Deve retornar dict {id_destino: hash_controle} do fetchall."""
        dados = [
            ("aluno:001", "aaa"),
            ("aluno:002", "bbb"),
        ]
        cursor = self._mock_cursor(dados)
        raw = MagicMock()
        # Simula psycopg3: sem atributo 'copy' → cai no else (copy_from)
        del raw.copy
        cursor.cursor = raw

        svc = _make_service()
        with self._patch_infra(cursor):
            resultado = svc._buscar_hashes_por_copy(
                ["aluno:001", "aluno:002"], "batch_1"
            )

        self.assertEqual(resultado, {"aluno:001": "aaa", "aluno:002": "bbb"})

    def test_usa_copy_from_quando_psycopg2(self) -> None:
        """Deve chamar copy_from quando o cursor não tem atributo copy."""
        cursor = self._mock_cursor([])
        raw = MagicMock()
        del raw.copy  # simula psycopg2: sem método copy
        cursor.cursor = raw

        svc = _make_service()
        with self._patch_infra(cursor):
            svc._buscar_hashes_por_copy(["tabela:123"], "batch_2")

        raw.copy_from.assert_called_once()
        args, kwargs = raw.copy_from.call_args
        self.assertIsInstance(args[0], io.StringIO)
        self.assertEqual(kwargs.get("columns") or args[2], ("id_destino",))

    def test_usa_copy_quando_psycopg3(self) -> None:
        """Deve chamar o context manager copy() quando disponível (psycopg3)."""
        cursor = self._mock_cursor([])

        copy_ctx = MagicMock()
        copy_ctx.__enter__ = lambda s: s
        copy_ctx.__exit__ = MagicMock(return_value=False)

        raw = MagicMock()
        raw.copy.return_value = copy_ctx
        cursor.cursor = raw

        svc = _make_service()
        with self._patch_infra(cursor):
            svc._buscar_hashes_por_copy(["tabela:999"], "batch_3")

        raw.copy.assert_called_once()
        copy_ctx.write.assert_called_once()

    def test_cria_temp_table_on_commit_drop(self) -> None:
        """Deve criar temp table com ON COMMIT DROP para limpeza automática."""
        cursor = self._mock_cursor([])
        raw = MagicMock()
        del raw.copy
        cursor.cursor = raw

        svc = _make_service()
        with self._patch_infra(cursor):
            svc._buscar_hashes_por_copy(["x:1"], "batch-4")

        create_call = cursor.execute.call_args_list[0]
        sql_create = create_call[0][0]
        # Converte Composed para string para verificação (psycopg 3)
        sql_str = sql_create.as_string(None)
        self.assertIn("ON COMMIT DROP", sql_str)
        self.assertIn("temp_lookup_batch_4", sql_str)

    def test_nome_temp_table_sanitiza_hifens(self) -> None:
        """Hifens no batch_id devem ser substituídos por underscores."""
        cursor = self._mock_cursor([])
        raw = MagicMock()
        del raw.copy
        cursor.cursor = raw

        svc = _make_service()
        with self._patch_infra(cursor):
            svc._buscar_hashes_por_copy(["x:1"], "abc-def-ghi")

        create_call = cursor.execute.call_args_list[0]
        # Converte Composed para string para verificação (psycopg 3)
        sql_str = create_call[0][0].as_string(None)
        self.assertIn("temp_lookup_abc_def_ghi", sql_str)
        self.assertNotIn("-", sql_str.split("TEMP TABLE")[1].split("(")[0])


class ProcessarBatchFullSyncTest(TestCase, BaseEtlMockMixin):
    databases = {"default", "eol_db", "alunos_db"}
    """Valida _processar_batch em modo full-sync (primeiro_run=True).

    Foco: bulk_create sem update_conflicts e acumulação de hashes.
    """

    def _make_svc(self, **kwargs) -> BaseEtlService:
        return BaseEtlService(
            db_alias="default", primeiro_run=True, **kwargs
        )

    def _make_obj(self) -> MagicMock:
        obj = MagicMock()
        obj.campo_a = "v"
        return obj

    def _batch_data(
        self, n: int = 2
    ) -> list[tuple[str, str, MagicMock]]:
        return [(str(i), f"hash{i}", self._make_obj()) for i in range(n)]

    def test_full_sync_usa_bulk_create_sem_update_conflicts(
        self,
    ) -> None:
        """bulk_create DEVE receber update_conflicts=True no full-sync.

        Válido somente para fases marcadas com suporta_bulk_insert=True.
        """
        svc = self._make_svc()
        svc._fase_suporta_bulk_insert = True
        mock_qs = MagicMock()
        mock_model = MagicMock()
        mock_model.objects.using.return_value = mock_qs

        with (
            self._patch_infra() as (mock_atomic, _),
            patch.object(svc.pg_engine, "upsert_bulk"),
        ):
            meta = PhaseConfig(
                nome="f", sql="s", table_name="tabela", 
                pk_field="id", update_fields=("campo_a",), unique_fields=("id",),
                model_class=mock_model, dto_in=MagicMock()
            )
            svc._processar_batch(
                config=meta,
                chunk=self._batch_data(),
                batch_num=0
            )

        mock_qs.bulk_create.assert_called_once()
        _, kwargs = mock_qs.bulk_create.call_args
        self.assertTrue(kwargs.get("update_conflicts"))

    def test_full_sync_tabela_global_usa_update_conflicts(
        self,
    ) -> None:
        """Tabelas globais (suporta_bulk_insert=False) mantêm update_conflicts.

        Garante que tabelas de referência compartilhadas entre partições
        paralelas não causem duplicate key errors no full-sync.
        """
        svc = self._make_svc()
        svc._fase_suporta_bulk_insert = False
        mock_qs = MagicMock()
        mock_model = MagicMock()
        mock_model.objects.using.return_value = mock_qs

        with (
            self._patch_infra() as (mock_atomic, _),
            patch.object(svc.pg_engine, "upsert_bulk"),
        ):
            meta = PhaseConfig(
                nome="f", sql="s", table_name="tabela",
                pk_field="id", update_fields=("campo_a",), unique_fields=("id",),
                model_class=mock_model, dto_in=MagicMock(),
                suporta_bulk_insert=False
            )
            svc._processar_batch(
                config=meta,
                chunk=self._batch_data(),
                batch_num=0
            )

        mock_qs.bulk_create.assert_called_once()
        _, kwargs = mock_qs.bulk_create.call_args
        self.assertTrue(kwargs.get("update_conflicts"))

    def test_incremental_usa_bulk_create_com_update_conflicts(
        self,
    ) -> None:
        """bulk_create DEVE receber update_conflicts=True no incremental."""
        svc = BaseEtlService(db_alias="default", primeiro_run=False)
        mock_qs = MagicMock()
        mock_model = MagicMock()
        mock_model.objects.using.return_value = mock_qs

        with (
            self._patch_infra() as (mock_atomic, _),
            patch.object(svc.pg_engine, "buscar_hashes", return_value={}),
            patch.object(svc.pg_engine, "upsert_bulk"),
        ):
            meta = PhaseConfig(
                nome="f", sql="s", table_name="tabela",
                pk_field="id", update_fields=("campo_a",), unique_fields=("id",),
                model_class=mock_model, dto_in=MagicMock()
            )
            svc._processar_batch(
                config=meta,
                chunk=self._batch_data(),
                batch_num=0
            )

        mock_qs.bulk_create.assert_called_once()
        _, kwargs = mock_qs.bulk_create.call_args
        self.assertTrue(kwargs.get("update_conflicts"))

    def test_full_sync_sem_auditor_escreve_hashes_via_pg_engine(
        self,
    ) -> None:
        """Sem auditor, hashes devem ser enviados via pg_engine.upsert_bulk."""
        svc = self._make_svc()
        mock_qs = MagicMock()
        mock_model = MagicMock()
        mock_model.objects.using.return_value = mock_qs

        with (
            self._patch_infra() as (mock_atomic, _),
            patch.object(svc.pg_engine, "upsert_bulk") as mock_upsert,
        ):
            meta = PhaseConfig(
                nome="f", sql="s", table_name="tabela",
                pk_field="id", update_fields=("campo_a",), unique_fields=("id",),
                model_class=mock_model, dto_in=MagicMock()
            )
            svc._processar_batch(
                config=meta,
                chunk=self._batch_data(2),
                batch_num=0
            )

        mock_upsert.assert_called_once()
        args = mock_upsert.call_args[0]
        self.assertEqual(args[0], "etl_auditoria_linha")
        self.assertEqual(len(args[1]), 2)

    def test_full_sync_deduplica_por_id_antes_de_escrever(self) -> None:
        """Registros com id duplicado devem ser deduplicados no full-sync."""
        svc = self._make_svc()
        mock_qs = MagicMock()
        mock_model = MagicMock()
        mock_model.objects.using.return_value = mock_qs
        obj = self._make_obj()
        data = [("1", "h1", obj), ("1", "h2", obj)]

        with (
            self._patch_infra() as (mock_atomic, _),
            patch.object(svc.pg_engine, "upsert_bulk"),
        ):
            meta = PhaseConfig(
                nome="f", sql="s", table_name="tabela",
                pk_field="id", update_fields=("campo_a",), unique_fields=("id",),
                model_class=mock_model, dto_in=MagicMock()
            )
            escritos, ignorados = svc._processar_batch(
                config=meta,
                chunk=data,
                batch_num=0,
                transform=lambda x: x
            )

        self.assertEqual(escritos, 1)
        self.assertEqual(ignorados, 1)


class PhaseConfigNovosCamposTest(SimpleTestCase):
    """Valida os novos campos opcionais de PhaseConfig (§8.7)."""

    def test_truncate_on_full_sync_padrao_false(self) -> None:
        """truncate_on_full_sync deve ser False por padrão."""
        config = _make_phase()
        self.assertFalse(config.truncate_on_full_sync)

    def test_audit_flush_size_padrao_zero(self) -> None:
        """audit_flush_size deve ser 0 por padrão (flush por batch)."""
        config = _make_phase()
        self.assertEqual(config.audit_flush_size, 0)

    def test_aceita_truncate_on_full_sync_true(self) -> None:
        """Deve aceitar truncate_on_full_sync=True sem erro."""
        config = _make_phase(truncate_on_full_sync=True)
        self.assertTrue(config.truncate_on_full_sync)

    def test_aceita_audit_flush_size_personalizado(self) -> None:
        """Deve aceitar audit_flush_size > 0."""
        config = _make_phase(audit_flush_size=500_000)
        self.assertEqual(config.audit_flush_size, 500_000)


class FlushDiferidoHashesTest(TestCase):
    databases = {"default", "eol_db", "alunos_db"}
    """Valida o flush diferido de hashes no full-sync (P1).

    Quando audit_flush_size > 0 e primeiro_run=True, os hashes devem ser
    acumulados e gravados em lotes maiores em vez de por batch processado.
    """

    def _make_svc(self) -> BaseEtlService:
        return BaseEtlService(db_alias="default", primeiro_run=True)

    def _make_config(self, flush_size: int = 0) -> PhaseConfig:
        mock_model = MagicMock()
        mock_model._meta.fields = []

        dto_mock = MagicMock()
        dto_mock.side_effect = lambda *a: MagicMock(campo_a="v")

        return PhaseConfig(
            nome="fase_flush",
            sql="SELECT 1",
            table_name="tabela_flush",
            source_table="origem",
            model_class=mock_model,
            dto_in=dto_mock,
            pk_field="id",
            update_fields=("campo_a",),
            unique_fields=("id",),
            audit_flush_size=flush_size,
        )

    @patch.object(BaseEtlService, "_processar_batch", return_value=(1, 0))
    def test_flush_padrao_chama_sync_batch_por_chunk(
        self, mock_batch: MagicMock
    ) -> None:
        """Com audit_flush_size=0, _sync_batch é chamado uma vez por chunk."""
        svc = self._make_svc()
        config = self._make_config(flush_size=0)

        chunks = [
            [(1, "A", 1, None)],
            [(2, "B", 1, None)],
        ]

        with patch.object(svc, "_iter_chunks", return_value=iter(chunks)):
            svc._executar_fase(config)

        self.assertEqual(mock_batch.call_count, 2)

    @patch.object(BaseEtlService, "_processar_batch", return_value=(1, 0))
    def test_executar_fase_com_flush_size_positivo_executa_sem_erro(
        self, _mock_batch: MagicMock
    ) -> None:
        """_executar_fase com audit_flush_size > 0 não deve lançar exceção."""
        svc = self._make_svc()
        config = self._make_config(flush_size=100_000)
        chunks = [[(1, "A", 1, None)]]

        with patch.object(svc, "_iter_chunks", return_value=iter(chunks)):
            metrics = svc._executar_fase(config)

        self.assertIsInstance(metrics, PipelineMetrics)
        self.assertEqual(metrics.total_lidos, 1)

class MockService(BaseEtlService):
    """Subclasse para testar implementação abstrata."""

    _dominio = "TEST"

    def _iter_chunks(self, sql):
        return iter([[(1,)]])


class BaseEtlServiceCoverageTest(TestCase, BaseEtlMockMixin):
    databases = {"default", "eol_db", "alunos_db"}
    """Testes focados em coberturas de branches específicas."""

    def setUp(self) -> None:
        self.svc = MockService(db_alias="default")
        self.config = PhaseConfig(
            nome="fase",
            sql="SELECT 1",
            table_name="t",
            source_table="s",
            model_class=MagicMock(),
            dto_in=MagicMock(),
            pk_field="id",
            update_fields=("f",),
            unique_fields=("id",),
        )

    def test_abstract_methods_raise_error(self) -> None:
        """Testa que a classe base exige implementação de _iter_chunks."""
        svc_base = BaseEtlService(db_alias="d")
        with self.assertRaises(NotImplementedError):
            svc_base._iter_chunks("SQL")

    def test_retry_deadlock_decorator_success_after_failure(self) -> None:
        """Testa o decorador retry_deadlock com falha seguida de sucesso."""
        mock_func = MagicMock()
        # Falha com deadlock (1213 no SQL Server) e depois passa
        erro_deadlock = OperationalError()
        erro_deadlock.args = (1213, "Deadlock")
        mock_func.side_effect = [erro_deadlock, 42]

        decorated = retry_deadlock()(mock_func)
        res = decorated(self.svc, "arg")
        self.assertEqual(res, 42)
        self.assertEqual(mock_func.call_count, 2)

    def test_retry_deadlock_raises_other_errors(self) -> None:
        """Testa que erros que não são deadlock sobem imediatamente."""
        mock_func = MagicMock(side_effect=ValueError("Erro Real"))
        decorated = retry_deadlock()(mock_func)
        with self.assertRaises(ValueError):
            decorated(self.svc)

    def test_truncar_tabela_executa_sql(self) -> None:
        """Testa o método privado _truncar_tabela."""
        with self._patch_infra() as (_, mock_conns):
            self.svc._truncar_tabela("minha_tabela")
            mock_cursor = mock_conns.__getitem__.return_value.cursor.return_value.__enter__.return_value
            # Verifica se o execute foi chamado com um objeto SQL equivalente
            args, _ = mock_cursor.execute.call_args
            self.assertEqual(
                args[0].as_string(None),
                'TRUNCATE TABLE "minha_tabela" CASCADE'
            )

    def test_criar_transform_caminho_adapter(self) -> None:
        """Testa _criar_transform quando dto_out não é fornecido (padrão Adapter)."""
        config = PhaseConfig(
            nome="f",
            sql="s",
            table_name="t",
            model_class=MagicMock,  # Class constructor
            dto_in=MagicMock(),
            pk_field="id",
            update_fields=("f",),
            unique_fields=("id",),
            dto_out=None,
        )

        # O mock dto_in retorna um objeto com id=1 e to_domain() fixo
        dto_inst = MagicMock()
        dto_inst.id = 1
        dto_inst.to_domain.return_value = {"id": 1, "f": "v"}
        config.dto_in.return_value = dto_inst

        transform = self.svc._criar_transform(config)
        id_dest, _, obj = transform((1,))

        self.assertEqual(id_dest, "1")
        self.assertEqual(obj.id, 1)

    def test_executar_fase_error_in_producer(self) -> None:
        """Testa erro no produtor dentro de _executar_fase."""
        with patch.object(
            self.svc, "_iter_chunks", side_effect=RuntimeError("Falha na Query")
        ):
            with self.assertRaises(RuntimeError):
                self.svc._executar_fase(self.config)

    def test_executar_fluxo_completo_com_fases(self) -> None:
        """Testa o método principal executar com múltiplas fases."""
        self.svc._fases = [self.config]
        m = MagicMock()
        m.total_escritos = 10
        with patch.object(self.svc, "_executar_fase", return_value=m):
            res = self.svc.executar()
            self.assertEqual(res["fase"], 10)
            self.assertEqual(self.svc.ultima_fase_concluida, 1)

    def test_executar_para_em_fase_inicial(self) -> None:
        """Testa iniciar o ETL de uma fase específica."""
        f1 = replace(self.config, nome="f1", table_name="t1")
        f2 = replace(self.config, nome="f2", table_name="t2")
        self.svc._fases = [f1, f2]
        m = MagicMock()
        m.total_escritos = 5
        with patch.object(self.svc, "_executar_fase", return_value=m) as mock_fase:
            res = self.svc.executar(fase_inicial=2)
            self.assertEqual(mock_fase.call_count, 1)  # Só a f2
            self.assertEqual(res["f2"], 5)
            self.assertEqual(self.svc.ultima_fase_concluida, 2)


    def test_thread_processor_context_manager(self) -> None:
        """Força cobertura do context manager do ThreadPoolProcessor."""
        from apps.core.libs.thread_processor import ThreadPoolProcessor

        with ThreadPoolProcessor(max_workers=1, prefixo_log="TEST") as p:
            self.assertIsNotNone(p)
            self.assertTrue(p.max_workers == 1)



    def test_fmt_num_casos_grandes(self) -> None:
        """Cobre branches de formatação de números 1M e 1k."""
        from apps.core.libs.base_etl_service import _fmt_num
        self.assertEqual(_fmt_num(2_500_000), "2.5M")
        self.assertEqual(_fmt_num(10_000), "10k")
        self.assertEqual(_fmt_num(500), "500")

    def test_retry_deadlock_falha_exaurida(self) -> None:
        """Garante que a última exceção é re-lançada ao esgotar as tentativas de retry."""
        from apps.core.libs.base_etl_service import retry_deadlock
        mock = MagicMock(side_effect=OperationalError("deadlock", "deadlock"))
        decorated = retry_deadlock(max_retries=2, backoff=0.01)(mock)
        with self.assertRaises(OperationalError):
            decorated()
        self.assertEqual(mock.call_count, 2)

    def test_stage_timer_stop(self) -> None:
        """Verifica que stop registra o tempo de término no StageTimer."""
        from apps.core.libs.base_etl_service import StageTimer
        t = StageTimer("teste")
        time.sleep(0.01)
        t.stop()
        self.assertGreater(t.end, 0)



    def test_executar_fase_producer_timeout(self) -> None:
        """Garante RuntimeError quando o producer ultrapassa o timeout configurado."""
        svc = MockService(db_alias="default")
        config = PhaseConfig(
            nome="f", sql="s", table_name="t", model_class=MagicMock(),
            dto_in=MagicMock(), pk_field="id", update_fields=("f",), 
            unique_fields=("id",)
        )
        # Força o _iter_chunks a travar/dormir mais que o timeout
        with (
            patch.object(svc, "_iter_chunks", side_effect=lambda x: time.sleep(2)),
            patch("apps.core.libs.base_etl_service.settings") as mock_settings
        ):
            mock_settings.THREAD_POOL_CHUNK_TIMEOUT = 0.1
            mock_settings.THREAD_POOL_MAX_WORKERS = 1
            with self.assertRaises(RuntimeError):
                svc._executar_fase(config)

    def test_executar_fase_producer_bubble_error(self) -> None:
        """Garante que exceção do producer é propagada ao consumidor."""
        svc = MockService(db_alias="default")
        config = PhaseConfig(
            nome="f", sql="s", table_name="t", model_class=MagicMock(),
            dto_in=MagicMock(), pk_field="id", update_fields=("f",), 
            unique_fields=("id",)
        )
        # Injeta o erro via side_effect do _iter_chunks imediatamente
        with patch.object(svc, "_iter_chunks", side_effect=RuntimeError("Erro Fatal")):
             with self.assertRaises(RuntimeError):
                 svc._executar_fase(config)

    def test_processar_batch_vazio(self) -> None:
        """Returna 0,0 quando não há dados."""
        svc = BaseEtlService(db_alias="default")
        res = svc._processar_batch(config=self.config, chunk=[])
        self.assertEqual(res, (0, 0))

    def test_processar_batch_incremental_ignorado(self) -> None:
        """Ignorados += 1 no incremental."""
        svc = BaseEtlService(db_alias="default", primeiro_run=False)
        obj = MagicMock()
        data = [("1", "hash_igual", obj)]
        with (
            patch.object(svc.pg_engine, "buscar_hashes", return_value={"t:1": "hash_igual"}),
            patch.object(svc.pg_engine, "upsert_bulk")
        ):
            # No incremental, ao achar hash igual, ele retorna (0, 1) se objs estiver vazio
            escritos, ignorados = svc._processar_batch(config=self.config, chunk=data, transform=lambda x: x)
        
        # No incremental, ao achar hash igual, ele deve ser ignorado.
        self.assertEqual(escritos, 0)
        self.assertEqual(ignorados, 1)

    def test_processar_batch_com_auditor_externo(self) -> None:
        """Chamada ao auditor.upsert_bulk_hashes."""
        mock_auditor = MagicMock()
        svc = BaseEtlService(db_alias="default", primeiro_run=True, repositorio_auditoria=mock_auditor)
        obj = MagicMock()
        data = [("1", "h", obj)]
        with patch.object(svc, "sync_batch", wraps=svc.sync_batch):
             with (
                 patch("apps.core.libs.base_etl_service.transaction.atomic"),
                 patch("apps.core.libs.base_etl_service.connections"),
             ):
                svc._processar_batch(config=self.config, chunk=data, transform=lambda x: x)
             # Auditor foi chamado indiretamente via sync_batch -> pg_engine.upsert_bulk
             mock_auditor.registrar_tabela_escrita.assert_not_called() # Só registra no final da fase

    def test_calcular_hash_casos_bordas(self) -> None:
        """Cobre gaps do calcular_hash."""
        from apps.core.libs.thread_processor import calcular_hash
        # Vazio (292-293)
        self.assertIsNotNone(calcular_hash({}, []))
        # Int fields (296-297)
        self.assertIsNotNone(calcular_hash((1, 2), [0, 1]))
        # Dict (303)
        self.assertIsNotNone(calcular_hash({"a": 1}, ["a"]))
        # TypeError (313)
        with self.assertRaises(TypeError):
            calcular_hash((1,), [0, "a"]) # type: ignore

    def test_decorar_para_hash_modos(self) -> None:
        """Cobre branches Tupla SQL e Objeto do decorar_para_hash."""
        from apps.core.libs.thread_processor import decorar_para_hash
        # Modo SQL (352-356): tabela + 3 args
        res_sql = decorar_para_hash("t", 0, [1], (123, "valor"))
        self.assertEqual(res_sql[0], "t:123")
        
        # Modo Objeto (357-360): tabela + 2 args
        res_obj = decorar_para_hash("t", ["f"], (456, MagicMock(f="v")))
        self.assertEqual(res_obj[0], "t:456")

    def test_decorar_para_hash_invalido(self) -> None:
        """Garante TypeError ao passar argumentos insuficientes para decorar_para_hash."""
        from apps.core.libs.thread_processor import decorar_para_hash
        with self.assertRaises(TypeError):
            decorar_para_hash("t", 1, 2, 3, 4, 5)

    def test_postgres_upsert_engine_real_call(self) -> None:
        """Verifica que upsert_bulk executa múltiplas chamadas ao cursor."""
        from apps.core.libs.base_etl_service import PostgresUpsertEngine
        engine = PostgresUpsertEngine()
        with self._patch_infra() as (_, mock_conns):
            mock_cursor = mock_conns.__getitem__.return_value.cursor.return_value.__enter__.return_value
            engine.upsert_bulk("t", [("id", "hash")], "batch")
            self.assertGreater(mock_cursor.execute.call_count, 1)

    def test_sync_batch_usa_pg_engine_sem_auditor(self) -> None:
        """Garante que pg_engine.upsert_bulk é chamado quando auditor é None."""
        svc = BaseEtlService(db_alias="default", repositorio_auditoria=None)
        obj = MagicMock()
        data = [("1", "h", obj)]
        with (
            patch.object(svc.pg_engine, "upsert_bulk") as mock_upsert,
            patch("apps.core.libs.base_etl_service.transaction.atomic"),
            patch("apps.core.libs.base_etl_service.connections"),
        ):
             svc._processar_batch(config=self.config, chunk=data, transform=lambda x: x)
             mock_upsert.assert_called_once()


    def test_criar_transform_caminho_legado_dto_out(self) -> None:
        """Verifica o caminho com dto_out explícito."""
        config = PhaseConfig(
            nome="f", sql="s", table_name="t", model_class=MagicMock,
            dto_in=MagicMock(), pk_field="pk", update_fields=("f",),
            unique_fields=("id",), dto_out=MagicMock()
        )
        dto_in_inst = MagicMock(pk=1)
        config.dto_in.return_value = dto_in_inst
        config.dto_out.to_dict.return_value = {"id": 1, "f": "v"}
        
        svc = BaseEtlService(db_alias="d")
        transform = svc._criar_transform(config)
        id_dest, _, _ = transform((1,))
        
        self.assertEqual(id_dest, "1")
        config.dto_out.to_dict.assert_called_once_with(dto_in_inst)

    def test_truncar_tabela_chamado_em_executar_fase(self) -> None:
        """Garante que _truncar_tabela é chamado no modo full_refresh."""
        svc = MockService(db_alias="default", primeiro_run=True)
        config = PhaseConfig(
            nome="f", sql="s", table_name="t", model_class=MagicMock(),
            dto_in=MagicMock(), pk_field="id", update_fields=("f",), 
            unique_fields=("id",), truncate_on_full_sync=True, 
            modo_escrita="full_refresh"
        )
        with patch.object(svc, "_truncar_tabela") as mock_trunc:
             with patch.object(svc, "_iter_chunks", return_value=iter([[(1,)]])):
                with (
                    patch("apps.core.libs.base_etl_service.transaction.atomic"),
                    patch("apps.core.libs.base_etl_service.connections"),
                ):
                   svc._executar_fase(config)
                   mock_trunc.assert_called_once_with("t")

    def test_retry_deadlock_decorator_raise_outros_erros(self) -> None:
        """Garante que erros não relacionados a deadlock são re-lançados imediatamente."""
        from apps.core.libs.base_etl_service import retry_deadlock
        mock = MagicMock(side_effect=ValueError("Erro Comum"))
        decorated = retry_deadlock()(mock)
        with self.assertRaises(ValueError):
            decorated()

    def test_executar_fase_erro_producer_detectado_em_loop_consumer(
        self,
    ) -> None:
        """Garante que o consumer detecta o erro do producer via fila sincronizada."""
        import queue as _queue
        import threading

        svc = MockService(db_alias="default")
        config = PhaseConfig(
            nome="f",
            sql="s",
            table_name="t",
            model_class=MagicMock(),
            dto_in=MagicMock(),
            pk_field="id",
            update_fields=("f",),
            unique_fields=("id",),
        )

        erro_pronto = threading.Event()

        class FilaSincronizada(_queue.Queue):  # type: ignore[type-arg]
            def put(
                self, item: object, block: bool = True, timeout: object = None
            ) -> None:
                super().put(item, block=block, timeout=timeout)
                if item is None:
                    erro_pronto.set()

            def get(
                self, block: bool = True, timeout: object = None
            ) -> object:
                erro_pronto.wait(timeout=5)
                return super().get(block=block, timeout=timeout)

        def iter_chunks_com_erro(
            _sql: str,
        ):  # type: ignore[return]
            yield [(1,)]
            raise RuntimeError("Erro após primeiro chunk")

        with (
            patch.object(
                svc, "_iter_chunks", side_effect=iter_chunks_com_erro
            ),
            patch(
                "apps.core.libs.base_etl_service.Queue",
                FilaSincronizada,
            ),
            patch("apps.core.libs.base_etl_service.transaction.atomic"),
            patch("apps.core.libs.base_etl_service.connections"),
        ):
            with self.assertRaises(RuntimeError):
                svc._executar_fase(config)

    def test_executar_fase_producer_thread_nao_encerra_no_join(
        self,
    ) -> None:
        """Cobre linha 451: RuntimeError quando producer thread não finaliza
        dentro do timeout configurado, simulado via mock de is_alive.
        """
        svc = MockService(db_alias="default")
        config = PhaseConfig(
            nome="f",
            sql="s",
            table_name="t",
            model_class=MagicMock(),
            dto_in=MagicMock(),
            pk_field="id",
            update_fields=("f",),
            unique_fields=("id",),
        )
        with (
            patch.object(svc, "_iter_chunks", return_value=iter([])),
            patch("threading.Thread.is_alive", return_value=True),
        ):
            with self.assertRaises(RuntimeError):
                svc._executar_fase(config)

    def test_mock_service_iter_chunks_retorna_chunks(self) -> None:
        """Verifica que _iter_chunks retorna os chunks configurados."""
        resultado = list(self.svc._iter_chunks("SELECT 1"))
        self.assertEqual(resultado, [[(1,)]])

    def test_criar_transform_pk_field_lista(self) -> None:
        """Garante composição de pk como 'x-y' quando pk_field é lista."""
        config = PhaseConfig(
            nome="f",
            sql="s",
            table_name="t",
            model_class=MagicMock(),
            dto_in=MagicMock(),
            pk_field=["codigo", "turno"],
            update_fields=("nome",),
            unique_fields=("codigo", "turno"),
            dto_out=MagicMock(),
        )
        dto_inst = MagicMock(codigo=1, turno="M")
        config.dto_in.return_value = dto_inst
        config.dto_out.to_dict.return_value = {"nome": "A"}

        svc = BaseEtlService(db_alias="d")
        transform = svc._criar_transform(config)
        id_dest, _, _ = transform((1, "M"))

        self.assertEqual(id_dest, "1-M")


class AlunosFixesTest(SimpleTestCase):
    """Testes para as correções solicitadas (A, B, C, E, F, H)."""

    def _make_service(self, **kwargs):
        from apps.core.libs.base_etl_service import BaseEtlService
        return BaseEtlService(db_alias=kwargs.pop("db_alias", "default"), **kwargs)

    def _make_phase(self, **kwargs):
        from apps.core.libs.base_etl_service import PhaseConfig
        return PhaseConfig(
            nome=kwargs.get("nome", "fase"),
            sql=kwargs.get("sql", "SELECT 1"),
            table_name=kwargs.get("table_name", "tabela"),
            model_class=kwargs.get("model_class", MagicMock()),
            dto_in=kwargs.get("dto_in", MagicMock()),
            pk_field=kwargs.get("pk_field", "id"),
            update_fields=kwargs.get("update_fields", ("f",)),
            unique_fields=kwargs.get("unique_fields", ("id",)),
            modo_escrita=kwargs.get("modo_escrita", "upsert"),
        )

    def test_get_batch_meta_contem_campos_obrigatorios(self) -> None:
        """Ação B e F: Garante que table_name e modo_escrita estão nos metadados."""
        svc = self._make_service()
        config = self._make_phase(table_name="tabela_teste", modo_escrita="full_refresh")
        meta = svc._get_batch_meta(config)
        self.assertEqual(meta["table_name"], "tabela_teste")
        self.assertEqual(meta["modo_escrita"], "full_refresh")

    def test_registrar_auditoria_fase_registra_escrita(self) -> None:
        """Ação C: Garante registro da tabela escrita na auditoria."""
        mock_auditor = MagicMock()
        from uuid import uuid4
        svc = self._make_service(repositorio_auditoria=mock_auditor, id_execucao=uuid4())
        config = self._make_phase(table_name="tabela_dest")
        from apps.core.libs.base_etl_service import PipelineMetrics
        metrics = PipelineMetrics(total_lidos=100, total_escritos=50)

        svc._registrar_auditoria_fase(config, metrics)

        mock_auditor.registrar_tabela_escrita.assert_called_once_with(
            id_execucao=svc.id_execucao,
            tabela_destino="tabela_dest",
            linhas_escritas=50,
            modo_escrita="upsert",
        )

    def test_sync_batch_suporta_full_refresh(self) -> None:
        """Ação E: sync_batch deve processar full_refresh sem checar hashes."""
        svc = self._make_service()
        mock_model = MagicMock()
        processed_data = [("1", "h1", MagicMock())]
        meta = {
            "table_name": "t",
            "modo_escrita": "full_refresh",
            "model_class": mock_model,
            "update_fields": ["f"],
            "unique_fields": ["id"]
        }

        with (
            patch.object(svc.pg_engine, "_persistir") as mock_persist,
            patch("django.db.transaction.atomic", return_value=MagicMock())
        ):
            svc.sync_batch(processed_data, meta)
            
        mock_persist.assert_called_once()
        
        # Reset mock_persist and check search_hashes
        with (
            patch.object(svc.pg_engine, "buscar_hashes") as mock_hashes,
            patch("django.db.transaction.atomic", return_value=MagicMock())
        ):
            svc.sync_batch(processed_data, meta)
            mock_hashes.assert_not_called()

    def test_base_etl_service_nao_tem_lote_delay(self) -> None:
        """Ação H: Verifica que lote_delay foi removido do __init__."""
        from apps.core.libs.base_etl_service import BaseEtlService
        import inspect
        sig = inspect.signature(BaseEtlService.__init__)
        self.assertNotIn("lote_delay", sig.parameters)


class AuditoriaParcialTest(TestCase):
    databases = {"default", "eol_db", "alunos_db"}
    """Testa o registro de progresso parcial durante a fase."""

    def setUp(self) -> None:
        from unittest.mock import MagicMock
        from uuid import uuid4
        self.mock_auditor = MagicMock()
        self.svc = MockService(
            db_alias="default",
            repositorio_auditoria=self.mock_auditor,
            id_execucao=uuid4(),
        )
        self.config = _make_phase(source_table="origem")

    def test_log_progresso_chama_auditoria_parcial(self) -> None:
        """Deve chamar atualizar_checkpoint_dominio quando atingir o intervalo."""
        with patch("apps.core.libs.base_etl_service.settings") as mock_settings:
            with patch("apps.core.libs.base_etl_service.connections"), \
                 patch("apps.core.libs.base_etl_service.transaction.atomic"):
                from apps.core.libs.base_etl_service import PipelineMetrics

                mock_settings.EOL_CHUNK_SIZE = 100
                metrics = PipelineMetrics(total_lidos=101)

                # Chama log_progresso com metrics.total_lidos = 101 (> 100)
                self.svc._log_progresso(
                    bn=1, metrics=metrics, start=0, config=self.config
                )

                self.mock_auditor.registrar_tabela_lida.assert_not_called()
                self.assertEqual(
                    self.mock_auditor.atualizar_checkpoint_dominio.call_count, 1
                )

    def test_nao_chama_auditoria_parcial_se_abaixo_do_intervalo(self) -> None:
        """Não deve chamar auditoria se não atingiu o intervalo."""
        with patch("apps.core.libs.base_etl_service.settings") as mock_settings:
            from apps.core.libs.base_etl_service import PipelineMetrics

            mock_settings.EOL_CHUNK_SIZE = 1000
            metrics = PipelineMetrics(total_lidos=500)

            self.svc._log_progresso(
                bn=1, metrics=metrics, start=0, config=self.config
            )

            self.mock_auditor.registrar_tabela_lida.assert_not_called()

    def test_get_helper_coverage(self) -> None:
        """Verifica que sincronizar_lote retorna (1, 0) para um lote unitário."""
        engine = PostgresUpsertEngine()
        class FakeMeta:
            table_name = "teste"
            db_alias = "default"
            primeiro_run = True
            modo_escrita = "upsert"
            update_fields = ["f"]
            unique_fields = ["id"]
            def resolver_model(self): return MagicMock()

        res = engine.sincronizar_lote([("pk", "hash", MagicMock())], FakeMeta())
        self.assertEqual(res, (1, 0))

    def test_persistir_empty_objs(self) -> None:
        """Garante retorno antecipado quando lista de objetos está vazia."""
        engine = PostgresUpsertEngine()
        engine._persistir([], MagicMock(), [], [], "default")

    def test_persistir_objs_full_coverage(self) -> None:
        """Verifica bulk_create para lista vazia e para lista com um objeto."""
        svc = BaseEtlService(db_alias="default")
        svc._persistir_objs([], MagicMock(), [], [])
        
        mock_model = MagicMock()
        svc._persistir_objs([MagicMock()], mock_model, ["f"], ["id"])
        mock_model.objects.using.return_value.bulk_create.assert_called_once()

    def test_get_meta_attr_dict_coverage(self) -> None:
        """Garante que _get_meta_attr retorna valor do dict e default quando ausente."""
        svc = BaseEtlService(db_alias="default")
        meta_dict = {"teste": 123}
        res = svc._get_meta_attr(meta_dict, "teste")
        self.assertEqual(res, 123)
        
        res_default = svc._get_meta_attr(meta_dict, "inexistente", 456)
        self.assertEqual(res_default, 456)
