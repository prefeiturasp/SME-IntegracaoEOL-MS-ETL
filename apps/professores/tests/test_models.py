"""Testes de string representation dos modelos de professores."""

from django.test import TestCase

from apps.professores.models import (
    CargoBaseServidor,
    FuncionarioCargo,
    FuncionarioUnidadeEducacional,
    Pessoa,
    Professor,
)


class ProfessoresModelsTest(TestCase):
    """Testes para cobrir métodos __str__ do app professores."""

    def test_professor_str(self) -> None:
        """Verifica __str__ de Professor."""
        obj = Professor(codigo_rf="123456", nome="PROF TESTE")
        self.assertEqual(str(obj), "123456 - PROF TESTE")

    def test_cargo_base_str(self) -> None:
        """Verifica __str__ de CargoBaseServidor."""
        p = Professor(codigo_rf="12345", nome="P")
        obj = CargoBaseServidor(id=1, professor=p)
        self.assertEqual(str(obj), "CargoBase #1 RF=12345")

    def test_pessoa_str(self) -> None:
        """Verifica __str__ de Pessoa."""
        obj = Pessoa(cpf="123.456.789-00", nome="PESSOA TESTE")
        self.assertEqual(str(obj), "123.456.789-00 - PESSOA TESTE")

    def test_funcionario_meta(self) -> None:
        """Valida metadados de FuncionarioUnidadeEducacional."""
        meta = FuncionarioUnidadeEducacional._meta
        self.assertEqual(meta.db_table, "funcionario_unidade_educacional")
        self.assertEqual(meta.pk.name, "id")
        self.assertEqual(meta.get_field("codigo_rf").max_length, 20)
        self.assertFalse(meta.get_field("data_inicio").null)
        self.assertTrue(meta.get_field("data_fim").null)
        self.assertTrue(meta.get_field("dt_fim_nomeacao").null)
        self.assertTrue(meta.get_field("dt_fim_funcao_atividade").null)
        self.assertTrue(meta.get_field("origem_vinculo").null)
        self.assertFalse(meta.get_field("codigo_tipo_funcao_atividade").null)
        self.assertTrue(meta.get_field("codigo_cargo").null)
        nomes_indices = {indice.name for indice in meta.indexes}
        self.assertIn("idx_funcionario_ue", nomes_indices)
        self.assertIn("idx_funcionario_cargo", nomes_indices)
        self.assertIn("idx_funcionario_rf", nomes_indices)
        self.assertIn("idx_funcionario_ue_cargo", nomes_indices)
        nomes_constraints = {
            constraint.name for constraint in meta.constraints
        }
        self.assertIn(
            "uq_funcionario_rf_ue_cargo_funcao_vinculo",
            nomes_constraints,
        )
        constraint = next(
            constraint
            for constraint in meta.constraints
            if constraint.name == "uq_funcionario_rf_ue_cargo_funcao_vinculo"
        )
        self.assertFalse(constraint.nulls_distinct)

    def test_funcionario_cargo_meta(self) -> None:
        """Valida metadados de FuncionarioCargo."""
        meta = FuncionarioCargo._meta
        self.assertEqual(meta.db_table, "funcionario_cargo")
        self.assertEqual(meta.pk.name, "id")
        self.assertEqual(meta.get_field("codigo_rf").max_length, 20)
        self.assertTrue(meta.get_field("data_inicio").null)
        self.assertTrue(meta.get_field("data_fim").null)
        nomes_indices = {indice.name for indice in meta.indexes}
        self.assertIn("idx_funcionario_cargo_codigo", nomes_indices)
        self.assertIn("idx_funcionario_cargo_rf", nomes_indices)
        nomes_constraints = {
            constraint.name for constraint in meta.constraints
        }
        self.assertIn("uq_funcionario_cargo_vinculo", nomes_constraints)
        constraint = next(
            constraint
            for constraint in meta.constraints
            if constraint.name == "uq_funcionario_cargo_vinculo"
        )
        self.assertFalse(constraint.nulls_distinct)
