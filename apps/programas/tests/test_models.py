"""Testes de models do app programas — __str__ e shape básico."""

from django.test import TestCase

from apps.programas.models import (
    ComponenteCurricularPrograma,
    MatriculaTurmaPrograma,
    TipoPrograma,
    TurmaPrograma,
    TurmaProgramaComponenteCurricular,
)


class TestTipoProgramaStr(TestCase):
    def test_str(self) -> None:
        tp = TipoPrograma(
            codigo_tipo_programa=649, nome="PAP Recuperação", categoria="PAP"
        )
        self.assertEqual(str(tp), "PAP Recuperação (649)")


class TestComponenteCurricularProgramaStr(TestCase):
    def test_str(self) -> None:
        cc = ComponenteCurricularPrograma(
            codigo_componente_curricular=1322,
            nome_componente_curricular="PAP Rec",
            categoria="PAP",
        )
        resultado = str(cc)
        self.assertIn("1322", resultado)
        self.assertIn("PAP Rec", resultado)
        self.assertIn("PAP", resultado)


class TestTurmaProgramaStr(TestCase):
    def test_str(self) -> None:
        t = TurmaPrograma(
            codigo_turma=12345,
            nome_turma="TURMA PAP 1A",
            codigo_ue="000001",
            codigo_dre="108900",
            ano_letivo=2025,
            situacao="O",
            codigo_tipo_programa=649,
            categoria="PAP",
        )
        resultado = str(t)
        self.assertIn("12345", resultado)
        self.assertIn("2025", resultado)


class TestTurmaProgramaComponenteCurricularStr(TestCase):
    def test_str(self) -> None:
        tcc = TurmaProgramaComponenteCurricular(
            codigo_turma=12345,
            codigo_componente_curricular=1322,
            nome_componente_curricular="PAP Rec",
        )
        resultado = str(tcc)
        self.assertIn("12345", resultado)
        self.assertIn("1322", resultado)


class TestMatriculaTurmaProgramaStr(TestCase):
    def test_str(self) -> None:
        m = MatriculaTurmaPrograma(
            codigo_aluno=99999,
            codigo_turma=12345,
            codigo_componente_curricular=1322,
        )
        resultado = str(m)
        self.assertIn("99999", resultado)
        self.assertIn("12345", resultado)
        self.assertIn("1322", resultado)
