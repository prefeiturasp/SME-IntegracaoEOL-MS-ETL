"""Testes de string representation dos modelos pedagógicos."""

from django.test import TestCase
from apps.pedagogico.models import (
    DRE, TipoEscola, UnidadeEducacional, SerieEnsino, 
    ComponenteCurricular, TerritorioSaber, TipoExperienciaPedagogica, 
    TurmaEscola
)

class PedagogicoModelsTest(TestCase):
    """Testes para cobrir métodos __str__ do app pedagogico."""

    def test_dre_str(self) -> None:
        dre = DRE(codigo_dre="1", nome="DRE-1", sigla="D1")
        self.assertEqual(str(dre), "1 - D1")

    def test_tipo_escola_str(self) -> None:
        tipo = TipoEscola(codigo_tipo_escola=1, descricao="ESC")
        self.assertEqual(str(tipo), "1 - ESC")

    def test_unidade_educacional_str(self) -> None:
        ue = UnidadeEducacional(codigo_ue="100", nome="ESCOLA")
        self.assertEqual(str(ue), "100 - ESCOLA")

    def test_serie_ensino_str(self) -> None:
        se = SerieEnsino(codigo_serie=9, descricao="9ANO")
        self.assertEqual(str(se), "9 - 9ANO")

    def test_componente_curricular_str(self) -> None:
        cc = ComponenteCurricular(codigo_componente=10, descricao="ARTES")
        self.assertEqual(str(cc), "10 - ARTES")

    def test_territorio_saber_str(self) -> None:
        ts = TerritorioSaber(codigo_territorio=1, descricao="TERR")
        self.assertEqual(str(ts), "1 - TERR")

    def test_tipo_experiencia_pedagogica_str(self) -> None:
        te = TipoExperienciaPedagogica(codigo_experiencia=2, descricao="EXP")
        self.assertEqual(str(te), "2 - EXP")

    def test_turma_escola_str(self) -> None:
        te = TurmaEscola(codigo_turma=999, nome_turma="T1", ano_letivo=2024)
        self.assertEqual(str(te), "999 - T1 (2024)")
