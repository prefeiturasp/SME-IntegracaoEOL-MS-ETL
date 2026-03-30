"""Testes dos __str__ dos modelos do app professores."""

from django.test import SimpleTestCase

from apps.professores.models import (
    DRE,
    Cargo,
    CargoBaseServidor,
    ComponenteCurricular,
    FuncaoFuncionarioExterno,
    Pessoa,
    Professor,
    SerieEnsino,
    TerritorioSaber,
    TipoEscola,
    TipoExperienciaPedagogica,
    TurmaEscola,
    UnidadeEducacional,
)


class ModelStrTest(SimpleTestCase):
    """Testa __str__ de todos os modelos sem acesso ao banco."""

    def test_dre_str_com_sigla(self) -> None:
        """Verifica __str__ de DRE quando sigla está presente."""
        obj = DRE(codigo_dre="001", nome="DRE NORTE", sigla="DN")
        self.assertEqual(str(obj), "001 - DN")

    def test_dre_str_sem_sigla(self) -> None:
        """Verifica a representação __str__ de DRE quando sigla é None."""
        obj = DRE(codigo_dre="001", nome="DRE NORTE", sigla=None)
        self.assertEqual(str(obj), "001 - DRE NORTE")

    def test_tipo_escola_str_com_sigla(self) -> None:
        """Verifica __str__ de TipoEscola quando sigla está presente."""
        obj = TipoEscola(codigo_tipo_escola=1, descricao="EMEF", sigla="EF")
        self.assertEqual(str(obj), "1 - EF")

    def test_tipo_escola_str_sem_sigla(self) -> None:
        """Verifica __str__ de TipoEscola quando sigla é None."""
        obj = TipoEscola(codigo_tipo_escola=1, descricao="EMEF", sigla=None)
        self.assertEqual(str(obj), "1 - EMEF")

    def test_unidade_educacional_str(self) -> None:
        """Verifica a representação __str__ de UnidadeEducacional."""
        obj = UnidadeEducacional(codigo_ue="000001", nome="ESCOLA A")
        self.assertEqual(str(obj), "000001 - ESCOLA A")

    def test_componente_curricular_str(self) -> None:
        """Verifica a representação __str__ de ComponenteCurricular."""
        obj = ComponenteCurricular(codigo=10, descricao="MATEMATICA")
        self.assertEqual(str(obj), "10 - MATEMATICA")

    def test_serie_ensino_str(self) -> None:
        """Verifica a representação __str__ de SerieEnsino."""
        obj = SerieEnsino(codigo_serie=5, sigla_resumida="5A")
        self.assertEqual(str(obj), "5 - 5A")

    def test_territorio_saber_str(self) -> None:
        """Verifica a representação __str__ de TerritorioSaber."""
        obj = TerritorioSaber(codigo_territorio=1, descricao="TDS 1")
        self.assertEqual(str(obj), "1 - TDS 1")

    def test_tipo_experiencia_str(self) -> None:
        """Verifica __str__ de TipoExperienciaPedagogica."""
        obj = TipoExperienciaPedagogica(codigo_experiencia=2, descricao="EXP A")
        self.assertEqual(str(obj), "2 - EXP A")

    def test_turma_escola_str(self) -> None:
        """Verifica __str__ de TurmaEscola."""
        obj = TurmaEscola(codigo_turma=9999, nome_turma="TURMA A", ano_letivo=2024)
        self.assertEqual(str(obj), "9999 - TURMA A (2024)")

    def test_cargo_str(self) -> None:
        """Verifica a representação __str__ de Cargo."""
        obj = Cargo(codigo_cargo=3239, descricao="PEB I")
        self.assertEqual(str(obj), "3239 - PEB I")

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

    def test_funcao_funcionario_externo_str(self) -> None:
        """Verifica a representação __str__ de FuncaoFuncionarioExterno."""
        obj = FuncaoFuncionarioExterno(descricao="FUNCAO X")
        self.assertEqual(str(obj), "FUNCAO X")

    def test_pessoa_str(self) -> None:
        """Verifica a representação __str__ de Pessoa."""
        obj = Pessoa(cpf="123.456.789-00", nome="JOSE")
        self.assertEqual(str(obj), "123.456.789-00 - JOSE")
