"""Testes dos __str__ dos modelos do app professores."""

from django.test import SimpleTestCase

from apps.professores.models import (
    CargoBaseServidor,
    Pessoa,
    Professor,
    TurmaEscola,
    UnidadeEducacional,
)


class ModelStrTest(SimpleTestCase):
    """Testa __str__ de todos os modelos sem acesso ao banco."""

    def test_unidade_educacional_str(self) -> None:
        """Verifica a representação __str__ de UnidadeEducacional."""
        obj = UnidadeEducacional(codigo_ue="000001")
        self.assertEqual(str(obj), "000001")

    def test_turma_escola_str(self) -> None:
        """Verifica __str__ de TurmaEscola."""
        obj = TurmaEscola(codigo_turma=9999, ano_letivo=2024)
        self.assertEqual(str(obj), "9999 (2024)")

    def test_professor_str(self) -> None:
        """Verifica a representação __str__ de Professor."""
        obj = Professor(codigo_rf="012345", nome="ANA SILVA")
        self.assertEqual(str(obj), "012345 - ANA SILVA")

    def test_cargo_base_str(self) -> None:
        """Verifica a representação __str__ de CargoBaseServidor."""
        obj = CargoBaseServidor()
        obj.pk = 1001
        obj.professor_id = "012345"
        self.assertEqual(str(obj), "CargoBase #1001 RF=012345")

    def test_pessoa_str(self) -> None:
        """Verifica a representação __str__ de Pessoa."""
        obj = Pessoa(cpf="123.456.789-00", nome="JOSE")
        self.assertEqual(str(obj), "123.456.789-00 - JOSE")
