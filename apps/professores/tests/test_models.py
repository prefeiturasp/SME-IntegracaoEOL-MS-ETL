"""Testes de string representation dos modelos de professores."""

from django.test import TestCase

from apps.professores.models import (
    CargoBaseServidor,
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
