"""Testes de string representation dos modelos de alunos."""

from django.test import TestCase

from apps.alunos.models import (
    Aluno,
    DadosAlunoAcompanhamentoEscolar,
    Matricula,
    MatriculaAnoLetivo,
    MatriculaComponenteCurricularAnoLetivo,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
    TipoNecessidadeEspecial,
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

    def test_matricula_possui_indice_codigo_dre(self) -> None:
        nomes_indices = {
            indice.name for indice in Matricula._meta.indexes
        }
        self.assertIn("idx_matricula_codigo_dre", nomes_indices)

    def test_matricula_turma_str(self) -> None:
        obj = MatriculaTurma(codigo_matricula=100, codigo_turma=555)
        self.assertEqual(str(obj), "M: 100 - T: 555")

    def test_matricula_turma_sem_matricula_str(self) -> None:
        obj = MatriculaTurma(codigo_matricula=None, codigo_turma=777)
        self.assertEqual(str(obj), "M: None - T: 777")

    def test_matricula_ano_letivo_str(self) -> None:
        obj = MatriculaAnoLetivo(
            codigo_dre="DRE01", codigo_ue="UE01", ano_letivo=2024
        )
        self.assertEqual(str(obj), "DRE01/UE01 (2024)")

    def test_matricula_componente_curricular_str(self) -> None:
        obj = MatriculaComponenteCurricularAnoLetivo(
            codigo_ue="UE01",
            componente_curricular_id=10,
            ano_letivo=2024,
        )
        self.assertEqual(str(obj), "UE01/CC:10 (2024)")

    def test_dados_aluno_acompanhamento_escolar_str(self) -> None:
        obj = DadosAlunoAcompanhamentoEscolar(
            codigo_aluno=12345,
            nome="ALUNO TESTE",
            codigo_ue="UE01",
        )
        self.assertEqual(str(obj), "12345 - ALUNO TESTE (UE01)")
