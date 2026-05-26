"""Testes para tasks Celery do domínio Alunos."""

from unittest.mock import MagicMock, patch
from django.test import TestCase
from uuid import uuid4


def _fase_meta_dict(**kwargs: object) -> dict:
    defaults = {
        "nome": "aluno",
        "sql": "SELECT 1",
        "table_name": "aluno",
        "source_table": "aluno",
        "model_path": "apps.alunos.models.Aluno",
        "dto_in_path": "apps.alunos.dtos.model_in.AlunoIn",
        "pk_field": "codigo_aluno",
        "update_fields": ["nome", "cpf"],
        "unique_fields": ["codigo_aluno"],
        "db_alias": "alunos_db",
        "primeiro_run": False,
        "suporta_bulk_insert": False,
        "id_execucao": str(uuid4()),
        "numero_fase": 2,
        "total_fases": 6,
        "dominio": "alunos",
        "task_processamento_path": "apps.core.tasks.processar_chunk",
        "task_callback_path": "apps.core.tasks.finalizar_fase",
    }
    defaults.update(kwargs)
    return defaults


class TestProcessarChunkAlunos(TestCase):
    """Testes para a task processar_chunk."""

    @patch("apps.core.tasks.PostgresUpsertEngine")
    @patch("apps.core.tasks.ThreadPoolProcessor")
    @patch("apps.core.libs.base_etl_fase.BaseEtlFase.get_transformer")
    def test_caminho_feliz_retorna_tuple_com_escritos(
        self,
        mock_get_transformer: MagicMock,
        mock_processor_class: MagicMock,
        mock_upsert_class: MagicMock,
    ) -> None:
        """Valida que a task retorna tuple com escritos e ignorados."""
        from apps.core.tasks import processar_chunk

        mock_get_transformer.return_value = MagicMock()
        mock_processor = MagicMock()
        mock_processor.processar.return_value = [("1", "hash", MagicMock())]
        mock_processor_class.return_value = mock_processor

        mock_upsert = MagicMock()
        mock_upsert.sincronizar_lote.return_value = (5, 3)
        mock_upsert_class.return_value = mock_upsert

        chunk = [
            [1, "nome", None, None, None, None, None, None, None, None, None, False]
        ]
        resultado = processar_chunk.run(chunk, _fase_meta_dict())

        self.assertEqual(resultado, (5, 3))

    @patch("apps.core.tasks.PostgresUpsertEngine")
    @patch("apps.core.tasks.ThreadPoolProcessor")
    @patch("apps.core.libs.base_etl_fase.BaseEtlFase.get_transformer")
    def test_processar_chunk_usa_settings_para_max_workers(
        self,
        mock_get_transformer: MagicMock,
        mock_processor_class: MagicMock,
        mock_upsert_class: MagicMock,
    ) -> None:
        """Valida que ThreadPoolProcessor é instanciado sem max_workers fixo."""
        from apps.core.tasks import processar_chunk

        mock_get_transformer.return_value = MagicMock()
        mock_processor = MagicMock()
        mock_processor.processar.return_value = []
        mock_processor_class.return_value = mock_processor
        mock_upsert_class.return_value.sincronizar_lote.return_value = (0, 0)

        chunk: list = []
        processar_chunk.run(chunk, _fase_meta_dict())

        _, call_kwargs = mock_processor_class.call_args
        self.assertNotIn("max_workers", call_kwargs)

    @patch("apps.core.tasks.PostgresUpsertEngine")
    def test_excecao_aciona_retry(
        self,
        mock_upsert_class: MagicMock,
    ) -> None:
        """Valida que exceção no processamento lança retry do Celery."""
        from celery.exceptions import Retry
        from apps.core.tasks import processar_chunk

        mock_upsert_class.side_effect = RuntimeError("Falha")

        chunk = [
            [1, "nome", None, None, None, None, None, None, None, None, None, False]
        ]
        with self.assertRaises((Retry, RuntimeError)):
            processar_chunk.run(chunk, _fase_meta_dict())


class TestFinalizarFase(TestCase):
    """Testes para a task finalizar_fase (consolidada)."""

    @patch(
        "apps.core.tasks.RepositorioAuditoriaPostgres"
    )
    @patch("apps.core.tasks._lancar_fase_seguinte")
    def test_agrega_escritos_e_ignorados(
        self,
        mock_lancar: MagicMock,
        mock_repo_cls: MagicMock,
    ) -> None:
        """Valida que escritos/ignorados são somados e próxima fase lançada."""
        from apps.core.tasks import finalizar_fase

        resultados = [(10, 2), (5, 1)]
        meta = _fase_meta_dict(numero_fase=1, total_fases=6)
        todas = [meta] * 6

        finalizar_fase.run(resultados, meta, todas)

        mock_lancar.assert_called_once()
        mock_repo_cls.assert_called_once()

    @patch(
        "apps.core.tasks.RepositorioAuditoriaPostgres"
    )
    def test_ultima_fase_chama_finalizar_execucao_com_situacao(
        self,
        mock_repo_cls: MagicMock,
    ) -> None:
        """Valida que a última fase finaliza a execução com situacao='concluido'."""
        from apps.core.tasks import finalizar_fase

        mock_repo = mock_repo_cls.return_value
        resultados = [(3, 0)]
        meta = _fase_meta_dict(numero_fase=6, total_fases=6)
        todas = [meta] * 6

        finalizar_fase.run(resultados, meta, todas)

        args, kwargs = mock_repo.finalizar_execucao.call_args
        self.assertEqual(kwargs.get("situacao") or args[1], "concluido")

    @patch(
        "apps.core.tasks.RepositorioAuditoriaPostgres"
    )
    @patch("apps.core.tasks._lancar_fase_seguinte")
    def test_chama_registrar_tabela_lida_e_escrita(
        self,
        mock_lancar: MagicMock,
        mock_repo_cls: MagicMock,
    ) -> None:
        """Valida que auditoria de leitura e escrita são registradas."""
        from apps.core.tasks import finalizar_fase

        mock_repo = mock_repo_cls.return_value
        resultados = [(7, 2)]
        meta = _fase_meta_dict(numero_fase=1, total_fases=6)
        todas = [meta] * 6

        finalizar_fase.run(resultados, meta, todas)

        mock_repo.registrar_tabela_lida.assert_called_once()
        mock_repo.registrar_tabela_escrita.assert_called_once()
        _, kwargs = mock_repo.registrar_tabela_escrita.call_args
        self.assertEqual(kwargs["linhas_escritas"], 7)
        self.assertEqual(kwargs["tabela_destino"], "aluno")
        mock_lancar.assert_called_once()

    def test_finalizar_fase_geral_nao_existe(self) -> None:
        """Valida que finalizar_fase_geral foi consolidado e removido."""
        import apps.core.tasks as tasks_module

        self.assertFalse(
            hasattr(tasks_module, "finalizar_fase_geral"),
            "finalizar_fase_geral deve ter sido consolidado em finalizar_fase",
        )


class TestBaseEtlChunkSemSleep(TestCase):
    """Valida que o produtor não bloqueia o processo Django."""

    @patch("apps.core.libs.base_etl_chunck.time", create=True)
    def test_criar_grupo_nao_chama_sleep(
        self,
        mock_time: MagicMock,
    ) -> None:
        """Valida que time.sleep não é invocado durante a criação do grupo."""
        from apps.core.libs.base_etl_chunck import BaseEtlChunk
        from unittest.mock import MagicMock

        mock_eol = MagicMock()
        mock_eol.iter_query.return_value = [[(1,)], [(2,)]]
        mock_publisher = MagicMock()
        mock_publisher.criar_task.return_value = MagicMock()

        leitor = BaseEtlChunk(
            task_processamento=MagicMock(),
            eol=mock_eol,
            publisher=mock_publisher,
        )

        fase_meta = MagicMock()
        fase_meta.sql = "SELECT 1"
        fase_meta.nome = "teste"
        fase_meta.numero_fase = 1
        fase_meta.total_fases = 1

        leitor.criar_grupo(fase_meta)

        if hasattr(mock_time, "sleep"):
            mock_time.sleep.assert_not_called()
