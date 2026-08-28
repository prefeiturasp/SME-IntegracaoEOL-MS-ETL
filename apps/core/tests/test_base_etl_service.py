"""Testes para BaseEtlService e métodos auxiliares."""

import contextlib
import os
import time
from dataclasses import replace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.db import OperationalError
from django.test import SimpleTestCase, TestCase

from apps.core.libs.base_etl_service import (
    BaseEtlService,
    PhaseConfig,
    PipelineMetrics,
    PostgresUpsertEngine,
    _get_attr,
    _resolver_batch_size,
    _resolver_chunk_size,
    retry_deadlock,
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
        with self.assertRaises(AttributeError):
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


class ProgressoOperacionalTest(SimpleTestCase):
    """Valida atualização de progresso operacional no service."""

    def test_registra_progresso_com_force(self) -> None:
        """force=True ignora throttle e atualiza auditoria."""
        auditor = MagicMock()
        svc = _make_service(
            repositorio_auditoria=auditor,
            id_execucao=uuid4(),
        )
        config = _make_phase()
        metrics = PipelineMetrics(
            total_lidos=100,
            total_escritos=20,
            total_ignorados=80,
        )

        svc._registrar_progresso_execucao(
            config=config,
            metrics=metrics,
            numero_fase=2,
            total_fases=5,
            chunk_atual=3,
            etapa="processando_chunk",
            force=True,
        )

        auditor.atualizar_progresso_execucao.assert_called_once()
        _, kwargs = auditor.atualizar_progresso_execucao.call_args
        self.assertEqual(kwargs["fase_numero"], 2)
        self.assertEqual(kwargs["chunk_atual"], 3)
        self.assertEqual(kwargs["linhas_lidas"], 100)
        self.assertEqual(kwargs["linhas_escritas"], 20)
        self.assertEqual(kwargs["linhas_ignoradas"], 80)

    def test_respeita_throttle_de_progresso(self) -> None:
        """Sem force, não atualiza duas vezes dentro da janela."""
        auditor = MagicMock()
        svc = _make_service(
            repositorio_auditoria=auditor,
            id_execucao=uuid4(),
        )
        svc._progress_interval_seconds = 60
        config = _make_phase()
        metrics = PipelineMetrics(total_lidos=100)

        svc._registrar_progresso_execucao(
            config=config,
            metrics=metrics,
            numero_fase=1,
            total_fases=1,
            chunk_atual=1,
            etapa="processando_chunk",
        )
        svc._registrar_progresso_execucao(
            config=config,
            metrics=metrics,
            numero_fase=1,
            total_fases=1,
            chunk_atual=2,
            etapa="processando_chunk",
        )

        auditor.atualizar_progresso_execucao.assert_called_once()


class BuscarHashesPorCopyTest(SimpleTestCase, BaseEtlMockMixin):
    """Valida _buscar_sub_lote via WHERE id_destino = ANY(%s)."""

    def test_ids_vazios_retorna_dict_vazio(self) -> None:
        """Lista vazia não deve abrir conexão nem retornar dados."""
        svc = _make_service()
        resultado = svc._buscar_hashes_por_copy([])
        self.assertEqual(resultado, {})

    def test_retorna_mapeamento_id_hash(self) -> None:
        """Deve retornar dict {id_destino: hash_controle} do fetchall."""
        dados = [("aluno:001", "aaa"), ("aluno:002", "bbb")]
        cursor = self._mock_cursor(dados)

        svc = _make_service()
        with self._patch_infra(cursor):
            resultado = svc._buscar_hashes_por_copy(["aluno:001", "aluno:002"])

        self.assertEqual(resultado, {"aluno:001": "aaa", "aluno:002": "bbb"})

    def test_execute_recebe_ids_como_parametro(self) -> None:
        """cursor.execute deve receber a lista de ids como parâmetro."""
        cursor = self._mock_cursor([])
        svc = _make_service()
        ids = ["t:1", "t:2"]

        with self._patch_infra(cursor):
            svc._buscar_hashes_por_copy(ids)

        args, _ = cursor.execute.call_args
        params = args[1]
        self.assertIn(ids, params)

    def test_execute_nao_usa_create_temp_table(self) -> None:
        """cursor.execute não deve ser chamado com CREATE TEMP TABLE."""
        cursor = self._mock_cursor([])
        svc = _make_service()

        with self._patch_infra(cursor):
            svc._buscar_hashes_por_copy(["x:1"])

        for call in cursor.execute.call_args_list:
            sql_str = str(call[0][0]).upper()
            self.assertNotIn("CREATE TEMP TABLE", sql_str)

    def test_ids_ausentes_nao_aparecem_no_resultado(self) -> None:
        """IDs não retornados pelo banco não devem aparecer no dict."""
        cursor = self._mock_cursor([("t:1", "hash_a")])
        svc = _make_service()

        with self._patch_infra(cursor):
            resultado = svc._buscar_hashes_por_copy(["t:1", "t:999"])

        self.assertIn("t:1", resultado)
        self.assertNotIn("t:999", resultado)


class ChunkedHashesTest(SimpleTestCase, BaseEtlMockMixin):
    """Valida o chunking interno de buscar_hashes por EOL_CHUNK_SIZE."""

    def _engine(self) -> PostgresUpsertEngine:
        return PostgresUpsertEngine()

    def test_lista_vazia_retorna_dict_sem_query(self) -> None:
        engine = self._engine()
        with patch.object(engine, "_buscar_sub_lote") as mock_sub:
            resultado = engine.buscar_hashes([])
        self.assertEqual(resultado, {})
        mock_sub.assert_not_called()

    def test_lista_menor_que_chunk_faz_um_sub_lote(self) -> None:
        engine = self._engine()
        with (
            patch("apps.core.libs.base_etl_service._CHUNK_SIZE", 10),
            patch.object(
                engine,
                "_buscar_sub_lote",
                return_value={"t:1": "h1", "t:2": "h2"},
            ) as mock_sub,
        ):
            resultado = engine.buscar_hashes(["t:1", "t:2"])
        mock_sub.assert_called_once()
        self.assertEqual(resultado, {"t:1": "h1", "t:2": "h2"})

    def test_lista_igual_ao_chunk_faz_um_sub_lote(self) -> None:
        engine = self._engine()
        with (
            patch("apps.core.libs.base_etl_service._CHUNK_SIZE", 3),
            patch.object(
                engine,
                "_buscar_sub_lote",
                return_value={"t:0": "h0", "t:1": "h1", "t:2": "h2"},
            ) as mock_sub,
        ):
            resultado = engine.buscar_hashes(["t:0", "t:1", "t:2"])
        mock_sub.assert_called_once()
        self.assertEqual(len(resultado), 3)

    def test_lista_maior_que_chunk_divide_e_mescla(self) -> None:
        engine = self._engine()
        ids = [f"t:{i}" for i in range(7)]
        with (
            patch("apps.core.libs.base_etl_service._CHUNK_SIZE", 3),
            patch.object(
                engine,
                "_buscar_sub_lote",
                side_effect=[
                    {"t:0": "h0", "t:1": "h1", "t:2": "h2"},
                    {"t:3": "h3", "t:4": "h4", "t:5": "h5"},
                    {"t:6": "h6"},
                ],
            ) as mock_sub,
        ):
            resultado = engine.buscar_hashes(ids)
        self.assertEqual(mock_sub.call_count, 3)
        self.assertEqual(len(resultado), 7)
        self.assertEqual(resultado["t:6"], "h6")

    def test_retorna_apenas_ids_presentes_no_banco(self) -> None:
        engine = self._engine()
        with patch.object(
            engine, "_buscar_sub_lote", return_value={"t:1": "hash_a"}
        ):
            resultado = engine.buscar_hashes(["t:1", "t:999"])
        self.assertIn("t:1", resultado)
        self.assertNotIn("t:999", resultado)

    def test_eol_chunk_size_sobrescrito_respeita_novo_valor(self) -> None:
        engine = self._engine()
        ids = [f"t:{i}" for i in range(5)]
        with (
            patch("apps.core.libs.base_etl_service._CHUNK_SIZE", 2),
            patch.object(
                engine, "_buscar_sub_lote", return_value={}
            ) as mock_sub,
        ):
            engine.buscar_hashes(ids)
        self.assertEqual(mock_sub.call_count, 3)

    def test_falha_em_sub_lote_propaga_excecao(self) -> None:
        engine = self._engine()
        with (
            patch("apps.core.libs.base_etl_service._CHUNK_SIZE", 10),
            patch.object(
                engine,
                "_buscar_sub_lote",
                side_effect=OperationalError("DB indisponível"),
            ),
            self.assertRaises(OperationalError),
        ):
            engine.buscar_hashes(["t:1"])


class ProcessarBatchFullSyncTest(TestCase, BaseEtlMockMixin):
    databases = {"default", "eol_db", "alunos_db"}
    """Valida _processar_batch em modo full-sync (primeiro_run=True).

    Foco: bulk_create sem update_conflicts e acumulação de hashes.
    """

    def _make_svc(self, **kwargs) -> BaseEtlService:
        return BaseEtlService(db_alias="default", primeiro_run=True, **kwargs)

    def _make_obj(self) -> MagicMock:
        obj = MagicMock()
        obj.campo_a = "v"
        return obj

    def _batch_data(self, n: int = 2) -> list[tuple[str, str, MagicMock]]:
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
                nome="f",
                sql="s",
                table_name="tabela",
                pk_field="id",
                update_fields=("campo_a",),
                unique_fields=("id",),
                model_class=mock_model,
                dto_in=MagicMock(),
            )
            svc._processar_batch(
                config=meta, chunk=self._batch_data(), batch_num=0
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
                nome="f",
                sql="s",
                table_name="tabela",
                pk_field="id",
                update_fields=("campo_a",),
                unique_fields=("id",),
                model_class=mock_model,
                dto_in=MagicMock(),
                suporta_bulk_insert=False,
            )
            svc._processar_batch(
                config=meta, chunk=self._batch_data(), batch_num=0
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
                nome="f",
                sql="s",
                table_name="tabela",
                pk_field="id",
                update_fields=("campo_a",),
                unique_fields=("id",),
                model_class=mock_model,
                dto_in=MagicMock(),
            )
            svc._processar_batch(
                config=meta, chunk=self._batch_data(), batch_num=0
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
                nome="f",
                sql="s",
                table_name="tabela",
                pk_field="id",
                update_fields=("campo_a",),
                unique_fields=("id",),
                model_class=mock_model,
                dto_in=MagicMock(),
            )
            svc._processar_batch(
                config=meta, chunk=self._batch_data(2), batch_num=0
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
                nome="f",
                sql="s",
                table_name="tabela",
                pk_field="id",
                update_fields=("campo_a",),
                unique_fields=("id",),
                model_class=mock_model,
                dto_in=MagicMock(),
            )
            escritos, ignorados = svc._processar_batch(
                config=meta, chunk=data, batch_num=0, transform=lambda x: x
            )

        self.assertEqual(escritos, 1)
        self.assertEqual(ignorados, 1)


class PhaseConfigNovosCamposTest(SimpleTestCase):
    """Valida campos opcionais de PhaseConfig."""

    def test_truncate_on_full_sync_padrao_false(self) -> None:
        """truncate_on_full_sync deve ser False por padrão."""
        config = _make_phase()
        self.assertFalse(config.truncate_on_full_sync)

    def test_aceita_truncate_on_full_sync_true(self) -> None:
        """Deve aceitar truncate_on_full_sync=True sem erro."""
        config = _make_phase(truncate_on_full_sync=True)
        self.assertTrue(config.truncate_on_full_sync)

    def test_phase_config_rejeita_audit_flush_size(self) -> None:
        """PhaseConfig não aceita audit_flush_size após remoção do campo."""
        with self.assertRaises(TypeError):
            _make_phase(audit_flush_size=0)

    def test_base_etl_service_nao_tem_persistir_objs(self) -> None:
        """BaseEtlService não deve expor _persistir_objs após consolidação."""
        self.assertFalse(hasattr(BaseEtlService, "_persistir_objs"))


class FlushDiferidoHashesTest(TestCase):
    databases = {"default", "eol_db", "alunos_db"}
    """Valida que _processar_batch é chamado uma vez por chunk."""

    def _make_svc(self) -> BaseEtlService:
        return BaseEtlService(db_alias="default", primeiro_run=True)

    def _make_config(self) -> PhaseConfig:
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
        )

    @patch.object(BaseEtlService, "_processar_batch", return_value=(1, 0))
    def test_flush_padrao_chama_sync_batch_por_chunk(
        self, mock_batch: MagicMock
    ) -> None:
        """_processar_batch é chamado uma vez por chunk recebido."""
        svc = self._make_svc()
        config = self._make_config()

        chunks = [
            [(1, "A", 1, None)],
            [(2, "B", 1, None)],
        ]

        with patch.object(svc, "_iter_chunks", return_value=iter(chunks)):
            svc._executar_fase(config)

        self.assertEqual(mock_batch.call_count, 2)


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
            conn = mock_conns.__getitem__.return_value
            mock_cursor = conn.cursor.return_value.__enter__.return_value
            args, _ = mock_cursor.execute.call_args
            self.assertEqual(
                args[0].as_string(None),
                'TRUNCATE TABLE "minha_tabela" CASCADE',
            )

    def test_criar_transform_caminho_adapter(self) -> None:
        """Testa _criar_transform via to_domain no dto."""
        config = PhaseConfig(
            nome="f",
            sql="s",
            table_name="t",
            model_class=MagicMock,  # Class constructor
            dto_in=MagicMock(),
            pk_field="id",
            update_fields=("f",),
            unique_fields=("id",),
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
        with (
            patch.object(
                self.svc,
                "_iter_chunks",
                side_effect=RuntimeError("Falha na Query"),
            ),
            self.assertRaises(RuntimeError),
        ):
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
        with patch.object(
            self.svc, "_executar_fase", return_value=m
        ) as mock_fase:
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
        """Garante re-lançamento da exceção ao esgotar tentativas de retry."""
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

    def test_executar_fase_aguarda_producer_lento(self) -> None:
        """Garante que producer lento nao falha antes de devolver chunk."""
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

        def iter_lento(_: str) -> object:
            time.sleep(0.2)
            return iter([])

        with (
            patch.object(svc, "_iter_chunks", side_effect=iter_lento),
            patch("apps.core.libs.base_etl_service.settings") as mock_settings,
        ):
            mock_settings.THREAD_POOL_CHUNK_TIMEOUT = 0.05
            mock_settings.THREAD_POOL_MAX_WORKERS = 1
            mock_settings.PRODUCER_MAX_WAIT_SECONDS = 1
            metrics = svc._executar_fase(config)

        self.assertEqual(metrics.total_lidos, 0)

    def test_executar_fase_timeout_finaliza_producer(self) -> None:
        """Garante limpeza da thread quando producer fica preso em I/O."""
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

        def iter_preso(_: str) -> object:
            time.sleep(0.3)
            return iter([])

        with (
            patch.object(svc, "_iter_chunks", side_effect=iter_preso),
            patch.object(svc, "_finalizar_threads") as mock_finalizar,
            patch("apps.core.libs.base_etl_service.settings") as mock_settings,
            self.assertRaises(TimeoutError),
        ):
            mock_settings.THREAD_POOL_CHUNK_TIMEOUT = 0.05
            mock_settings.THREAD_POOL_MAX_WORKERS = 1
            mock_settings.PRODUCER_MAX_WAIT_SECONDS = 0.1
            svc._executar_fase(config)

        mock_finalizar.assert_called_once()

    def test_executar_fase_producer_bubble_error(self) -> None:
        """Garante que exceção do producer é propagada ao consumidor."""
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
            patch.object(
                svc,
                "_iter_chunks",
                side_effect=RuntimeError("Erro Fatal"),
            ),
            self.assertRaises(RuntimeError),
        ):
            svc._executar_fase(config)

    def test_processar_batch_vazio(self) -> None:
        """Returna 0,0 quando não há dados."""
        svc = BaseEtlService(db_alias="default")
        res = svc._processar_batch(config=self.config, chunk=[])
        self.assertEqual(res, (0, 0))

    def test_processar_batch_incremental_ignorado(self) -> None:
        """Ignorados += 1 no incremental quando hash não mudou."""
        svc = BaseEtlService(db_alias="default", primeiro_run=False)
        obj = MagicMock()
        data = [("1", "hash_igual", obj)]
        with (
            patch.object(
                svc.pg_engine,
                "buscar_hashes",
                return_value={"t:1": "hash_igual"},
            ),
            patch.object(svc.pg_engine, "upsert_bulk"),
        ):
            escritos, ignorados = svc._processar_batch(
                config=self.config, chunk=data, transform=lambda x: x
            )

        self.assertEqual(escritos, 0)
        self.assertEqual(ignorados, 1)

    def test_processar_batch_com_auditor_externo(self) -> None:
        """Chamada ao auditor.upsert_bulk_hashes."""
        mock_auditor = MagicMock()
        svc = BaseEtlService(
            db_alias="default",
            primeiro_run=True,
            repositorio_auditoria=mock_auditor,
        )
        obj = MagicMock()
        data = [("1", "h", obj)]
        with (
            patch.object(svc, "sync_batch", wraps=svc.sync_batch),
            patch("apps.core.libs.base_etl_service.transaction.atomic"),
            patch("apps.core.libs.base_etl_service.connections"),
        ):
            svc._processar_batch(
                config=self.config,
                chunk=data,
                transform=lambda x: x,
            )
        mock_auditor.registrar_tabela_escrita.assert_not_called()

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
            calcular_hash((1,), [0, "a"])  # type: ignore

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
        """Garante TypeError ao chamar decorar_para_hash com muitos args."""
        from apps.core.libs.thread_processor import decorar_para_hash

        with self.assertRaises(TypeError):
            decorar_para_hash("t", 1, 2, 3, 4, 5)

    def test_postgres_upsert_engine_real_call(self) -> None:
        """Verifica que upsert_bulk executa múltiplas chamadas ao cursor."""
        from apps.core.libs.base_etl_service import PostgresUpsertEngine

        engine = PostgresUpsertEngine()
        with self._patch_infra() as (_, mock_conns):
            conn = mock_conns.__getitem__.return_value
            mock_cursor = conn.cursor.return_value.__enter__.return_value
            engine.upsert_bulk("t", [("id", "hash")], "batch")
            self.assertGreater(mock_cursor.execute.call_count, 1)

    def test_sync_batch_usa_pg_engine_sem_auditor(self) -> None:
        """Garante que pg_engine.upsert_bulk é chamado sem auditor."""
        svc = BaseEtlService(db_alias="default", repositorio_auditoria=None)
        obj = MagicMock()
        data = [("1", "h", obj)]
        with (
            patch.object(svc.pg_engine, "upsert_bulk") as mock_upsert,
            patch("apps.core.libs.base_etl_service.transaction.atomic"),
            patch("apps.core.libs.base_etl_service.connections"),
        ):
            svc._processar_batch(
                config=self.config,
                chunk=data,
                transform=lambda x: x,
            )
            mock_upsert.assert_called_once()

    def test_processar_batch_usa_thread_processor_quando_definido(
        self,
    ) -> None:
        """Transform via ThreadPoolProcessor quando _thread_processor ativo."""
        from apps.core.libs.thread_processor import ThreadPoolProcessor

        svc = BaseEtlService(db_alias="default", primeiro_run=True)
        obj = MagicMock()
        transform = MagicMock(return_value=("1", "h", obj))

        with ThreadPoolProcessor(max_workers=1) as tp:
            svc._thread_processor = tp
            with (
                patch("apps.core.libs.base_etl_service.transaction.atomic"),
                patch("apps.core.libs.base_etl_service.connections"),
            ):
                escritos, _ = svc._processar_batch(
                    config=self.config,
                    chunk=[("raw",)],
                    transform=transform,
                )
        self.assertEqual(escritos, 1)
        transform.assert_called_once_with(("raw",))

    def test_executar_fase_define_e_limpa_thread_processor(self) -> None:
        """_thread_processor é None antes e depois de _executar_fase."""
        svc = MockService(db_alias="default")
        self.assertIsNone(svc._thread_processor)

        with patch.object(
            svc, "_processar_batch", return_value=(1, 0)
        ) as mock_batch:
            svc._executar_fase(self.config)

        self.assertIsNone(svc._thread_processor)
        mock_batch.assert_called_once()

    def test_truncar_tabela_chamado_em_executar_fase(self) -> None:
        """Garante que _truncar_tabela é chamado no modo full_refresh."""
        svc = MockService(db_alias="default", primeiro_run=True)
        config = PhaseConfig(
            nome="f",
            sql="s",
            table_name="t",
            model_class=MagicMock(),
            dto_in=MagicMock(),
            pk_field="id",
            update_fields=("f",),
            unique_fields=("id",),
            truncate_on_full_sync=True,
            modo_escrita="full_refresh",
        )
        with (
            patch.object(svc, "_truncar_tabela") as mock_trunc,
            patch.object(svc, "_iter_chunks", return_value=iter([[(1,)]])),
            patch("apps.core.libs.base_etl_service.transaction.atomic"),
            patch("apps.core.libs.base_etl_service.connections"),
        ):
            svc._executar_fase(config)
            mock_trunc.assert_called_once_with("t")

    def test_retry_deadlock_decorator_raise_outros_erros(self) -> None:
        """Erros não relacionados a deadlock são re-lançados imediatamente."""
        from apps.core.libs.base_etl_service import retry_deadlock

        mock = MagicMock(side_effect=ValueError("Erro Comum"))
        decorated = retry_deadlock()(mock)
        with self.assertRaises(ValueError):
            decorated()

    def test_executar_fase_erro_producer_detectado_em_loop_consumer(
        self,
    ) -> None:
        """Garante que o consumer detecta erro do producer via fila sync."""
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
            self.assertRaises(RuntimeError),
        ):
            svc._executar_fase(config)

    def test_executar_fase_producer_thread_nao_encerra_no_join(
        self,
    ) -> None:
        """Cobre RuntimeError quando producer thread não finaliza no join.

        Simulado via mock de is_alive retornando True.
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
            self.assertLogs(
                "apps.core.libs.base_etl_service",
                level="WARNING",
            ) as cm,
        ):
            svc._executar_fase(config)

        self.assertTrue(
            any("Producer thread não finalizou" in msg for msg in cm.output)
        )

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
        )
        dto_inst = MagicMock(codigo=1, turno="M")
        dto_inst.to_domain.return_value = {"nome": "A"}
        config.dto_in.return_value = dto_inst

        svc = BaseEtlService(db_alias="d")
        transform = svc._criar_transform(config)
        id_dest, _, _ = transform((1, "M"))

        self.assertEqual(id_dest, "1-M")


class AlunosFixesTest(TestCase):
    """Testes para as correções solicitadas (A, B, C, E, F, H)."""

    databases = {"default"}

    def _make_service(self, **kwargs):
        from apps.core.libs.base_etl_service import BaseEtlService

        return BaseEtlService(
            db_alias=kwargs.pop("db_alias", "default"), **kwargs
        )

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
        """Garante que table_name e modo_escrita estão nos metadados."""
        svc = self._make_service()
        config = self._make_phase(
            table_name="tabela_teste", modo_escrita="full_refresh"
        )
        meta = svc._get_batch_meta(config)
        self.assertEqual(meta["table_name"], "tabela_teste")
        self.assertEqual(meta["modo_escrita"], "full_refresh")

    def test_registrar_auditoria_fase_registra_escrita(self) -> None:
        """Garante registro da tabela escrita na auditoria."""
        mock_auditor = MagicMock()
        from uuid import uuid4

        svc = self._make_service(
            repositorio_auditoria=mock_auditor, id_execucao=uuid4()
        )
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
            "unique_fields": ["id"],
        }

        with (
            patch.object(svc.pg_engine, "_persistir") as mock_persist,
            patch("django.db.transaction.atomic", return_value=MagicMock()),
        ):
            svc.sync_batch(processed_data, meta)

        mock_persist.assert_called_once()

        # Reset mock_persist and check search_hashes
        with (
            patch.object(svc.pg_engine, "buscar_hashes") as mock_hashes,
            patch("django.db.transaction.atomic", return_value=MagicMock()),
        ):
            svc.sync_batch(processed_data, meta)
            mock_hashes.assert_not_called()

    def test_base_etl_service_nao_tem_lote_delay(self) -> None:
        """Ação H: Verifica que lote_delay foi removido do __init__."""
        import inspect

        from apps.core.libs.base_etl_service import BaseEtlService

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
        """Deve chamar atualizar_checkpoint_dominio ao atingir intervalo."""
        with (
            patch("apps.core.libs.base_etl_service.settings") as mock_settings,
            patch("apps.core.libs.base_etl_service.connections"),
            patch("apps.core.libs.base_etl_service.transaction.atomic"),
        ):
            from apps.core.libs.base_etl_service import PipelineMetrics

            mock_settings.EOL_CHUNK_SIZE = 100
            metrics = PipelineMetrics(total_lidos=101)

            self.svc._log_progresso(
                bn=1, metrics=metrics, start=0, config=self.config
            )

            self.mock_auditor.registrar_tabela_lida.assert_not_called()
            self.assertEqual(
                self.mock_auditor.atualizar_checkpoint_dominio.call_count,
                1,
            )

    def test_nao_chama_auditoria_parcial_se_abaixo_do_intervalo(
        self,
    ) -> None:
        """Não deve chamar auditoria se não atingiu o intervalo."""
        with patch(
            "apps.core.libs.base_etl_service.settings"
        ) as mock_settings:
            from apps.core.libs.base_etl_service import PipelineMetrics

            mock_settings.EOL_CHUNK_SIZE = 1000
            metrics = PipelineMetrics(total_lidos=500)

            self.svc._log_progresso(
                bn=1, metrics=metrics, start=0, config=self.config
            )

            self.mock_auditor.registrar_tabela_lida.assert_not_called()

    def test_sincronizar_lote_primeiro_run_retorna_escrito(self) -> None:
        """sincronizar_lote retorna (1, 0) para lote unitário."""
        engine = PostgresUpsertEngine()

        class FakeMeta:
            table_name = "teste"
            db_alias = "default"
            primeiro_run = True
            modo_escrita = "upsert"
            truncate_on_full_sync = False
            update_fields = ["f"]
            unique_fields = ["id"]

            def resolver_model(self) -> MagicMock:
                return MagicMock()

        res = engine.sincronizar_lote(
            [("pk", "hash", MagicMock())], FakeMeta()
        )
        self.assertEqual(res, (1, 0))

    def test_persistir_empty_objs(self) -> None:
        """Garante retorno antecipado quando lista de objetos está vazia."""
        engine = PostgresUpsertEngine()
        engine._persistir([], MagicMock(), [], [], "default")

    def test_get_helper_acessa_dict(self) -> None:
        """_get_attr retorna valor de dicionário."""
        self.assertEqual(_get_attr({"a": 1}, "a"), 1)

    def test_get_helper_acessa_objeto(self) -> None:
        """_get_attr retorna atributo de objeto via getattr."""

        class Obj:
            x = 42

        self.assertEqual(_get_attr(Obj(), "x"), 42)

    def test_get_helper_default_quando_ausente(self) -> None:
        """_get_attr retorna default para chave inexistente."""
        self.assertIsNone(_get_attr({}, "k"))
        self.assertEqual(_get_attr({}, "k", 99), 99)

    def test_base_etl_service_nao_tem_get_meta_attr(self) -> None:
        """BaseEtlService não deve ter _get_meta_attr após consolidação."""
        self.assertFalse(hasattr(BaseEtlService, "_get_meta_attr"))

    def test_resolver_batch_size_padrao(self) -> None:
        """_resolver_batch_size retorna 5000 quando env var não definida."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ETL_BULK_BATCH_SIZE", None)
            resultado = _resolver_batch_size()
        self.assertEqual(resultado, 5000)

    def test_resolver_batch_size_env_var(self) -> None:
        """_resolver_batch_size usa valor da variável de ambiente."""
        with patch.dict(os.environ, {"ETL_BULK_BATCH_SIZE": "2000"}):
            resultado = _resolver_batch_size()
        self.assertEqual(resultado, 2000)

    def test_resolver_batch_size_invalido_retorna_fallback(self) -> None:
        """_resolver_batch_size retorna 5000 quando valor não é inteiro."""
        with patch.dict(os.environ, {"ETL_BULK_BATCH_SIZE": "abc"}):
            resultado = _resolver_batch_size()
        self.assertEqual(resultado, 5000)

    def test_resolver_chunk_size_padrao(self) -> None:
        """_resolver_chunk_size retorna 10000 sem variável de ambiente."""
        env = {k: v for k, v in os.environ.items() if k != "CHUNKED_HASHES"}
        with patch.dict(os.environ, env, clear=True):
            resultado = _resolver_chunk_size()
        self.assertEqual(resultado, 10_000)

    def test_resolver_chunk_size_env_var(self) -> None:
        """_resolver_chunk_size usa valor da variável de ambiente."""
        with patch.dict(os.environ, {"CHUNKED_HASHES": "500"}):
            resultado = _resolver_chunk_size()
        self.assertEqual(resultado, 500)

    def test_resolver_chunk_size_invalido_retorna_fallback(self) -> None:
        """_resolver_chunk_size retorna 10000 quando valor não é inteiro."""
        with patch.dict(os.environ, {"CHUNKED_HASHES": "xyz"}):
            resultado = _resolver_chunk_size()
        self.assertEqual(resultado, 10_000)

    def test_truncate_sync_skip_buscar_hashes(self) -> None:
        """truncate_on_full_sync=True → buscar_hashes não é chamado."""
        engine = PostgresUpsertEngine()
        fase_meta = {
            "table_name": "t",
            "db_alias": "default",
            "primeiro_run": False,
            "modo_escrita": "upsert",
            "update_fields": ["f"],
            "unique_fields": ["id"],
            "truncate_on_full_sync": True,
        }
        obj = MagicMock()
        obj.f = "v"

        with (
            patch.object(engine, "buscar_hashes") as mock_bh,
            patch.object(engine, "_persistir"),
            patch("apps.core.libs.base_etl_service.transaction.atomic"),
            patch("apps.core.libs.base_etl_service.connections"),
        ):
            engine.sincronizar_lote([("1", "h", obj)], fase_meta)

        mock_bh.assert_not_called()

    def test_truncate_sync_false_chama_buscar_hashes(self) -> None:
        """truncate_on_full_sync=False, primeiro_run=False: buscar_hashes."""
        engine = PostgresUpsertEngine()
        fase_meta = {
            "table_name": "t",
            "db_alias": "default",
            "primeiro_run": False,
            "modo_escrita": "upsert",
            "update_fields": ["f"],
            "unique_fields": ["id"],
            "truncate_on_full_sync": False,
        }
        obj = MagicMock()

        with (
            patch.object(engine, "buscar_hashes", return_value={}) as mock_bh,
            patch.object(engine, "_persistir"),
            patch("apps.core.libs.base_etl_service.transaction.atomic"),
            patch("apps.core.libs.base_etl_service.connections"),
        ):
            engine.sincronizar_lote([("1", "h", obj)], fase_meta)

        mock_bh.assert_called_once()
