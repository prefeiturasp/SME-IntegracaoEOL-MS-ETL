"""Testes de string representation dos modelos de alunos."""
 
from django.test import TestCase
from apps.alunos.models import (
    TipoNecessidadeEspecial, Aluno, ResponsavelAluno,
    NecessidadeEspecialAluno, Matricula, MatriculaTurma
)
 
class AlunosModelsTest(TestCase):
    """Testes para cobrir métodos __str__ do app alunos."""
 
    def test_tipo_necessidade_especial_str(self) -> None:
        obj = TipoNecessidadeEspecial(
            codigo_necessidade_especial=1, descricao="NEE TESTE"
        )
        self.assertEqual(str(obj), "1 - NEE TESTE")
 
    def test_aluno_str(self) -> None:
        obj = Aluno(codigo_aluno=12345, nome="ALUNO TESTE")
        self.assertEqual(str(obj), "12345 - ALUNO TESTE")
 
    def test_responsavel_aluno_str(self) -> None:
        aluno = Aluno(codigo_aluno=12345, nome="ALUNO")
        obj = ResponsavelAluno(aluno=aluno, nome="RESPONSAVEL TESTE")
        self.assertEqual(str(obj), "RESPONSAVEL TESTE (Aluno: 12345)")
 
    def test_necessidade_especial_aluno_str(self) -> None:
        aluno = Aluno(codigo_aluno=12345)
        nee = TipoNecessidadeEspecial(codigo_necessidade_especial=10)
        obj = NecessidadeEspecialAluno(
            aluno=aluno, necessidade_especial=nee
        )
        self.assertEqual(str(obj), "Aluno 12345 - NEE 10")
 
    def test_matricula_str(self) -> None:
        obj = Matricula(codigo_matricula=999, ano_letivo=2024)
        self.assertEqual(str(obj), "999 (2024)")
 
    def test_matricula_turma_str(self) -> None:
        obj = MatriculaTurma(matricula_id=100, codigo_turma=555)
        self.assertEqual(str(obj), "M: 100 - T: 555")
