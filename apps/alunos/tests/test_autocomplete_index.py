"""Valida o índice de leitura do autocomplete por UE e ano."""

from importlib import import_module

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db.models import Q
from django.test import SimpleTestCase

from apps.alunos.models import MatriculaTurma
from config.db_router import DominioRouter


class AutocompleteIndexTest(SimpleTestCase):
    """Mantém modelo, migration e roteamento do índice alinhados."""

    def test_indice_atende_ue_ano_e_origem_de_turmas_regulares(self) -> None:
        """Restringe o índice à seleção de turmas regulares."""
        index = next(
            index
            for index in MatriculaTurma._meta.indexes
            if index.name == "idx_mt_regular_ue_ano_origem"
        )
        self.assertEqual(
            index.fields,
            ["codigo_ue_turma", "ano_letivo_turma", "origem_atual"],
        )
        self.assertEqual(index.condition, Q(codigo_tipo_turma=1))

    def test_migration_concorrente_corresponde_ao_modelo(self) -> None:
        """Cria o índice sem envolver a operação em uma transação."""
        migration = import_module(
            "apps.alunos.migrations.0025_indice_autocomplete_ue_ano"
        ).Migration
        self.assertFalse(migration.atomic)
        self.assertEqual(len(migration.operations), 1)
        operation = migration.operations[0]
        self.assertIsInstance(operation, AddIndexConcurrently)
        self.assertEqual(operation.model_name, "matriculaturma")
        index = next(
            index
            for index in MatriculaTurma._meta.indexes
            if index.name == operation.index.name
        )
        self.assertEqual(operation.index.deconstruct(), index.deconstruct())

    def test_router_restringe_migration_ao_banco_de_alunos(self) -> None:
        """Não direciona o índice para bancos de outros domínios."""
        router = DominioRouter()
        for alias in ("default", "alunos_db", "pedagogico_db"):
            with self.subTest(alias=alias):
                self.assertEqual(
                    router.allow_migrate(alias, "alunos"),
                    alias == "alunos_db",
                )
