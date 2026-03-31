"""Testes de string representation dos modelos de alunos."""

from django.test import TestCase
from apps.alunos.models import (
    DRE, TipoEscola, UnidadeEducacional, TurmaEscola, Aluno
)

class AlunosModelsTest(TestCase):
    """Testes para cobrir métodos __str__ do app alunos."""

    def test_dre_str(self) -> None:
        obj = DRE(codigo_dre="1", nome="DRE-1", sigla="D1")
        self.assertEqual(str(obj), "1 - D1")

    def test_tipo_escola_str(self) -> None:
        obj = TipoEscola(codigo_tipo_escola=1, descricao="ESC")
        self.assertEqual(str(obj), "1 - ESC")

    def test_unidade_educacional_str(self) -> None:
        obj = UnidadeEducacional(codigo_ue="100", nome="ESCOLA")
        self.assertEqual(str(obj), "100 - ESCOLA")

    def test_turma_escola_str(self) -> None:
        obj = TurmaEscola(codigo_turma=999, nome_turma="TURMA A", ano_letivo=2024)
        self.assertEqual(str(obj), "999 - TURMA A (2024)")

    def test_aluno_str(self) -> None:
        obj = Aluno(codigo_aluno=12345, nome="ALUNO TESTE")
        self.assertEqual(str(obj), "12345 - ALUNO TESTE")
