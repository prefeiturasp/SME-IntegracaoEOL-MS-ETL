"""Testes dos DTOs (ModelIn/ModelOut) do app programas."""

import datetime

from django.test import TestCase

from apps.programas.dtos.model_in import (
    ComponenteCurricularProgramaIn,
    MatriculaTurmaProgramaIn,
    TipoProgramaIn,
    TurmaProgramaComponenteCurricularIn,
    TurmaProgramaIn,
)
from apps.programas.dtos.model_out import (
    ComponenteCurricularProgramaOut,
    MatriculaTurmaProgramaOut,
    TipoProgramaOut,
    TurmaProgramaComponenteCurricularOut,
    TurmaProgramaOut,
)
from apps.programas.enums import (
    CategoriaPrograma,
    ComponenteCurricularEOL,
    SituacaoMatricula,
    SituacaoTurma,
    TipoProgramaEOL,
)

_DATA_MATRICULA = datetime.date(2025, 2, 1)


def _row_tipo(id_=649, sigla="PAP-RECUP", descricao="PAP Recuperação"):
    return (id_, sigla, descricao)


def _row_componente(id_=1322, nome="PAP Rec Aprend"):
    return (id_, nome)


def _row_turma(
    codigo=12345, nome="TURMA PAP 1A", ue="000001", dre="108900",
    ano=2025, turno=1, desc_turno="Manhã", situacao="O", tipo_prog=649,
):
    return (codigo, nome, ue, dre, ano, turno, desc_turno, situacao, tipo_prog)


def _row_comp_turma(codigo_turma=12345, codigo_comp=1322, nome="PAP Rec"):
    return (codigo_turma, codigo_comp, nome)


def _row_matricula(
    aluno=99999, turma=12345, comp=1322, nome_comp="PAP Rec",
    sit=1, dt_mat=_DATA_MATRICULA, dt_sit=None,
    ano=2025, ue="000001", dre="108900", tipo_prog=649,
):
    return (aluno, turma, comp, nome_comp, sit, dt_mat, dt_sit, ano, ue, dre, tipo_prog)


class TestTipoProgramaOut(TestCase):
    def test_pap_649(self) -> None:
        obj = TipoProgramaOut.from_in(TipoProgramaIn(*_row_tipo(649)))
        self.assertEqual(obj.codigo_tipo_programa, 649)
        self.assertEqual(obj.categoria, "PAP")
        self.assertTrue(obj.ativo)

    def test_pap_650(self) -> None:
        obj = TipoProgramaOut.from_in(TipoProgramaIn(*_row_tipo(650)))
        self.assertEqual(obj.categoria, "PAP")

    def test_paee_656(self) -> None:
        obj = TipoProgramaOut.from_in(TipoProgramaIn(*_row_tipo(656, "PAEE-SRM", "PAEE SRM")))
        self.assertEqual(obj.categoria, "PAEE")

    def test_paee_657_e_658(self) -> None:
        for id_ in (657, 658):
            with self.subTest(id_=id_):
                obj = TipoProgramaOut.from_in(TipoProgramaIn(*_row_tipo(id_)))
                self.assertEqual(obj.categoria, "PAEE")

    def test_nome_usa_descricao(self) -> None:
        obj = TipoProgramaOut.from_in(TipoProgramaIn(*_row_tipo(649, "SIG", "Descrição Completa")))
        self.assertEqual(obj.nome, "Descrição Completa")

    def test_nome_fallback_sigla_se_descricao_vazia(self) -> None:
        obj = TipoProgramaOut.from_in(TipoProgramaIn(649, "SIG", ""))
        self.assertEqual(obj.nome, "SIG")

    def test_codigo_desconhecido_default_pap(self) -> None:
        obj = TipoProgramaOut.from_in(TipoProgramaIn(999, "X", "Desconhecido"))
        self.assertEqual(obj.categoria, "PAP")

    def test_nome_trimado(self) -> None:
        obj = TipoProgramaOut.from_in(TipoProgramaIn(649, "  SIG  ", "  Nome  "))
        self.assertEqual(obj.nome, "Nome")


class TestComponenteCurricularProgramaOut(TestCase):
    def test_pap_vigente_1322(self) -> None:
        obj = ComponenteCurricularProgramaOut.from_in(
            ComponenteCurricularProgramaIn(*_row_componente(1322))
        )
        self.assertEqual(obj.categoria, "PAP")
        self.assertTrue(obj.vigente)
        self.assertEqual(obj.codigo_componente_curricular, 1322)

    def test_pap_vigente_1770_1804_1805(self) -> None:
        for id_ in (1770, 1804, 1805):
            with self.subTest(id_=id_):
                obj = ComponenteCurricularProgramaOut.from_in(
                    ComponenteCurricularProgramaIn(*_row_componente(id_))
                )
                self.assertTrue(obj.vigente)
                self.assertEqual(obj.categoria, "PAP")

    def test_pap_legado_1033(self) -> None:
        obj = ComponenteCurricularProgramaOut.from_in(
            ComponenteCurricularProgramaIn(*_row_componente(1033))
        )
        self.assertEqual(obj.categoria, "PAP")
        self.assertFalse(obj.vigente)

    def test_pap_legados_restantes(self) -> None:
        for id_ in (1051, 1052, 1053, 1054):
            with self.subTest(id_=id_):
                obj = ComponenteCurricularProgramaOut.from_in(
                    ComponenteCurricularProgramaIn(*_row_componente(id_))
                )
                self.assertFalse(obj.vigente)

    def test_paee_vigente_1030(self) -> None:
        obj = ComponenteCurricularProgramaOut.from_in(
            ComponenteCurricularProgramaIn(*_row_componente(1030))
        )
        self.assertEqual(obj.categoria, "PAEE")
        self.assertTrue(obj.vigente)


class TestTurmaProgramaOut(TestCase):
    def test_campos_basicos(self) -> None:
        obj = TurmaProgramaOut.from_in(TurmaProgramaIn(*_row_turma()))
        self.assertEqual(obj.codigo_turma, 12345)
        self.assertEqual(obj.nome_turma, "TURMA PAP 1A")
        self.assertEqual(obj.codigo_ue, "000001")
        self.assertEqual(obj.codigo_dre, "108900")
        self.assertEqual(obj.ano_letivo, 2025)
        self.assertEqual(obj.situacao, "O")
        self.assertEqual(obj.codigo_tipo_programa, 649)
        self.assertEqual(obj.categoria, "PAP")

    def test_paee(self) -> None:
        obj = TurmaProgramaOut.from_in(TurmaProgramaIn(*_row_turma(tipo_prog=656)))
        self.assertEqual(obj.categoria, "PAEE")

    def test_tipo_turno_none(self) -> None:
        obj = TurmaProgramaOut.from_in(TurmaProgramaIn(*_row_turma(turno=None)))
        self.assertIsNone(obj.tipo_turno)

    def test_descricao_turno_vazia_vira_string_vazia(self) -> None:
        obj = TurmaProgramaOut.from_in(TurmaProgramaIn(*_row_turma(desc_turno="")))
        self.assertEqual(obj.descricao_turno, "")

    def test_nome_trimado(self) -> None:
        obj = TurmaProgramaOut.from_in(TurmaProgramaIn(*_row_turma(nome="  TURMA  ")))
        self.assertEqual(obj.nome_turma, "TURMA")


class TestTurmaProgramaComponenteCurricularOut(TestCase):
    def test_campos(self) -> None:
        obj = TurmaProgramaComponenteCurricularOut.from_in(
            TurmaProgramaComponenteCurricularIn(*_row_comp_turma())
        )
        self.assertEqual(obj.codigo_turma, 12345)
        self.assertEqual(obj.codigo_componente_curricular, 1322)
        self.assertEqual(obj.nome_componente_curricular, "PAP Rec")

    def test_nome_trimado(self) -> None:
        obj = TurmaProgramaComponenteCurricularOut.from_in(
            TurmaProgramaComponenteCurricularIn(12345, 1322, "  PAP Rec  ")
        )
        self.assertEqual(obj.nome_componente_curricular, "PAP Rec")


class TestMatriculaTurmaProgramaOut(TestCase):
    def test_campos_basicos(self) -> None:
        obj = MatriculaTurmaProgramaOut.from_in(MatriculaTurmaProgramaIn(*_row_matricula()))
        self.assertEqual(obj.codigo_aluno, 99999)
        self.assertEqual(obj.codigo_turma, 12345)
        self.assertEqual(obj.codigo_componente_curricular, 1322)
        self.assertEqual(obj.nome_componente_curricular, "PAP Rec")
        self.assertEqual(obj.codigo_situacao_matricula, 1)
        self.assertEqual(obj.descricao_situacao_matricula, "Ativo")
        self.assertEqual(obj.data_matricula, _DATA_MATRICULA)
        self.assertEqual(obj.ano_letivo, 2025)
        self.assertEqual(obj.codigo_ue, "000001")
        self.assertEqual(obj.codigo_dre, "108900")
        self.assertEqual(obj.categoria, "PAP")

    def test_paee(self) -> None:
        obj = MatriculaTurmaProgramaOut.from_in(
            MatriculaTurmaProgramaIn(*_row_matricula(tipo_prog=656))
        )
        self.assertEqual(obj.categoria, "PAEE")

    def test_data_situacao_none(self) -> None:
        obj = MatriculaTurmaProgramaOut.from_in(
            MatriculaTurmaProgramaIn(*_row_matricula(dt_sit=None))
        )
        self.assertIsNone(obj.data_situacao)

    def test_data_situacao_preenchida(self) -> None:
        dt = datetime.date(2025, 6, 30)
        obj = MatriculaTurmaProgramaOut.from_in(
            MatriculaTurmaProgramaIn(*_row_matricula(dt_sit=dt))
        )
        self.assertEqual(obj.data_situacao, dt)

    def test_descricao_situacao_derivada_do_codigo(self) -> None:
        """O descricao_situacao_matricula é derivado de codigo_situacao_matricula via enum."""
        obj = MatriculaTurmaProgramaOut.from_in(
            MatriculaTurmaProgramaIn(*_row_matricula(sit=5))
        )
        self.assertEqual(obj.descricao_situacao_matricula, "Concluído")


class TestTipoProgramaEOLEnum(TestCase):
    def test_categoria_pap(self) -> None:
        for id_ in (649, 650):
            with self.subTest(id_=id_):
                self.assertEqual(TipoProgramaEOL.categoria(id_), CategoriaPrograma.PAP)

    def test_categoria_paee(self) -> None:
        for id_ in (656, 657, 658):
            with self.subTest(id_=id_):
                self.assertEqual(TipoProgramaEOL.categoria(id_), CategoriaPrograma.PAEE)

    def test_categoria_desconhecido_default_pap(self) -> None:
        self.assertEqual(TipoProgramaEOL.categoria(999), CategoriaPrograma.PAP)

    def test_categoria_none_default_pap(self) -> None:
        self.assertEqual(TipoProgramaEOL.categoria(None), CategoriaPrograma.PAP)

    def test_categoria_invalido_default_pap(self) -> None:
        self.assertEqual(TipoProgramaEOL.categoria("abc"), CategoriaPrograma.PAP)

    def test_codigos_retorna_cinco(self) -> None:
        codigos = TipoProgramaEOL.codigos()
        self.assertEqual(len(codigos), 5)
        self.assertEqual(set(codigos), {649, 650, 656, 657, 658})


class TestComponenteCurricularEOLEnum(TestCase):
    def test_categoria_pap_vigentes(self) -> None:
        for id_ in (1322, 1770, 1804, 1805):
            with self.subTest(id_=id_):
                self.assertEqual(ComponenteCurricularEOL.categoria(id_), CategoriaPrograma.PAP)
                self.assertTrue(ComponenteCurricularEOL.vigente(id_))

    def test_categoria_pap_legados(self) -> None:
        for id_ in (1033, 1051, 1052, 1053, 1054):
            with self.subTest(id_=id_):
                self.assertEqual(ComponenteCurricularEOL.categoria(id_), CategoriaPrograma.PAP)
                self.assertFalse(ComponenteCurricularEOL.vigente(id_))

    def test_categoria_paee_vigente(self) -> None:
        self.assertEqual(ComponenteCurricularEOL.categoria(1030), CategoriaPrograma.PAEE)
        self.assertTrue(ComponenteCurricularEOL.vigente(1030))

    def test_vigente_desconhecido_false(self) -> None:
        self.assertFalse(ComponenteCurricularEOL.vigente(9999))

    def test_codigos_retorna_dez(self) -> None:
        codigos = ComponenteCurricularEOL.codigos()
        self.assertEqual(len(codigos), 10)


class TestSituacaoTurmaEnum(TestCase):
    def test_descricao_organizada(self) -> None:
        self.assertEqual(SituacaoTurma.get_descricao("O"), "Organizada")

    def test_descricao_nao_organizada(self) -> None:
        self.assertEqual(SituacaoTurma.get_descricao("A"), "Não Organizada")

    def test_descricao_concluida(self) -> None:
        self.assertEqual(SituacaoTurma.get_descricao("C"), "Concluída")

    def test_descricao_extinta(self) -> None:
        self.assertEqual(SituacaoTurma.get_descricao("E"), "Extinta")

    def test_descricao_none(self) -> None:
        self.assertEqual(SituacaoTurma.get_descricao(None), "Não Informada")

    def test_descricao_codigo_invalido(self) -> None:
        self.assertEqual(SituacaoTurma.get_descricao("X"), "Desconhecido")


class TestSituacaoMatriculaEnum(TestCase):
    def test_codigos_mapeados(self) -> None:
        casos = [
            (1, "Ativo"),
            (5, "Concluído"),
            (6, "Pendente de Rematrícula"),
            (10, "Rematriculado"),
            (13, "Sem continuidade"),
            (17, "Dispensado Ed. Física"),
        ]
        for codigo, esperado in casos:
            with self.subTest(codigo=codigo):
                self.assertEqual(SituacaoMatricula.get_descricao(codigo), esperado)

    def test_descricao_none(self) -> None:
        self.assertEqual(SituacaoMatricula.get_descricao(None), "Não Informada")

    def test_descricao_invalido(self) -> None:
        self.assertEqual(SituacaoMatricula.get_descricao("abc"), "Desconhecido")

    def test_descricao_fora_do_dominio(self) -> None:
        self.assertEqual(SituacaoMatricula.get_descricao(999), "Desconhecido")

    def test_aceita_string_numerica(self) -> None:
        self.assertEqual(SituacaoMatricula.get_descricao("1"), "Ativo")
