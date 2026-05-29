"""Testes dos DTOs do app Programas — método to_domain()."""

import datetime

from django.test import TestCase
from django.utils import timezone

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
    """Monta uma linha bruta de tipo_programa."""
    return (id_, sigla, descricao)


def _row_componente(id_=1322, nome="PAP Rec Aprend"):
    """Monta uma linha bruta de componente_curricular."""
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
    """Monta uma linha bruta de turma_programa."""
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
    """Monta uma linha bruta de turma_programa_componente_curricular."""
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
    """Monta uma linha bruta de matricula_turma_programa."""
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
    """Valida a conversão de TipoProgramaIn para o domínio."""

    def test_pap_649(self) -> None:
        """Tipo 649 deve ser classificado como PAP ativo."""
        d = TipoProgramaIn(*_row_tipo(649)).to_domain()
        self.assertEqual(d["codigo_tipo_programa"], 649)
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)
        self.assertTrue(d["ativo"])

    def test_pap_650(self) -> None:
        """Tipo 650 deve ser classificado como PAP."""
        d = TipoProgramaIn(*_row_tipo(650)).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)

    def test_paee_656(self) -> None:
        """Tipo 656 com sigla PAEE-SRM deve ser classificado como PAEE."""
        d = TipoProgramaIn(*_row_tipo(656, "PAEE-SRM", "PAEE SRM")).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAEE)

    def test_todos_tipos_programa_eol(self) -> None:
        """Todos os tipos canônicos devem preservar o código de origem."""
        for id_ in TipoProgramaEOL.codigos():
            with self.subTest(id_=id_):
                d = TipoProgramaIn(*_row_tipo(id_)).to_domain()
                self.assertEqual(d["codigo_tipo_programa"], id_)

    def test_nome_usa_descricao_quando_disponivel(self) -> None:
        """Nome deve vir da descrição quando ela existir."""
        d = TipoProgramaIn(
            *_row_tipo(649, "SIG", "Descrição Completa")
        ).to_domain()
        self.assertEqual(d["nome"], "Descrição Completa")

    def test_nome_cai_para_sigla_quando_descricao_vazia(self) -> None:
        """Nome deve usar a sigla quando a descrição estiver vazia."""
        d = TipoProgramaIn(649, "SIG", "").to_domain()
        self.assertEqual(d["nome"], "SIG")

    def test_categoria_outros_para_id_desconhecido(self) -> None:
        """Tipo desconhecido sem PAP/PAEE/SRM deve ser OUTROS."""
        d = TipoProgramaIn(999, "X", "Desconhecido").to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.OUTROS)

    def test_categoria_pap_quando_sigla_contem_pap(self) -> None:
        """Sigla contendo 'PAP' deve resultar em categoria PAP."""
        d = TipoProgramaIn(700, "PAP-X", "Programa qualquer").to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)

    def test_strip_em_campos_texto(self) -> None:
        """Campos sigla e descrição devem ter espaços removidos."""
        d = TipoProgramaIn(649, "  SIG  ", "  Nome  ").to_domain()
        self.assertEqual(d["nome"], "Nome")


class TestComponenteCurricularProgramaIn(TestCase):
    """Valida a conversão de ComponenteCurricularProgramaIn para o domínio."""

    def test_pap_vigente_1322(self) -> None:
        """Componente 1322 deve ser PAP vigente."""
        d = ComponenteCurricularProgramaIn(*_row_componente(1322)).to_domain()
        self.assertEqual(d["codigo_componente_curricular"], 1322)
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)
        self.assertTrue(d["vigente"])

    def test_todos_componentes_pap_vigentes(self) -> None:
        """Componentes PAP vigentes devem ser PAP e marcados como vigentes."""
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
        """Componente 1033 deve ser PAP legado (não vigente)."""
        d = ComponenteCurricularProgramaIn(*_row_componente(1033)).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)
        self.assertFalse(d["vigente"])

    def test_todos_componentes_pap_legados(self) -> None:
        """Componentes PAP legados não devem ser marcados como vigentes."""
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
        """Componente 1030 deve ser PAEE vigente."""
        d = ComponenteCurricularProgramaIn(*_row_componente(1030)).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAEE)
        self.assertTrue(d["vigente"])

    def test_componente_desconhecido_vira_outros(self) -> None:
        """Componente fora do enum deve ser OUTROS e não vigente."""
        d = ComponenteCurricularProgramaIn(
            *_row_componente(1769, nome="POSL COMPARTILHADO")
        ).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.OUTROS)
        self.assertFalse(d["vigente"])


class TestTurmaProgramaIn(TestCase):
    """Valida a conversão de TurmaProgramaIn para o domínio."""

    def test_turma_pap_padrao(self) -> None:
        """Linha PAP padrão deve preservar todos os campos esperados."""
        d = TurmaProgramaIn(*_row_turma()).to_domain()
        self.assertEqual(d["codigo_turma"], 12345)
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)
        self.assertEqual(d["situacao"], "O")
        self.assertEqual(d["nome_turma"], "TURMA PAP 1A")
        self.assertEqual(d["ano_letivo"], 2025)
        self.assertEqual(d["codigo_tipo_programa"], 649)

    def test_turma_paee(self) -> None:
        """Categoria PAEE deve ser preservada na conversão."""
        d = TurmaProgramaIn(*_row_turma(categoria="PAEE")).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAEE)

    def test_turno_nullable(self) -> None:
        """tipo_turno deve ser None quando ausente na origem."""
        d = TurmaProgramaIn(*_row_turma(turno=None)).to_domain()
        self.assertIsNone(d["tipo_turno"])

    def test_descricao_turno_vazia(self) -> None:
        """descricao_turno vazia deve permanecer string vazia."""
        d = TurmaProgramaIn(*_row_turma(desc_turno="")).to_domain()
        self.assertEqual(d["descricao_turno"], "")

    def test_strip_em_nome_turma(self) -> None:
        """Espaços nas pontas do nome_turma devem ser removidos."""
        d = TurmaProgramaIn(*_row_turma(nome="  TURMA  ")).to_domain()
        self.assertEqual(d["nome_turma"], "TURMA")

    def test_codigo_tipo_programa_nullable(self) -> None:
        """codigo_tipo_programa deve aceitar None."""
        d = TurmaProgramaIn(*_row_turma(tipo_prog=None)).to_domain()
        self.assertIsNone(d["codigo_tipo_programa"])

    def test_descricao_grade_default_none(self) -> None:
        """descricao_grade ausente deve resultar em None."""
        d = TurmaProgramaIn(*_row_turma()).to_domain()
        self.assertIsNone(d["descricao_grade"])

    def test_descricao_grade_preenchida(self) -> None:
        """descricao_grade preenchida deve ser preservada."""
        d = TurmaProgramaIn(
            *_row_turma(desc_grade="PAP COLABORATIVO 3 / 4 E 5 ANO")
        ).to_domain()
        self.assertEqual(
            d["descricao_grade"], "PAP COLABORATIVO 3 / 4 E 5 ANO"
        )

    def test_descricao_grade_strip(self) -> None:
        """Espaços nas pontas da descricao_grade devem ser removidos."""
        d = TurmaProgramaIn(
            *_row_turma(desc_grade="  PAP COLABORATIVO  ")
        ).to_domain()
        self.assertEqual(d["descricao_grade"], "PAP COLABORATIVO")

    def test_descricao_grade_string_vazia_vira_none(self) -> None:
        """descricao_grade vazia deve ser convertida em None."""
        d = TurmaProgramaIn(*_row_turma(desc_grade="")).to_domain()
        self.assertIsNone(d["descricao_grade"])


class TestTurmaProgramaComponenteCurricularIn(TestCase):
    """Valida a conversão de TurmaProgramaComponenteCurricularIn."""

    def test_basico(self) -> None:
        """Conversão deve preservar turma, componente e nome do componente."""
        d = TurmaProgramaComponenteCurricularIn(*_row_comp_turma()).to_domain()
        self.assertEqual(d["codigo_turma"], 12345)
        self.assertEqual(d["codigo_componente_curricular"], 1322)
        self.assertEqual(d["nome_componente_curricular"], "PAP Rec")

    def test_strip_em_nome_componente(self) -> None:
        """Espaços nas pontas do nome do componente devem ser removidos."""
        d = TurmaProgramaComponenteCurricularIn(
            *_row_comp_turma(nome="  PAP Rec  ")
        ).to_domain()
        self.assertEqual(d["nome_componente_curricular"], "PAP Rec")


class TestMatriculaTurmaProgramaIn(TestCase):
    """Valida a conversão de MatriculaTurmaProgramaIn para o domínio."""

    def test_matricula_padrao(self) -> None:
        """Matrícula padrão deve preservar campos e mapear descrição da situação."""
        d = MatriculaTurmaProgramaIn(*_row_matricula()).to_domain()
        self.assertEqual(d["codigo_aluno"], 99999)
        self.assertEqual(d["codigo_turma"], 12345)
        self.assertEqual(d["codigo_componente_curricular"], 1322)
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)
        self.assertEqual(
            d["data_matricula"], timezone.make_aware(_DATA_MATRICULA)
        )
        self.assertEqual(
            d["descricao_situacao_matricula"],
            SituacaoMatricula.get_descricao(1),
        )

    def test_data_situacao_nullable(self) -> None:
        """data_situacao ausente deve resultar em None."""
        d = MatriculaTurmaProgramaIn(*_row_matricula(dt_sit=None)).to_domain()
        self.assertIsNone(d["data_situacao"])

    def test_situacao_concluido(self) -> None:
        """Situação 5 deve mapear para a descrição correspondente."""
        d = MatriculaTurmaProgramaIn(*_row_matricula(sit=5)).to_domain()
        self.assertEqual(d["codigo_situacao_matricula"], 5)
        self.assertEqual(
            d["descricao_situacao_matricula"],
            SituacaoMatricula.get_descricao(5),
        )

    def test_categoria_paee_pelo_componente_1030(self) -> None:
        """Categoria deve ser PAEE quando o componente é o de SRM."""
        d = MatriculaTurmaProgramaIn(
            *_row_matricula(comp=1030, nome_comp="SRM")
        ).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAEE)

    def test_categoria_pap_pelo_componente(self) -> None:
        """Categoria deve ser PAP quando o componente é PAP conhecido."""
        d = MatriculaTurmaProgramaIn(*_row_matricula(comp=1322)).to_domain()
        self.assertEqual(d["categoria"], CategoriaPrograma.PAP)

    def test_codigos_ue_dre_preservados(self) -> None:
        """Códigos de UE e DRE devem ser preservados como string."""
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
    """Monta uma linha bruta de aluno_pap_ano_letivo."""
    return (aluno, turma, comp, ano, ue, dre)


class TestAlunoPapAnoLetivoIn(TestCase):
    """Valida a conversão de AlunoPapAnoLetivoIn para o domínio."""

    def test_to_domain_basico(self) -> None:
        """Linha padrão deve preservar todos os campos."""
        d = AlunoPapAnoLetivoIn(*_row_aluno_pap()).to_domain()
        self.assertEqual(d["codigo_aluno"], 99999)
        self.assertEqual(d["codigo_turma"], 12345)
        self.assertEqual(d["codigo_componente_curricular"], 1322)
        self.assertEqual(d["ano_letivo"], 2026)
        self.assertEqual(d["codigo_ue"], "000001")
        self.assertEqual(d["codigo_dre"], "108900")

    def test_to_domain_coerce_str_to_int(self) -> None:
        """codigo_aluno em string deve ser convertido para inteiro."""
        d = AlunoPapAnoLetivoIn(*_row_aluno_pap(aluno="99999")).to_domain()
        self.assertEqual(d["codigo_aluno"], 99999)

    def test_to_domain_codigo_ue_e_dre_sao_string(self) -> None:
        """codigo_ue e codigo_dre devem ser sempre strings no domínio."""
        d = AlunoPapAnoLetivoIn(*_row_aluno_pap(ue=1, dre=108900)).to_domain()
        self.assertEqual(d["codigo_ue"], "1")
        self.assertEqual(d["codigo_dre"], "108900")


class TestComponenteCurricularEOLPapVigentes(TestCase):
    """Valida os códigos PAP vigentes usados na carga."""

    def test_codigos_pap_vigentes_contem_apenas_pap_atuais(self) -> None:
        """Apenas os 4 componentes PAP atuais devem estar listados."""
        codigos = ComponenteCurricularEOL.codigos_pap_vigentes()
        esperados = {
            ComponenteCurricularEOL.PAP_RECUPERACAO_APRENDIZAGENS.value,
            ComponenteCurricularEOL.PAP_PROJETO_COLABORATIVO.value,
            ComponenteCurricularEOL.PAP_2ANO_ALFABETIZACAO.value,
            ComponenteCurricularEOL.PAP_2ANO_COLABORATIVO_ALFABETIZACAO.value,
        }
        self.assertEqual(set(codigos), esperados)

    def test_codigos_pap_vigentes_nao_inclui_paee(self) -> None:
        """Componente PAEE não pode aparecer entre os PAP vigentes."""
        codigos = ComponenteCurricularEOL.codigos_pap_vigentes()
        self.assertNotIn(
            ComponenteCurricularEOL.PAEE_SALA_RECURSOS_MULTIFUNCIONAIS.value,
            codigos,
        )

    def test_codigos_pap_vigentes_nao_inclui_legados(self) -> None:
        """Componentes PAP legados não podem aparecer entre os vigentes."""
        codigos = ComponenteCurricularEOL.codigos_pap_vigentes()
        legados = {
            ComponenteCurricularEOL.PAP_LEGADO_MATEMATICA.value,
            ComponenteCurricularEOL.PAP_LEGADO_CIENCIAS.value,
            ComponenteCurricularEOL.PAP_LEGADO_GEOGRAFIA.value,
            ComponenteCurricularEOL.PAP_LEGADO_HISTORIA.value,
            ComponenteCurricularEOL.PAP_LEGADO_PORTUGUES.value,
        }
        self.assertFalse(set(codigos) & legados)
