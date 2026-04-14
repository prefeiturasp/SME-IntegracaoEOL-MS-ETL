"""Testes para o pipeline assíncrono (Orquestrador, TaskPublisher, Chunks e Tasks)."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase
from celery.result import EagerResult

from apps.core.libs.base_etl_orquestrador import GenericEtlOrquestrador
from apps.core.libs.task_publisher import TaskPublisher, serializar_chunk, EtlJsonEncoder
from apps.core.libs.base_etl_chunck import BaseEtlChunk
from apps.core.libs.base_etl_fase import BaseEtlFase
from apps.core.tasks import processar_chunk, finalizar_fase, _lancar_fase_seguinte
from datetime import date, datetime
from decimal import Decimal

class AsyncPipelineTestCase(TestCase):
    """Cobre as classes e funções do fluxo assíncrono via Celery."""
    databases = {"default", "eol_db", "alunos_db"}

    def _get_fase_meta(self, nome="fase1", sql="SELECT 1", n=1, total=1) -> BaseEtlFase:
        return BaseEtlFase(
            nome=nome,
            sql=sql,
            table_name="t1",
            source_table="s1",
            model_path="apps.controle_auditoria.models.EtlExecucao",
            dto_in_path="apps.alunos.dtos.model_in.AlunoIn",
            pk_field="id",
            update_fields=["f1"],
            unique_fields=["id"],
            db_alias="eol_db",
            primeiro_run=True,
            suporta_bulk_insert=True,
            id_execucao=str(uuid4()),
            numero_fase=n,
            total_fases=total,
            dominio="teste",
            task_processamento_path="apps.core.tasks.processar_chunk",
            task_callback_path="apps.core.tasks.finalizar_fase"
        )

    def test_etl_json_encoder(self) -> None:
        encoder = EtlJsonEncoder()
        self.assertEqual(encoder.default(date(2023, 1, 1)), "2023-01-01")
        self.assertEqual(encoder.default(datetime(2023, 1, 1, 12, 0)), "2023-01-01T12:00:00")
        self.assertEqual(encoder.default(Decimal("10.5")), "10.5")
        with self.assertRaises(TypeError):
            encoder.default(object())

    def test_serializar_chunk_converte_tipos(self) -> None:
        chunk = [(1, date(2023, 1, 1), Decimal("100"), datetime(2023, 1, 1, 10, 0, 0))]
        res = serializar_chunk(chunk)
        self.assertEqual(res, [[1, "2023-01-01", "100", "2023-01-01T10:00:00"]])

    def test_task_publisher_cria_assinatura(self) -> None:
        mock_task = MagicMock()
        publisher = TaskPublisher(mock_task)
        fase_meta = self._get_fase_meta()
        publisher.criar_task([(1,)], fase_meta)
        mock_task.s.assert_called_once()

    def test_base_etl_chunk_cria_grupo(self) -> None:
        mock_task = MagicMock()
        mock_eol = MagicMock()
        mock_eol.iter_query.return_value = [[(1,)]]
        publisher = TaskPublisher(mock_task)
        leitor = BaseEtlChunk(mock_task, eol=mock_eol, publisher=publisher)
        tasks = leitor.criar_grupo(self._get_fase_meta())
        self.assertEqual(len(tasks), 1)

    @patch("apps.core.libs.base_etl_orquestrador.chord")
    @patch("apps.core.libs.base_etl_orquestrador.group")
    def test_generic_orquestrador_lanca_chord(self, mock_group, mock_chord) -> None:
        mock_service = MagicMock()
        mock_fase_config = MagicMock()
        mock_fase_config.to_meta.return_value = self._get_fase_meta()
        mock_service._fases = [mock_fase_config]
        mock_eol = MagicMock()
        mock_eol.iter_query.return_value = [[(1,)]]
        orquestrador = GenericEtlOrquestrador(mock_service, dominio="teste", id_execucao=uuid4(), eol=mock_eol)
        orquestrador.lancar(fase_inicial=1)
        self.assertTrue(mock_chord.called)

    @patch("apps.core.libs.base_etl_orquestrador.chord")
    @patch("apps.core.libs.base_etl_orquestrador.group")
    @patch("apps.core.libs.base_etl_orquestrador.logger")
    def test_orquestrador_fase_sem_chunks(self, mock_logger, mock_group, mock_chord) -> None:
        mock_service = MagicMock()
        mock_fase_config = MagicMock()
        mock_fase_config.to_meta.return_value = self._get_fase_meta()
        mock_service._fases = [mock_fase_config]
        mock_callback = MagicMock()
        mock_eol = MagicMock()
        mock_eol.iter_query.return_value = []
        orquestrador = GenericEtlOrquestrador(
            mock_service, dominio="teste", id_execucao=uuid4(), 
            task_callback=mock_callback, eol=mock_eol
        )
        orquestrador.lancar(fase_inicial=1)
        mock_callback.apply_async.assert_called_once()

    @patch("apps.core.tasks.BaseEtlFase.from_dict")
    @patch("apps.core.tasks.PostgresUpsertEngine")
    @patch("apps.core.tasks.ThreadPoolProcessor")
    def test_task_processar_chunk_sucesso(self, mock_tp, mock_upsert, mock_fase_from_dict) -> None:
        mock_fase = MagicMock()
        mock_fase_from_dict.return_value = mock_fase
        mock_fase.get_transformer.return_value = lambda x: x
        mock_processor = mock_tp.return_value.__enter__.return_value
        mock_processor.processar.return_value = [("pk", "hash", "obj")]
        mock_upsert.return_value.sincronizar_lote.return_value = (1, 0)
        res = processar_chunk.apply(args=[[(1,)], {"d": 1}]).get()
        self.assertEqual(res, (1, 0))

    @patch("apps.core.tasks.BaseEtlFase.from_dict")
    @patch("apps.core.tasks.RepositorioAuditoriaPostgres")
    @patch("apps.core.tasks._lancar_fase_seguinte")
    def test_task_finalizar_fase(self, mock_lancar, mock_repo, mock_fase_from_dict) -> None:
        fase = self._get_fase_meta(n=1, total=2)
        mock_fase_from_dict.return_value = fase
        finalizar_fase.apply(args=[[(1, 0)], fase.to_dict(), [{}, {}]]).get()
        self.assertTrue(mock_lancar.called)

    @patch("apps.core.tasks.BaseEtlFase.from_dict")
    @patch("apps.core.tasks._lancar_fase_seguinte")
    def test_task_finalizar_fase_final(self, mock_lancar, mock_fase_from_dict) -> None:
        fase = self._get_fase_meta(n=1, total=1)
        mock_fase_from_dict.return_value = fase
        with patch("apps.core.tasks.RepositorioAuditoriaPostgres") as mock_repo:
            finalizar_fase.apply(args=[[(1, 0)], fase.to_dict(), [{}]]).get()
            mock_repo.return_value.finalizar_execucao.assert_called_once()

    @patch("apps.core.tasks.BaseEtlFase.from_dict")
    @patch("apps.core.tasks.BaseEtlChunk")
    @patch("apps.core.tasks.chord")
    def test_lancar_fase_seguinte_sucesso(self, mock_chord, mock_leitor_cls, mock_fase_from_dict) -> None:
        fase_atual = self._get_fase_meta(n=1, total=2)
        proxima = self._get_fase_meta(n=2, total=2)
        mock_fase_from_dict.return_value = proxima
        mock_leitor_cls.return_value.criar_grupo.return_value = [MagicMock()]
        _lancar_fase_seguinte(fase_atual, [{}, {}])
        self.assertTrue(mock_chord.called)

    @patch("apps.core.tasks.BaseEtlFase.from_dict")
    def test_lancar_fase_seguinte_vazia(self, mock_fase_from_dict) -> None:
        fase_atual = self._get_fase_meta(n=1, total=2)
        proxima = self._get_fase_meta(n=2, total=2)
        mock_fase_from_dict.return_value = proxima
        mock_callback = MagicMock()
        with patch.object(proxima, "resolver_task_callback", return_value=mock_callback):
            with patch("apps.core.tasks.BaseEtlChunk") as mock_leitor_cls:
                mock_leitor_cls.return_value.criar_grupo.return_value = []
                _lancar_fase_seguinte(fase_atual, [{}, {}])
                mock_callback.apply_async.assert_called_once()

    @patch("apps.core.tasks.BaseEtlFase.from_dict")
    def test_lancar_fase_seguinte_erro_resolucao(self, mock_fase_from_dict) -> None:
        fase_atual = self._get_fase_meta(n=1, total=2)
        proxima = self._get_fase_meta(n=2, total=2)
        mock_fase_from_dict.return_value = proxima
        with patch.object(proxima, "resolver_task_processamento", return_value=None):
            _lancar_fase_seguinte(fase_atual, [{}, {}])

    def test_base_etl_service_misc(self) -> None:
        from apps.core.libs.base_etl_service import BaseEtlService
        service = BaseEtlService("default")
        with self.assertRaises(NotImplementedError):
            service._iter_chunks("SQL")
        service._registrar_progresso_parcial(MagicMock(), MagicMock(), 1)
        service._registrar_auditoria_fase(MagicMock(), MagicMock())
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        with self.assertRaises(RuntimeError):
            service._finalizar_threads(mock_thread, [RuntimeError("E")])
        mock_thread.is_alive.return_value = True
        with self.assertRaises(RuntimeError):
            service._finalizar_threads(mock_thread, [])

    def test_thread_processor_context(self) -> None:
        from apps.core.libs.thread_processor import ThreadPoolProcessor
        with ThreadPoolProcessor(max_workers=2) as processor:
            res = processor.processar([1], lambda x: x)
            self.assertEqual(res, [1])
