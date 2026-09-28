"""Valida o índice de vínculos atuais por UE e ano."""

from importlib import import_module

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db.models import Q
from django.test import SimpleTestCase

from apps.alunos.models import MatriculaTurma


class ListagemUeIndexTest(SimpleTestCase):
    """Preserva o alcance da consulta e a criação concorrente do índice."""

    def test_indice_nao_restringe_tipo_de_turma(self) -> None:
        """Cobre vínculos atuais de qualquer tipo sem excluir programas."""
        indices = {i.name: i for i in MatriculaTurma._meta.indexes}
        self.assertIn("idx_mt_atual_ue_ano", indices)
        index = indices["idx_mt_atual_ue_ano"]
        self.assertEqual(index.fields, ["codigo_ue_turma", "ano_letivo_turma"])
        self.assertEqual(index.condition, Q(origem_atual=True))
        self.assertIn("idx_mt_regular_ue_ano_origem", indices)

    def test_migration_cria_indice_concorrentemente(self) -> None:
        """Mantém a operação fora de transação e alinhada ao modelo."""
        migration = import_module(
            "apps.alunos.migrations.0026_indice_listagem_ue_ano"
        ).Migration
        self.assertFalse(migration.atomic)
        self.assertEqual(len(migration.operations), 1)
        operation = migration.operations[0]
        self.assertIsInstance(operation, AddIndexConcurrently)
        self.assertEqual(operation.model_name, "matriculaturma")
        index = next(
            i
            for i in MatriculaTurma._meta.indexes
            if i.name == "idx_mt_atual_ue_ano"
        )
        self.assertEqual(operation.index.deconstruct(), index.deconstruct())
