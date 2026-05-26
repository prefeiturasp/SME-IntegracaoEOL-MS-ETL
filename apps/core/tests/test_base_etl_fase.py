"""Testes para BaseEtlFase (BaseEtlFase) serializável do core."""

from unittest.mock import MagicMock, patch
from django.test import TestCase
from apps.core.libs.base_etl_fase import BaseEtlFase

class TestBaseEtlFase(TestCase):
    """Testes de integridade e resolução do BaseEtlFase."""

    def _get_meta(self) -> BaseEtlFase:
        return BaseEtlFase(
            nome="teste",
            sql="SELECT 1",
            table_name="tabela",
            source_table="origem",
            model_path="apps.alunos.models.Aluno",
            dto_in_path="apps.alunos.dtos.model_in.AlunoIn",
            pk_field="codigo_aluno",
            update_fields=["nome"],
            unique_fields=["codigo_aluno"],
            db_alias="default",
            primeiro_run=False,
            suporta_bulk_insert=True,
            id_execucao=None,
            numero_fase=1,
            total_fases=1,
            dominio="teste",
            task_processamento_path="apps.core.tasks.processar_chunk",
            task_callback_path="apps.core.tasks.finalizar_fase"
        )

    def test_serialization_roundtrip(self) -> None:
        """Valida que to_dict e from_dict preservam dados."""
        meta = self._get_meta()
        data = meta.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["nome"], "teste")
        
        meta2 = BaseEtlFase.from_dict(data)
        self.assertEqual(meta2.nome, meta.nome)
        self.assertEqual(meta2.task_processamento_path, meta.task_processamento_path)

    def test_resolver_model_e_dto(self) -> None:
        """Valida a resolução dinâmica de classes via importlib."""
        meta = self._get_meta()
        model = meta.resolver_model()
        self.assertEqual(model.__name__, "Aluno")
        
        dto = meta.resolver_dto_in()
        self.assertEqual(dto.__name__, "AlunoIn")

    def test_resolver_tasks(self) -> None:
        """Valida a resolução dinâmica de tasks Celery."""
        meta = self._get_meta()
        task_proc = meta.resolver_task_processamento()
        self.assertTrue(callable(task_proc))
        self.assertEqual(task_proc.__name__, "processar_chunk")

    def test_get_transformer_produz_funcao_valida(self) -> None:
        """Valida que o transformer gerado funciona para uma linha fake."""
        meta = self._get_meta()
        transform = meta.get_transformer()
        self.assertTrue(callable(transform))
        
        fake_row = (
            1,
            "Teste",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
        )
        pk, _, obj = transform(fake_row)
        
        self.assertEqual(pk, "1")
        self.assertEqual(obj.nome, "Teste")

    def test_resolver_tasks_vazias(self) -> None:
        """Valida retorno None quando paths de task não existem."""
        meta = self._get_meta()
        meta.task_processamento_path = None
        meta.task_callback_path = None
        self.assertIsNone(meta.resolver_task_processamento())
        self.assertIsNone(meta.resolver_task_callback())

    def test_composite_pk_transformer(self) -> None:
        """Valida transformer com chave primária composta (list)."""
        meta = self._get_meta()
        meta.pk_field = ["codigo_aluno", "nome"]
        transform = meta.get_transformer()
        
        fake_row = (
            1,
            "Teste",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
        )
        pk, _, _ = transform(fake_row)
        self.assertEqual(pk, "1-Teste")
