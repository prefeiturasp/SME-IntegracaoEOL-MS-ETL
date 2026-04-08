"""Testes do app programas — models, DTOs e services."""

import datetime
from unittest.mock import MagicMock

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
from apps.programas.models import (
    ComponenteCurricularPrograma,
    MatriculaTurmaPrograma,
    TipoPrograma,
    TurmaPrograma,
    TurmaProgramaComponenteCurricular,
)
from apps.programas.services import (
    EtlProgramasService,
    _calcular_hash,
    _upsert_incremental,
)

# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

_DATA = datetime.date(2019, 1, 1)
_DATA_MATRICULA = datetime.date(2025, 2, 1)


def _row_tipo(id_=649, sigla="PAP-RECUP", descricao="PAP Recuperação"):
    return (id_, sigla, descricao)


def _row_componente(id_=1322, nome="PAP Rec Aprend", dt_inicio=_DATA, dt_fim=None):
    return (id_, nome, dt_inicio, dt_fim)


def _row_turma(
    codigo=12345, nome="TURMA PAP 1A", ue="000001", dre="108900",
    ano=2025, turno=1, desc_turno="Manhã", situacao="O", tipo_prog=649,
):
    return (codigo, nome, ue, dre, ano, turno, desc_turno, situacao, tipo_prog)


def _row_comp_turma(codigo_turma=12345, codigo_comp=1322, nome="PAP Rec"):
    return (codigo_turma, codigo_comp, nome)


def _row_matricula(
    aluno=99999, turma=12345, comp=1322, nome_comp="PAP Rec",
    sit=1, desc_sit="Ativo", dt_mat=_DATA_MATRICULA, dt_sit=None,
    ano=2025, ue="000001", dre="108900", tipo_prog=649,
):
    return (aluno, turma, comp, nome_comp, sit, desc_sit, dt_mat, dt_sit, ano, ue, dre, tipo_prog)


# ---------------------------------------------------------------------------
# Models — __str__
# ---------------------------------------------------------------------------


class TestTipoProgramaStr(TestCase):
    def test_str(self) -> None:
        tp = TipoPrograma(id=649, nome="PAP Recuperação", categoria="PAP")
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
            codigo_turma=12345, nome_turma="TURMA PAP 1A",
            codigo_ue="000001", codigo_dre="108900",
            ano_letivo=2025, situacao="O",
            codigo_tipo_programa=649, categoria="PAP",
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
            codigo_aluno=99999, codigo_turma=12345,
            codigo_componente_curricular=1322,
        )
        resultado = str(m)
        self.assertIn("99999", resultado)
        self.assertIn("12345", resultado)
        self.assertIn("1322", resultado)


# ---------------------------------------------------------------------------
# DTOs — TipoProgramaOut
# ---------------------------------------------------------------------------


class TestTipoProgramaOut(TestCase):
    def test_pap_649(self) -> None:
        obj = TipoProgramaOut.from_in(TipoProgramaIn(*_row_tipo(649)))
        self.assertEqual(obj.id, 649)
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


# ---------------------------------------------------------------------------
# DTOs — ComponenteCurricularProgramaOut
# ---------------------------------------------------------------------------


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
        dt_fim = datetime.date(2018, 12, 31)
        obj = ComponenteCurricularProgramaOut.from_in(
            ComponenteCurricularProgramaIn(*_row_componente(1033, dt_fim=dt_fim))
        )
        self.assertEqual(obj.categoria, "PAP")
        self.assertFalse(obj.vigente)
        self.assertEqual(obj.data_fim, dt_fim)

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

    def test_data_fim_none(self) -> None:
        obj = ComponenteCurricularProgramaOut.from_in(
            ComponenteCurricularProgramaIn(*_row_componente(1322, dt_fim=None))
        )
        self.assertIsNone(obj.data_fim)


# ---------------------------------------------------------------------------
# DTOs — TurmaProgramaOut
# ---------------------------------------------------------------------------


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

    def test_descricao_turno_vazia_vira_none(self) -> None:
        obj = TurmaProgramaOut.from_in(TurmaProgramaIn(*_row_turma(desc_turno="")))
        self.assertIsNone(obj.descricao_turno)

    def test_nome_trimado(self) -> None:
        obj = TurmaProgramaOut.from_in(TurmaProgramaIn(*_row_turma(nome="  TURMA  ")))
        self.assertEqual(obj.nome_turma, "TURMA")


# ---------------------------------------------------------------------------
# DTOs — TurmaProgramaComponenteCurricularOut
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# DTOs — MatriculaTurmaProgramaOut
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Services — _calcular_hash
# ---------------------------------------------------------------------------


class TestCalcularHash(TestCase):
    def test_retorna_sha256_de_64_chars(self) -> None:
        tp = TipoPrograma(id=649, nome="PAP Rec", categoria="PAP", ativo=True)
        h = _calcular_hash(tp, ["nome", "categoria", "ativo"])
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)

    def test_hash_muda_com_campo_alterado(self) -> None:
        t1 = TipoPrograma(id=649, nome="PAP Rec", categoria="PAP", ativo=True)
        t2 = TipoPrograma(id=649, nome="PAP Rec NOVO", categoria="PAP", ativo=True)
        campos = ["nome", "categoria", "ativo"]
        self.assertNotEqual(_calcular_hash(t1, campos), _calcular_hash(t2, campos))

    def test_hash_igual_para_mesmos_dados(self) -> None:
        t1 = TipoPrograma(id=649, nome="PAP Rec", categoria="PAP", ativo=True)
        t2 = TipoPrograma(id=649, nome="PAP Rec", categoria="PAP", ativo=True)
        campos = ["nome", "categoria", "ativo"]
        self.assertEqual(_calcular_hash(t1, campos), _calcular_hash(t2, campos))

    def test_hash_ignora_campo_nao_listado(self) -> None:
        """Campos fora da lista não afetam o hash."""
        t1 = TipoPrograma(id=649, nome="PAP", categoria="PAP", ativo=True)
        t2 = TipoPrograma(id=999, nome="PAP", categoria="PAP", ativo=False)
        self.assertEqual(_calcular_hash(t1, ["nome"]), _calcular_hash(t2, ["nome"]))


# ---------------------------------------------------------------------------
# Services — _upsert_incremental
# ---------------------------------------------------------------------------


class TestUpsertIncrementalProgramas(TestCase):
    databases = ["programas_db", "default"]

    def _make_tipo(self, id_=649, nome="PAP Rec", categoria="PAP") -> TipoPrograma:
        return TipoPrograma(id=id_, nome=nome, categoria=categoria, ativo=True)

    def _upsert_tipo(self, objs: list, nome_alt: str | None = None) -> int:
        campos = ["nome", "categoria", "ativo"]
        return _upsert_incremental(TipoPrograma, "tipo_programa", objs, campos)

    def test_lista_vazia_retorna_zero(self) -> None:
        resultado = self._upsert_tipo([])
        self.assertEqual(resultado, 0)

    def test_insere_novo_e_retorna_count(self) -> None:
        resultado = self._upsert_tipo([self._make_tipo()])
        self.assertEqual(resultado, 1)
        self.assertTrue(
            TipoPrograma.objects.using("programas_db").filter(id=649).exists()
        )

    def test_nao_reescreve_se_nao_mudou(self) -> None:
        objs = [self._make_tipo()]
        self._upsert_tipo(objs)
        resultado = self._upsert_tipo(objs)
        self.assertEqual(resultado, 0)
        self.assertEqual(TipoPrograma.objects.using("programas_db").count(), 1)

    def test_atualiza_se_dado_mudou(self) -> None:
        self._upsert_tipo([self._make_tipo(nome="PAP Rec")])
        resultado = self._upsert_tipo([self._make_tipo(nome="PAP Rec ALTERADO")])
        self.assertEqual(resultado, 1)
        tp = TipoPrograma.objects.using("programas_db").get(id=649)
        self.assertEqual(tp.nome, "PAP Rec ALTERADO")

    def test_deduplica_por_chave_mantém_ultimo(self) -> None:
        """Se a origem enviar a mesma PK duas vezes, persiste apenas o último."""
        objs = [self._make_tipo(nome="PRIMEIRO"), self._make_tipo(nome="SEGUNDO")]
        resultado = self._upsert_tipo(objs)
        self.assertEqual(resultado, 1)
        tp = TipoPrograma.objects.using("programas_db").get(id=649)
        self.assertEqual(tp.nome, "SEGUNDO")

    def test_multiplos_registros_novos(self) -> None:
        objs = [self._make_tipo(649, "PAP Rec"), self._make_tipo(650, "PAP Col", "PAP")]
        resultado = self._upsert_tipo(objs)
        self.assertEqual(resultado, 2)
        self.assertEqual(TipoPrograma.objects.using("programas_db").count(), 2)

    def test_unique_fields_compostos(self) -> None:
        """Upsert com chave composta em TurmaProgramaComponenteCurricular."""
        objs = [
            TurmaProgramaComponenteCurricular(
                codigo_turma=12345,
                codigo_componente_curricular=1322,
                nome_componente_curricular="PAP Rec",
            )
        ]
        resultado = _upsert_incremental(
            TurmaProgramaComponenteCurricular,
            "turma_programa_componente_curricular",
            objs,
            ["nome_componente_curricular"],
            unique_fields=["codigo_turma", "codigo_componente_curricular"],
        )
        self.assertEqual(resultado, 1)
        self.assertTrue(
            TurmaProgramaComponenteCurricular.objects.using("programas_db")
            .filter(codigo_turma=12345, codigo_componente_curricular=1322)
            .exists()
        )

    def test_timestamp_field_preenchido_no_insert(self) -> None:
        """atualizado_em é preenchido pelo ETL quando há alteração."""
        turma = TurmaPrograma(
            codigo_turma=12345, nome_turma="TURMA PAP",
            codigo_ue="000001", codigo_dre="108900",
            ano_letivo=2025, situacao="O",
            codigo_tipo_programa=649, categoria="PAP",
        )
        _upsert_incremental(
            TurmaPrograma, "turma_programa",
            [turma],
            ["nome_turma", "situacao", "atualizado_em"],
            unique_fields=["codigo_turma"],
            timestamp_field="atualizado_em",
        )
        salva = TurmaPrograma.objects.using("programas_db").get(codigo_turma=12345)
        self.assertIsNotNone(salva.atualizado_em)

    def test_timestamp_field_excluido_do_hash(self) -> None:
        """Segunda carga com mesmo conteúdo não deve ser contabilizada."""
        turma = TurmaPrograma(
            codigo_turma=12345, nome_turma="TURMA PAP",
            codigo_ue="000001", codigo_dre="108900",
            ano_letivo=2025, situacao="O",
            codigo_tipo_programa=649, categoria="PAP",
        )
        campos = ["nome_turma", "situacao", "atualizado_em"]
        _upsert_incremental(TurmaPrograma, "turma_programa", [turma], campos,
                            unique_fields=["codigo_turma"], timestamp_field="atualizado_em")
        resultado = _upsert_incremental(TurmaPrograma, "turma_programa", [turma], campos,
                                        unique_fields=["codigo_turma"], timestamp_field="atualizado_em")
        self.assertEqual(resultado, 0)


# ---------------------------------------------------------------------------
# Services — EtlProgramasService (fases individuais)
# ---------------------------------------------------------------------------


class TestEtlProgramasServiceInit(TestCase):
    databases = ["programas_db", "default"]

    def test_init_default_cria_eol(self) -> None:
        service = EtlProgramasService()
        self.assertIsNotNone(service.eol)
        self.assertEqual(service.ultima_fase_concluida, 0)

    def test_init_com_eol_injetado(self) -> None:
        mock_eol = MagicMock()
        service = EtlProgramasService(eol=mock_eol)
        self.assertIs(service.eol, mock_eol)


class TestEtlProgramasServiceFase1(TestCase):
    databases = ["programas_db", "default"]

    def setUp(self) -> None:
        self.mock_eol = MagicMock()
        self.service = EtlProgramasService(eol=self.mock_eol)

    def test_insere_tipo_programa(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_tipo(649)]
        resultado = self.service.popular_tipos_programa()
        self.assertEqual(resultado, 1)
        tp = TipoPrograma.objects.using("programas_db").get(id=649)
        self.assertEqual(tp.categoria, "PAP")

    def test_nao_reescreve_se_nao_mudou(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_tipo(649)]
        self.service.popular_tipos_programa()
        resultado = self.service.popular_tipos_programa()
        self.assertEqual(resultado, 0)

    def test_vazio_retorna_zero(self) -> None:
        self.mock_eol.executar_query.return_value = []
        self.assertEqual(self.service.popular_tipos_programa(), 0)

    def test_insere_multiplos_tipos(self) -> None:
        self.mock_eol.executar_query.return_value = [
            _row_tipo(649, "PAP-R", "PAP Rec"),
            _row_tipo(656, "PAEE-SRM", "PAEE SRM"),
        ]
        resultado = self.service.popular_tipos_programa()
        self.assertEqual(resultado, 2)


class TestEtlProgramasServiceFase2(TestCase):
    databases = ["programas_db", "default"]

    def setUp(self) -> None:
        self.mock_eol = MagicMock()
        self.service = EtlProgramasService(eol=self.mock_eol)

    def test_insere_componente(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_componente(1322)]
        resultado = self.service.popular_componentes_curriculares()
        self.assertEqual(resultado, 1)
        cc = ComponenteCurricularPrograma.objects.using("programas_db").get(
            codigo_componente_curricular=1322
        )
        self.assertEqual(cc.categoria, "PAP")
        self.assertTrue(cc.vigente)

    def test_nao_reescreve_se_nao_mudou(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_componente(1322)]
        self.service.popular_componentes_curriculares()
        resultado = self.service.popular_componentes_curriculares()
        self.assertEqual(resultado, 0)

    def test_insere_paee(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_componente(1030, "SRM")]
        self.service.popular_componentes_curriculares()
        cc = ComponenteCurricularPrograma.objects.using("programas_db").get(
            codigo_componente_curricular=1030
        )
        self.assertEqual(cc.categoria, "PAEE")


class TestEtlProgramasServiceFase3(TestCase):
    databases = ["programas_db", "default"]

    def setUp(self) -> None:
        self.mock_eol = MagicMock()
        self.service = EtlProgramasService(eol=self.mock_eol)

    def test_insere_turma_pap(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_turma()]
        resultado = self.service.popular_turmas_programa()
        self.assertEqual(resultado, 1)
        t = TurmaPrograma.objects.using("programas_db").get(codigo_turma=12345)
        self.assertEqual(t.categoria, "PAP")
        self.assertEqual(t.codigo_tipo_programa, 649)

    def test_insere_turma_paee(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_turma(tipo_prog=656)]
        self.service.popular_turmas_programa()
        t = TurmaPrograma.objects.using("programas_db").get(codigo_turma=12345)
        self.assertEqual(t.categoria, "PAEE")

    def test_nao_reescreve_se_nao_mudou(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_turma()]
        self.service.popular_turmas_programa()
        resultado = self.service.popular_turmas_programa()
        self.assertEqual(resultado, 0)

    def test_atualiza_situacao_e_preenche_atualizado_em(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_turma(situacao="O")]
        self.service.popular_turmas_programa()
        self.mock_eol.executar_query.return_value = [_row_turma(situacao="C")]
        resultado = self.service.popular_turmas_programa()
        self.assertEqual(resultado, 1)
        t = TurmaPrograma.objects.using("programas_db").get(codigo_turma=12345)
        self.assertEqual(t.situacao, "C")
        self.assertIsNotNone(t.atualizado_em)


class TestEtlProgramasServiceFase4(TestCase):
    databases = ["programas_db", "default"]

    def setUp(self) -> None:
        self.mock_eol = MagicMock()
        self.service = EtlProgramasService(eol=self.mock_eol)

    def test_insere_componente_turma(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_comp_turma()]
        resultado = self.service.popular_turmas_programa_componentes()
        self.assertEqual(resultado, 1)

    def test_nao_reescreve_se_nao_mudou(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_comp_turma()]
        self.service.popular_turmas_programa_componentes()
        resultado = self.service.popular_turmas_programa_componentes()
        self.assertEqual(resultado, 0)

    def test_atualiza_nome_componente(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_comp_turma(nome="PAP Rec")]
        self.service.popular_turmas_programa_componentes()
        self.mock_eol.executar_query.return_value = [_row_comp_turma(nome="PAP Rec NOVO")]
        resultado = self.service.popular_turmas_programa_componentes()
        self.assertEqual(resultado, 1)

    def test_insere_sem_turma_existente_sem_fk_fisica(self) -> None:
        """Sem FK física, deve inserir mesmo sem TurmaPrograma correspondente."""
        self.mock_eol.executar_query.return_value = [_row_comp_turma(codigo_turma=99999)]
        resultado = self.service.popular_turmas_programa_componentes()
        self.assertEqual(resultado, 1)


class TestEtlProgramasServiceFase5(TestCase):
    databases = ["programas_db", "default"]

    def setUp(self) -> None:
        self.mock_eol = MagicMock()
        self.service = EtlProgramasService(eol=self.mock_eol)

    def test_insere_matricula_pap(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_matricula()]
        resultado = self.service.popular_matriculas_turma_programa()
        self.assertEqual(resultado, 1)
        m = MatriculaTurmaPrograma.objects.using("programas_db").get(
            codigo_aluno=99999, codigo_turma=12345, codigo_componente_curricular=1322
        )
        self.assertEqual(m.categoria, "PAP")
        self.assertEqual(m.nome_componente_curricular, "PAP Rec")
        self.assertEqual(m.descricao_situacao_matricula, "Ativo")

    def test_insere_matricula_paee(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_matricula(tipo_prog=656)]
        self.service.popular_matriculas_turma_programa()
        m = MatriculaTurmaPrograma.objects.using("programas_db").get(
            codigo_aluno=99999, codigo_turma=12345, codigo_componente_curricular=1322
        )
        self.assertEqual(m.categoria, "PAEE")

    def test_nao_reescreve_se_nao_mudou(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_matricula()]
        self.service.popular_matriculas_turma_programa()
        resultado = self.service.popular_matriculas_turma_programa()
        self.assertEqual(resultado, 0)

    def test_atualiza_situacao_e_preenche_atualizado_em(self) -> None:
        self.mock_eol.executar_query.return_value = [_row_matricula(sit=1, desc_sit="Ativo")]
        self.service.popular_matriculas_turma_programa()
        self.mock_eol.executar_query.return_value = [_row_matricula(sit=5, desc_sit="Concluído")]
        resultado = self.service.popular_matriculas_turma_programa()
        self.assertEqual(resultado, 1)
        m = MatriculaTurmaPrograma.objects.using("programas_db").get(
            codigo_aluno=99999, codigo_turma=12345, codigo_componente_curricular=1322
        )
        self.assertEqual(m.codigo_situacao_matricula, 5)
        self.assertIsNotNone(m.atualizado_em)

    def test_insere_sem_turma_existente_sem_fk_fisica(self) -> None:
        """Sem FK física, deve inserir mesmo sem TurmaPrograma correspondente."""
        self.mock_eol.executar_query.return_value = [_row_matricula(turma=88888)]
        resultado = self.service.popular_matriculas_turma_programa()
        self.assertEqual(resultado, 1)

    def test_vazio_retorna_zero(self) -> None:
        self.mock_eol.executar_query.return_value = []
        self.assertEqual(self.service.popular_matriculas_turma_programa(), 0)


# ---------------------------------------------------------------------------
# Services — executar
# ---------------------------------------------------------------------------


class TestEtlProgramasServiceExecutar(TestCase):
    databases = ["programas_db", "default"]

    def _make_service_mockado(self, retorno: int = 1) -> EtlProgramasService:
        """Cria serviço com todos os métodos popular_* mockados."""
        mock_eol = MagicMock()
        srv = EtlProgramasService(eol=mock_eol)
        for nome in [m for m in dir(srv) if m.startswith("popular_")]:
            setattr(srv, nome, MagicMock(return_value=retorno))
        return srv

    def test_executar_completo_retorna_5_chaves(self) -> None:
        srv = self._make_service_mockado()
        resultado = srv.executar(fase_inicial=1)
        self.assertEqual(len(resultado), 5)
        self.assertIn("tipo_programa", resultado)
        self.assertIn("componente_curricular_programa", resultado)
        self.assertIn("turma_programa", resultado)
        self.assertIn("turma_programa_componente_curricular", resultado)
        self.assertIn("matricula_turma_programa", resultado)

    def test_executar_atualiza_ultima_fase_concluida(self) -> None:
        srv = self._make_service_mockado()
        srv.executar(fase_inicial=1)
        self.assertEqual(srv.ultima_fase_concluida, 5)

    def test_executar_fase_inicial_3_pula_1_e_2(self) -> None:
        srv = self._make_service_mockado()
        resultado = srv.executar(fase_inicial=3)
        self.assertNotIn("tipo_programa", resultado)
        self.assertNotIn("componente_curricular_programa", resultado)
        self.assertIn("turma_programa", resultado)

    def test_executar_fase_inicial_5_retorna_so_matriculas(self) -> None:
        srv = self._make_service_mockado()
        resultado = srv.executar(fase_inicial=5)
        self.assertEqual(len(resultado), 1)
        self.assertIn("matricula_turma_programa", resultado)
        self.assertEqual(srv.ultima_fase_concluida, 5)

    def test_executar_real_fluxo_completo(self) -> None:
        """Fluxo completo com banco em memória — valida integração dos 5 estágios."""
        mock_eol = MagicMock()
        mock_eol.executar_query.side_effect = [
            [_row_tipo(649)],           # Fase 1 — TipoPrograma
            [_row_componente(1322)],    # Fase 2 — ComponenteCurricularPrograma
            [_row_turma()],             # Fase 3 — TurmaPrograma
            [_row_comp_turma()],        # Fase 4 — TurmaProgramaComponenteCurricular
            [_row_matricula()],         # Fase 5 — MatriculaTurmaPrograma
        ]
        srv = EtlProgramasService(eol=mock_eol)
        resultado = srv.executar()

        self.assertEqual(resultado["tipo_programa"], 1)
        self.assertEqual(resultado["componente_curricular_programa"], 1)
        self.assertEqual(resultado["turma_programa"], 1)
        self.assertEqual(resultado["turma_programa_componente_curricular"], 1)
        self.assertEqual(resultado["matricula_turma_programa"], 1)
        self.assertEqual(srv.ultima_fase_concluida, 5)

        # Valida que os dados foram persistidos com os campos desnormalizados
        self.assertEqual(
            TurmaPrograma.objects.using("programas_db").get(codigo_turma=12345).categoria,
            "PAP",
        )
        self.assertEqual(
            MatriculaTurmaPrograma.objects.using("programas_db").get(
                codigo_aluno=99999
            ).categoria,
            "PAP",
        )

    def test_executar_segunda_vez_retorna_zero_alteracoes(self) -> None:
        """Segunda execução com mesmos dados não deve gerar alterações."""
        mock_eol = MagicMock()
        rows = [
            [_row_tipo(649)],
            [_row_componente(1322)],
            [_row_turma()],
            [_row_comp_turma()],
            [_row_matricula()],
        ]
        mock_eol.executar_query.side_effect = rows[:]
        srv = EtlProgramasService(eol=mock_eol)
        srv.executar()

        mock_eol.executar_query.side_effect = rows[:]
        resultado = srv.executar()

        self.assertTrue(all(v == 0 for v in resultado.values()))
