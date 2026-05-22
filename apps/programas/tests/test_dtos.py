"""Testes dos DTOs (ModelIn) do app programas — método to_domain()."""

import datetime

from django.test import TestCase

from apps.programas.dtos.model_in import (
    AlunoPapAnoLetivoIn,
    ComponenteCurricularProgramaIn,
    MatriculaTurmaProgramaIn,
    TipoProgramaIn,
    TurmaProgramaComponenteCurricularIn,
    TurmaProgramaIn,
)
from apps.programas.enums import (
    CategoriaPrograma,
    ComponenteCurricularEOL,
    SituacaoMatricula,
    TipoProgramaEOL,
)

_DATA_MATRICULA = datetime.datetime(2025, 2, 1, 11, 51, 46, 820000)


def _row_tipo(id_=649, sigla="PAP-RECUP", descricao="PAP Recuperação"):
    return (id_, sigla, descricao)


def _row_componente(id_=1322, nome="PAP Rec Aprend"):
    return (id_, nome)


def _row_turma(
    codigo=12345,
    nome="TURMA PAP 1A",
    ue="000001",
    dre="108900",
    ano=2025,
    turno=1,
    desc_turno="Manhã",
    situacao="O",
    tipo_prog=649,
    categoria="PAP",
    desc_grade=None,
):
    return (
        codigo,
        nome,
        ue,
        dre,
        ano,
        turno,
        desc_turno,
        situacao,
        tipo_prog,
        categoria,
        desc_grade,
    )


def _row_comp_turma(codigo_turma=12345, codigo_comp=1322, nome="PAP Rec"):
    return (codigo_turma, codigo_comp, nome)


def _row_matricula(
    aluno=99999,
    turma=12345,
    comp=1322,
    nome_comp="PAP Rec",
    sit=1,
    dt_mat=_DATA_MATRICULA,
    dt_sit=None,
    ano=2025,
    ue="000001",
    dre="108900",
):
    return (
        aluno,
        turma,
        comp,
        nome_comp,
        sit,
        dt_mat,
        dt_sit,
        ano,
        ue,
        dre,
    )


class TestTipoProgramaIn(TestCase):
    def test_pap_649(self) -> None:
        d = TipoProgramaIn(*_row_tipo(649)).to_domain()
        self.assertEqual(d["codigo_tipo_programa"], 649)
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)
        self.assertTrue(d["ativo"])

    def test_pap_650(self) -> None:
        d = TipoProgramaIn(*_row_tipo(650)).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)

    def test_paee_656(self) -> None:
        d = TipoProgramaIn(*_row_tipo(656, "PAEE-SRM", "PAEE SRM")).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAEE)

    def test_todos_tipos_programa_eol(self) -> None:
        for id_ in TipoProgramaEOL.codigos():
            with self.subTest(id_=id_):
                d = TipoProgramaIn(*_row_tipo(id_)).to_domain()
                self.assertEqual(d["codigo_tipo_programa"], id_)

    def test_nome_usa_descricao_quando_disponivel(self) -> None:
        d = TipoProgramaIn(
            *_row_tipo(649, "SIG", "Descrição Completa")
        ).to_domain()
        self.assertEqual(d["nome"], "Descrição Completa")

    def test_nome_cai_para_sigla_quando_descricao_vazia(self) -> None:
        d = TipoProgramaIn(649, "SIG", "").to_domain()
        self.assertEqual(d["nome"], "SIG")

    def test_categoria_outros_para_id_desconhecido(self) -> None:
        d = TipoProgramaIn(999, "X", "Desconhecido").to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.OUTROS)

    def test_categoria_pap_quando_sigla_contem_pap(self) -> None:
        d = TipoProgramaIn(700, "PAP-X", "Programa qualquer").to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)

    def test_strip_em_campos_texto(self) -> None:
        d = TipoProgramaIn(649, "  SIG  ", "  Nome  ").to_domain()
        self.assertEqual(d["nome"], "Nome")


class TestComponenteCurricularProgramaIn(TestCase):
    def test_pap_vigente_1322(self) -> None:
        d = ComponenteCurricularProgramaIn(*_row_componente(1322)).to_domain()
        self.assertEqual(d["codigo_componente_curricular"], 1322)
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)
        self.assertTrue(d["vigente"])

    def test_todos_componentes_pap_vigentes(self) -> None:
        vigentes_pap = (
            ComponenteCurricularEOL.PAP_RECUPERACAO_APRENDIZAGENS,
            ComponenteCurricularEOL.PAP_PROJETO_COLABORATIVO,
            ComponenteCurricularEOL.PAP_2ANO_ALFABETIZACAO,
            ComponenteCurricularEOL.PAP_2ANO_COLABORATIVO_ALFABETIZACAO,
        )
        for id_ in vigentes_pap:
            with self.subTest(id_=id_):
                d = ComponenteCurricularProgramaIn(
                    *_row_componente(id_)
                ).to_domain()
                self.assertTrue(d["vigente"])
                self.assertEqual(d["categoria"], CategoriaPrograma.PAP)

    def test_pap_legado_1033(self) -> None:
        d = ComponenteCurricularProgramaIn(*_row_componente(1033)).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)
        self.assertFalse(d["vigente"])

    def test_todos_componentes_pap_legados(self) -> None:
        legados_pap = (
            ComponenteCurricularEOL.PAP_LEGADO_MATEMATICA,
            ComponenteCurricularEOL.PAP_LEGADO_CIENCIAS,
            ComponenteCurricularEOL.PAP_LEGADO_GEOGRAFIA,
            ComponenteCurricularEOL.PAP_LEGADO_HISTORIA,
            ComponenteCurricularEOL.PAP_LEGADO_PORTUGUES,
        )
        for id_ in legados_pap:
            with self.subTest(id_=id_):
                d = ComponenteCurricularProgramaIn(
                    *_row_componente(id_)
                ).to_domain()
                self.assertFalse(d["vigente"])

    def test_paee_1030(self) -> None:
        d = ComponenteCurricularProgramaIn(*_row_componente(1030)).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAEE)
        self.assertTrue(d["vigente"])

    def test_componente_desconhecido_vira_outros(self) -> None:
        d = ComponenteCurricularProgramaIn(
            *_row_componente(1769, nome="POSL COMPARTILHADO")
        ).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.OUTROS)
        self.assertFalse(d["vigente"])


class TestTurmaProgramaIn(TestCase):
    def test_turma_pap_padrao(self) -> None:
        d = TurmaProgramaIn(*_row_turma()).to_domain()
        self.assertEqual(d["codigo_turma"], 12345)
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)
        self.assertEqual(d["situacao"], "O")
        self.assertEqual(d["nome_turma"], "TURMA PAP 1A")
        self.assertEqual(d["ano_letivo"], 2025)
        self.assertEqual(d["codigo_tipo_programa"], 649)

    def test_turma_paee(self) -> None:
        d = TurmaProgramaIn(*_row_turma(categoria="PAEE")).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAEE)

    def test_turno_nullable(self) -> None:
        d = TurmaProgramaIn(*_row_turma(turno=None)).to_domain()
        self.assertIsNone(d["tipo_turno"])

    def test_descricao_turno_vazia(self) -> None:
        d = TurmaProgramaIn(*_row_turma(desc_turno="")).to_domain()
        self.assertEqual(d["descricao_turno"], "")

    def test_strip_em_nome_turma(self) -> None:
        d = TurmaProgramaIn(*_row_turma(nome="  TURMA  ")).to_domain()
        self.assertEqual(d["nome_turma"], "TURMA")

    def test_codigo_tipo_programa_nullable(self) -> None:
        d = TurmaProgramaIn(*_row_turma(tipo_prog=None)).to_domain()
        self.assertIsNone(d["codigo_tipo_programa"])

    def test_descricao_grade_default_none(self) -> None:
        d = TurmaProgramaIn(*_row_turma()).to_domain()
        self.assertIsNone(d["descricao_grade"])

    def test_descricao_grade_preenchida(self) -> None:
        d = TurmaProgramaIn(
            *_row_turma(desc_grade="PAP COLABORATIVO 3 / 4 E 5 ANO")
        ).to_domain()
        self.assertEqual(
            d["descricao_grade"], "PAP COLABORATIVO 3 / 4 E 5 ANO"
        )

    def test_descricao_grade_strip(self) -> None:
        d = TurmaProgramaIn(
            *_row_turma(desc_grade="  PAP COLABORATIVO  ")
        ).to_domain()
        self.assertEqual(d["descricao_grade"], "PAP COLABORATIVO")

    def test_descricao_grade_string_vazia_vira_none(self) -> None:
        d = TurmaProgramaIn(*_row_turma(desc_grade="")).to_domain()
        self.assertIsNone(d["descricao_grade"])


class TestTurmaProgramaComponenteCurricularIn(TestCase):
    def test_basico(self) -> None:
        d = TurmaProgramaComponenteCurricularIn(*_row_comp_turma()).to_domain()
        self.assertEqual(d["codigo_turma"], 12345)
        self.assertEqual(d["codigo_componente_curricular"], 1322)
        self.assertEqual(d["nome_componente_curricular"], "PAP Rec")

    def test_strip_em_nome_componente(self) -> None:
        d = TurmaProgramaComponenteCurricularIn(
            *_row_comp_turma(nome="  PAP Rec  ")
        ).to_domain()
        self.assertEqual(d["nome_componente_curricular"], "PAP Rec")


class TestMatriculaTurmaProgramaIn(TestCase):
    def test_matricula_padrao(self) -> None:
        d = MatriculaTurmaProgramaIn(*_row_matricula()).to_domain()
        self.assertEqual(d["codigo_aluno"], 99999)
        self.assertEqual(d["codigo_turma"], 12345)
        self.assertEqual(d["codigo_componente_curricular"], 1322)
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)
        self.assertEqual(d["data_matricula"], _DATA_MATRICULA)
        self.assertEqual(
            d["descricao_situacao_matricula"],
            SituacaoMatricula.get_descricao(1),
        )

    def test_data_situacao_nullable(self) -> None:
        d = MatriculaTurmaProgramaIn(*_row_matricula(dt_sit=None)).to_domain()
        self.assertIsNone(d["data_situacao"])

    def test_situacao_concluido(self) -> None:
        d = MatriculaTurmaProgramaIn(*_row_matricula(sit=5)).to_domain()
        self.assertEqual(d["codigo_situacao_matricula"], 5)
        self.assertEqual(
            d["descricao_situacao_matricula"],
            SituacaoMatricula.get_descricao(5),
        )

    def test_categoria_paee_pelo_componente_1030(self) -> None:
        d = MatriculaTurmaProgramaIn(
            *_row_matricula(comp=1030, nome_comp="SRM")
        ).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAEE)

    def test_categoria_pap_pelo_componente(self) -> None:
        d = MatriculaTurmaProgramaIn(*_row_matricula(comp=1322)).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)

    def test_codigos_ue_dre_preservados(self) -> None:
        d = MatriculaTurmaProgramaIn(
            *_row_matricula(ue="000001", dre="108900")
        ).to_domain()
        self.assertEqual(d["codigo_ue"], "000001")
        self.assertEqual(d["codigo_dre"], "108900")


def _row_aluno_pap(
    aluno=99999,
    turma=12345,
    comp=1322,
    ano=2026,
    ue="000001",
    dre="108900",
):
    return (aluno, turma, comp, ano, ue, dre)


class TestAlunoPapAnoLetivoIn(TestCase):
    def test_to_domain_basico(self) -> None:
        d = AlunoPapAnoLetivoIn(*_row_aluno_pap()).to_domain()
        self.assertEqual(d["codigo_aluno"], 99999)
        self.assertEqual(d["codigo_turma"], 12345)
        self.assertEqual(d["codigo_componente_curricular"], 1322)
        self.assertEqual(d["ano_letivo"], 2026)
        self.assertEqual(d["codigo_ue"], "000001")
        self.assertEqual(d["codigo_dre"], "108900")

    def test_to_domain_coerce_str_to_int(self) -> None:
        d = AlunoPapAnoLetivoIn(*_row_aluno_pap(aluno="99999")).to_domain()
        self.assertEqual(d["codigo_aluno"], 99999)

    def test_to_domain_codigo_ue_e_dre_sao_string(self) -> None:
        d = AlunoPapAnoLetivoIn(*_row_aluno_pap(ue=1, dre=108900)).to_domain()
        self.assertEqual(d["codigo_ue"], "1")
        self.assertEqual(d["codigo_dre"], "108900")


class TestComponenteCurricularEOLPapVigentes(TestCase):
    """Valida os códigos PAP vigentes usados na carga."""

    def test_codigos_pap_vigentes_contem_apenas_pap_atuais(self) -> None:
        codigos = ComponenteCurricularEOL.codigos_pap_vigentes()
        esperados = {
            ComponenteCurricularEOL.PAP_RECUPERACAO_APRENDIZAGENS.value,
            ComponenteCurricularEOL.PAP_PROJETO_COLABORATIVO.value,
            ComponenteCurricularEOL.PAP_2ANO_ALFABETIZACAO.value,
            ComponenteCurricularEOL.PAP_2ANO_COLABORATIVO_ALFABETIZACAO.value,
        }
        self.assertEqual(set(codigos), esperados)

    def test_codigos_pap_vigentes_nao_inclui_paee(self) -> None:
        codigos = ComponenteCurricularEOL.codigos_pap_vigentes()
        self.assertNotIn(
            ComponenteCurricularEOL.PAEE_SALA_RECURSOS_MULTIFUNCIONAIS.value,
            codigos,
        )

    def test_codigos_pap_vigentes_nao_inclui_legados(self) -> None:
        codigos = ComponenteCurricularEOL.codigos_pap_vigentes()
        legados = {
            ComponenteCurricularEOL.PAP_LEGADO_MATEMATICA.value,
            ComponenteCurricularEOL.PAP_LEGADO_CIENCIAS.value,
            ComponenteCurricularEOL.PAP_LEGADO_GEOGRAFIA.value,
            ComponenteCurricularEOL.PAP_LEGADO_HISTORIA.value,
            ComponenteCurricularEOL.PAP_LEGADO_PORTUGUES.value,
        }
        self.assertFalse(set(codigos) & legados)
