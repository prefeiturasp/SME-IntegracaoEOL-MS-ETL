"""Testes dos DTOs de entrada do domínio Alunos."""

from datetime import date, datetime
from typing import Any

from django.test import SimpleTestCase
from django.utils import timezone

from apps.alunos.dtos.model_in import (
    AlunoIn,
    DadosAlunoAcompanhamentoEscolarIn,
    MatriculaAnoLetivoIn,
    MatriculaComponenteCurricularAnoLetivoIn,
    MatriculaIn,
    MatriculaTurmaIn,
    NecessidadeEspecialAlunoIn,
    ResponsavelAlunoIn,
    TipoNecessidadeEspecialIn,
)
from apps.alunos.enums import SituacaoMatricula
from apps.core.libs.helpers import strip_str


class StripStrTest(SimpleTestCase):
    """Testes do utilitário de saneamento de strings."""

    def test_remove_espacos(self) -> None:
        self.assertEqual(strip_str("  text  "), "text")

    def test_remove_nulo(self) -> None:
        self.assertEqual(strip_str("text\x00"), "text")

    def test_nenhum_retorna_none(self) -> None:
        self.assertIsNone(strip_str(None))

    def test_vazio_retorna_none(self) -> None:
        self.assertIsNone(strip_str(""))

    def test_aceita_inteiro(self) -> None:
        self.assertEqual(strip_str(123), "123")


class TipoNecessidadeEspecialInTest(SimpleTestCase):
    """Testes de TipoNecessidadeEspecialIn.to_domain()."""

    def test_ativo_quando_sem_cancelamento(self) -> None:
        dto = TipoNecessidadeEspecialIn(
            codigo_necessidade_especial=10,
            descricao=" NEE ",
            codigo_estado=1,
            dt_cancelamento=None,
        )
        data = dto.to_domain()
        self.assertEqual(data["descricao"], "NEE")
        self.assertTrue(data["ativo"])

    def test_inativo_quando_com_cancelamento(self) -> None:
        dto = TipoNecessidadeEspecialIn(
            codigo_necessidade_especial=10,
            descricao="NEE",
            codigo_estado=1,
            dt_cancelamento=date(2023, 1, 1),
        )
        self.assertFalse(dto.to_domain()["ativo"])


class AlunoInTest(SimpleTestCase):
    """Testes de AlunoIn.to_domain()."""

    def test_campos_saneados(self) -> None:
        dto = AlunoIn(
            codigo_aluno=1,
            nome=" João  ",
            nome_social=None,
            data_nascimento=date(2010, 1, 1),
            sexo=1,
            nacionalidade=" Brasileira ",
            nis="123",
            cpf="456",
            nome_mae=" Maria ",
            raca_cor=" Branca ",
            cns="789",
            data_atualizacao_contato=datetime(2023, 1, 1, 14, 46, 50),
            possui_deficiencia=True,
        )
        data = dto.to_domain()
        self.assertEqual(data["nome"], "João")
        self.assertEqual(data["nacionalidade"], "Brasileira")
        self.assertEqual(data["raca_cor"], "Branca")
        self.assertEqual(data["sexo"], 1)
        self.assertEqual(data["nome_mae"], "Maria")
        self.assertEqual(data["cns"], "789")
        self.assertTrue(data["possui_deficiencia"])
        contato = data["data_atualizacao_contato"]
        self.assertIsInstance(contato, datetime)
        self.assertFalse(timezone.is_naive(contato))
        self.assertEqual(
            contato.replace(tzinfo=None), datetime(2023, 1, 1, 14, 46, 50)
        )

    def test_defaults_quando_campos_vazios(self) -> None:
        dto = AlunoIn(
            codigo_aluno=1,
            nome="",
            nome_social="",
            data_nascimento=None,
            sexo=None,
            nacionalidade="",
            nis="",
            cpf="",
            raca_cor="",
            nome_mae="",
            cns="",
            data_atualizacao_contato=None,
            possui_deficiencia=False,
        )
        data = dto.to_domain()
        self.assertEqual(data["nome"], "NÃO INFORMADO")
        self.assertEqual(data["sexo"], "U")
        self.assertEqual(data["nacionalidade"], "0")
        self.assertEqual(data["raca_cor"], "NÃO INFORMADA")

    def test_converte_string_iso_com_tempo_para_date(self) -> None:
        """Celery/JSON pode converter date para string ISO com tempo."""
        dto = AlunoIn(
            codigo_aluno=1,
            nome="Teste",
            nome_social=None,
            data_nascimento="2007-07-04T09:01:00",  # type: ignore[arg-type]
            sexo=1,
            nacionalidade="BR",
            nis=None,
            cpf=None,
            raca_cor=None,
            nome_mae=None,
            cns=None,
            data_atualizacao_contato=None,
            possui_deficiencia=False,
        )
        data = dto.to_domain()
        self.assertEqual(data["data_nascimento"], date(2007, 7, 4))
        self.assertIsInstance(data["data_nascimento"], date)


class ResponsavelAlunoInTest(SimpleTestCase):
    """Testes de ResponsavelAlunoIn.to_domain()."""

    def test_mapeamento_basico(self) -> None:
        dto = ResponsavelAlunoIn(
            codigo_responsavel=100,
            codigo_aluno=1,
            tipo_responsavel=1,
            nome="Pai",
            cpf="111",
            email="pai@email.com",
            ddd_celular="11",
            numero_celular="999",
            ddd_telefone_fixo="11",
            nr_telefone_fixo="33334444",
            ddd_telefone_comercial="11",
            nr_telefone_comercial="55556666",
            autoriza_sms=1,
            data_nascimento=date(1980, 5, 20),
            nome_mae="Mae do Responsavel",
            endereco_id=10,
            numero_endereco="100",
            complemento="AP",
            bairro="Centro",
            logradouro="Rua X",
            cep=12345,
            nome_municipio="SP",
            sigla_uf="SP",
            tipo_logradouro="Rua",
            data_atualizacao_tabela=None,
            data_fim_vinculo_aluno=None,
        )
        data = dto.to_domain()
        self.assertEqual(data["codigo_responsavel"], 100)
        self.assertEqual(data["aluno_id"], 1)
        self.assertEqual(data["email"], "pai@email.com")
        self.assertEqual(data["ddd_telefone_fixo"], "11")
        self.assertEqual(data["nr_telefone_fixo"], "33334444")
        self.assertEqual(data["data_nascimento"], date(1980, 5, 20))
        self.assertEqual(data["nome_mae"], "Mae do Responsavel")

    def test_mapeamento_posicional_compatibilidade_query(self) -> None:
        dto = ResponsavelAlunoIn(
            100,
            1,
            1,
            "Pai",
            "111",
            "pai@email.com",
            date(1980, 5, 20),
            "Mae do Responsavel",
            "11",
            "999",
            "11",
            "33334444",
            "11",
            "55556666",
            1,
            10,
            "100",
            "AP",
            "Centro",
            "Rua X",
            12345,
            "SP",
            "SP",
            "Rua",
            None,
            None,
        )

        data = dto.to_domain()

        self.assertEqual(data["ddd_celular"], "11")
        self.assertEqual(data["numero_celular"], "999")
        self.assertEqual(data["nr_telefone_comercial"], "55556666")
        self.assertEqual(data["data_nascimento"], date(1980, 5, 20))
        self.assertEqual(data["nome_mae"], "Mae do Responsavel")


class NecessidadeEspecialAlunoInTest(SimpleTestCase):
    """Testes de NecessidadeEspecialAlunoIn.to_domain()."""

    def test_mapeamento_fk(self) -> None:
        dto = NecessidadeEspecialAlunoIn(
            codigo_necessidade_especial_aluno=500,
            codigo_aluno=1,
            codigo_necessidade_especial=10,
            dt_inicio=date(2020, 1, 1),
            dt_fim=None,
            codigo_tipo_recurso=10,
            descricao_tipo_recurso="NENHUM",
        )
        data = dto.to_domain()
        self.assertEqual(data["codigo_necessidade_especial_aluno"], 500)
        self.assertEqual(data["aluno_id"], 1)
        self.assertEqual(data["necessidade_especial_id"], 10)
        self.assertEqual(data["codigo_tipo_recurso"], 10)


class MatriculaInTest(SimpleTestCase):
    """Testes de MatriculaIn.to_domain()."""

    def test_situacao_mapeada_via_enum(self) -> None:
        dto = MatriculaIn(
            codigo_matricula=1000,
            codigo_aluno=1,
            codigo_ue="UE123",
            codigo_dre=" DRE01 ",
            data_situacao_matricula=date(2023, 2, 2),
            data_situacao_matricula_data_hora=datetime(2023, 2, 2, 10, 20, 30),
            ano_letivo=2023,
            codigo_situacao_matricula=1,
            origem_atual=True,
            origem_historica=False,
            data_situacao_matricula_historica=None,
        )
        data = dto.to_domain()
        self.assertEqual(data["codigo_matricula"], 1000)
        self.assertEqual(data["aluno_id"], 1)
        self.assertEqual(data["codigo_dre"], "DRE01")
        self.assertEqual(data["situacao_matricula"], "Ativo")
        self.assertFalse(
            timezone.is_naive(data["data_situacao_matricula_data_hora"])
        )

    def test_situacao_fora_do_dominio(self) -> None:
        dto = MatriculaIn(
            codigo_matricula=1001,
            codigo_aluno=2,
            codigo_ue="UE123",
            codigo_dre="DRE02",
            data_situacao_matricula=None,
            data_situacao_matricula_data_hora=None,
            ano_letivo=2023,
            codigo_situacao_matricula=99,
            origem_atual=False,
            origem_historica=True,
            data_situacao_matricula_historica=None,
        )
        data = dto.to_domain()
        self.assertEqual(data["codigo_dre"], "DRE02")
        self.assertEqual(
            data["situacao_matricula"], "Fora do domínio liberado pela PRODAM"
        )


class MatriculaTurmaInTest(SimpleTestCase):
    """Testes de MatriculaTurmaIn.to_domain()."""

    def test_mapeamento_completo(self) -> None:
        dto = MatriculaTurmaIn(
            codigo_matricula=1000,
            codigo_turma=55,
            numero_chamada=" A1 ",
            data_situacao=date(2023, 3, 3),
            data_situacao_data_hora=datetime(2023, 3, 3, 10, 20, 30),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            tipo_turno=2,
            data_atualizacao_tabela=None,
            nome_turma=" 5A ",
            codigo_ue_turma=" 100001 ",
            codigo_etapa_ensino=5,
            codigo_ciclo_ensino=2,
            descricao_etapa_ensino=" Ensino Fundamental ",
            descricao_ciclo_ensino=" Ciclo Interdisciplinar ",
            sequencia=2,
        )
        data = dto.to_domain()
        self.assertEqual(data["codigo_matricula"], 1000)
        self.assertEqual(data["codigo_turma"], 55)
        self.assertEqual(data["numero_chamada"], "A1")
        self.assertEqual(data["nome_turma"], "5A")
        self.assertEqual(data["codigo_ue_turma"], "100001")
        self.assertEqual(data["codigo_etapa_ensino"], 5)
        self.assertEqual(data["codigo_ciclo_ensino"], 2)
        self.assertEqual(
            data["descricao_etapa_ensino"],
            "Ensino Fundamental",
        )
        self.assertEqual(
            data["descricao_ciclo_ensino"],
            "Ciclo Interdisciplinar",
        )
        self.assertEqual(data["tipo_turno"], 2)
        self.assertEqual(data["sequencia"], 2)
        self.assertFalse(
            timezone.is_naive(data["data_situacao_aluno_data_hora"])
        )


class SituacaoMatriculaTest(SimpleTestCase):
    """Testes diretos do Enum SituacaoMatricula."""

    def test_get_descricao_nulo(self) -> None:
        self.assertEqual(
            SituacaoMatricula.get_descricao(None),
            "Não Informada",
        )

    def test_get_descricao_invalido(self) -> None:
        self.assertEqual(
            SituacaoMatricula.get_descricao("ABC"),
            "Fora do domínio liberado pela PRODAM",
        )

    def test_get_descricao_nao_mapeado(self) -> None:
        self.assertEqual(
            SituacaoMatricula.get_descricao(999),
            "Fora do domínio liberado pela PRODAM",
        )


class MatriculaAnoLetivoInTest(SimpleTestCase):
    """Testes de MatriculaAnoLetivoIn.to_domain()."""

    def _make(self, **kwargs: Any) -> MatriculaAnoLetivoIn:
        """Cria instância com campos padrão sobrescrevíveis via kwargs."""
        defaults: dict[str, Any] = {
            "codigo_dre": "DRE01",
            "codigo_ue": "UE01",
            "tipo_escola": 1,
            "ano_letivo": 2024,
            "codigo_modalidade": 5,
            "modalidade": "EF",
            "ordem": 3,
            "ano": "3A",
            "turma": "Turma A",
            "quantidade": 100,
        }
        defaults.update(kwargs)
        return MatriculaAnoLetivoIn(**defaults)

    def test_to_domain_completo(self) -> None:
        data = self._make().to_domain()
        self.assertEqual(data["codigo_dre"], "DRE01")
        self.assertEqual(data["codigo_ue"], "UE01")
        self.assertEqual(data["tipo_escola"], 1)
        self.assertEqual(data["ano_letivo"], 2024)
        self.assertEqual(data["codigo_modalidade"], 5)
        self.assertEqual(data["modalidade"], "EF")
        self.assertEqual(data["ordem"], 3)
        self.assertEqual(data["ano"], "3A")
        self.assertEqual(data["turma"], "Turma A")
        self.assertEqual(data["quantidade"], 100)

    def test_to_domain_campos_opcionais_nulos(self) -> None:
        data = self._make(
            codigo_modalidade=None,
            modalidade=None,
            ordem=None,
            ano=None,
            turma=None,
        ).to_domain()
        self.assertIsNone(data["codigo_modalidade"])
        self.assertIsNone(data["modalidade"])
        self.assertIsNone(data["ordem"])
        self.assertIsNone(data["ano"])
        self.assertIsNone(data["turma"])

    def test_strip_em_strings(self) -> None:
        data = self._make(
            codigo_dre=" DRE01 ",
            codigo_ue=" UE01 ",
            ano=" 3A ",
            turma=" Turma A ",
        ).to_domain()
        self.assertEqual(data["codigo_dre"], "DRE01")
        self.assertEqual(data["codigo_ue"], "UE01")
        self.assertEqual(data["ano"], "3A")
        self.assertEqual(data["turma"], "Turma A")


class MatriculaComponenteCurricularAnoLetivoInTest(SimpleTestCase):
    """Testes de MatriculaComponenteCurricularAnoLetivoIn.to_domain()."""

    def _make(self, **kwargs: Any) -> MatriculaComponenteCurricularAnoLetivoIn:
        """Cria instância com campos padrão sobrescrevíveis via kwargs."""
        defaults: dict[str, Any] = {
            "codigo_ue": "UE01",
            "codigo_dre": "DRE01",
            "ano_letivo": 2024,
            "modalidade": "EF",
            "ordem": 3,
            "componente_curricular_id": 100,
            "ano": "3A",
            "turma": "Turma A",
            "quantidade": 50,
        }
        defaults.update(kwargs)
        return MatriculaComponenteCurricularAnoLetivoIn(**defaults)

    def test_to_domain_completo(self) -> None:
        data = self._make().to_domain()
        self.assertEqual(data["codigo_ue"], "UE01")
        self.assertEqual(data["codigo_dre"], "DRE01")
        self.assertEqual(data["ano_letivo"], 2024)
        self.assertEqual(data["modalidade"], "EF")
        self.assertEqual(data["ordem"], 3)
        self.assertEqual(data["componente_curricular_id"], 100)
        self.assertEqual(data["ano"], "3A")
        self.assertEqual(data["turma"], "Turma A")
        self.assertEqual(data["quantidade"], 50)

    def test_to_domain_modalidade_nula(self) -> None:
        data = self._make(
            modalidade=None, ordem=None, ano=None, turma=None
        ).to_domain()
        self.assertIsNone(data["modalidade"])
        self.assertIsNone(data["ordem"])
        self.assertIsNone(data["ano"])
        self.assertIsNone(data["turma"])

    def test_strip_em_strings(self) -> None:
        data = self._make(
            codigo_ue=" UE01 ",
            codigo_dre=" DRE01 ",
            ano=" 3A ",
            turma=" Turma A ",
        ).to_domain()
        self.assertEqual(data["codigo_ue"], "UE01")
        self.assertEqual(data["codigo_dre"], "DRE01")
        self.assertEqual(data["ano"], "3A")
        self.assertEqual(data["turma"], "Turma A")


class DadosAlunoAcompanhamentoEscolarInTest(SimpleTestCase):
    """Testes de DadosAlunoAcompanhamentoEscolarIn.to_domain()."""

    def _make(self, **kwargs: Any) -> DadosAlunoAcompanhamentoEscolarIn:
        """Cria instância com campos padrão sobrescrevíveis via kwargs."""
        defaults: dict[str, Any] = {
            "codigo_aluno": 1001,
            "nome": "JOAO SILVA",
            "nome_social": None,
            "nome_responsavel": "MARIA SILVA",
            "cpf_responsavel": "12345678900",
            "data_nascimento": date(2010, 5, 20),
            "descricao_tipo_escola": "EMEF",
            "tipo_responsavel": 1,
            "codigo_dre": "DRE01",
            "sigla_dre": "DRE-NORTE",
            "codigo_ue": "UE01",
            "unidade_educacional": "EMEF TESTE",
            "codigo_turma": 555,
            "turma": "Turma A",
            "codigo_tipo_escola": 1,
            "situacao_matricula": "Ativo",
            "data_situacao_matricula": date(2024, 2, 1),
            "codigo_etapa_ensino": 5,
            "codigo_ciclo_ensino": 2,
            "descricao_etapa_ensino": "Ensino Fundamental",
            "descricao_ciclo_ensino": "Ciclo Interdisciplinar",
            "serie_resumida": "5A",
            "codigo_modalidade_turma": 5,
        }
        defaults.update(kwargs)
        return DadosAlunoAcompanhamentoEscolarIn(**defaults)

    def test_to_domain_completo(self) -> None:
        data = self._make().to_domain()
        self.assertEqual(data["codigo_aluno"], 1001)
        self.assertEqual(data["nome"], "JOAO SILVA")
        self.assertEqual(data["nome_responsavel"], "MARIA SILVA")
        self.assertEqual(data["cpf_responsavel"], "12345678900")
        self.assertEqual(data["data_nascimento"], date(2010, 5, 20))
        self.assertEqual(data["descricao_tipo_escola"], "EMEF")
        self.assertEqual(data["tipo_responsavel"], 1)
        self.assertEqual(data["codigo_dre"], "DRE01")
        self.assertEqual(data["codigo_ue"], "UE01")
        self.assertEqual(data["codigo_turma"], 555)
        self.assertEqual(data["situacao_matricula"], "Ativo")
        self.assertEqual(data["codigo_etapa_ensino"], 5)
        self.assertEqual(data["descricao_etapa_ensino"], "Ensino Fundamental")
        self.assertEqual(
            data["descricao_ciclo_ensino"], "Ciclo Interdisciplinar"
        )
        self.assertEqual(data["serie_resumida"], "5A")

    def test_to_domain_campos_opcionais_nulos(self) -> None:
        data = self._make(
            nome_social=None,
            nome_responsavel=None,
            cpf_responsavel=None,
            data_nascimento=None,
            tipo_responsavel=None,
            sigla_dre=None,
            data_situacao_matricula=None,
            codigo_etapa_ensino=None,
            codigo_ciclo_ensino=None,
            descricao_etapa_ensino=None,
            descricao_ciclo_ensino=None,
            serie_resumida=None,
            codigo_modalidade_turma=None,
        ).to_domain()
        self.assertIsNone(data["nome_social"])
        self.assertIsNone(data["nome_responsavel"])
        self.assertIsNone(data["cpf_responsavel"])
        self.assertIsNone(data["data_nascimento"])
        self.assertIsNone(data["tipo_responsavel"])
        self.assertIsNone(data["sigla_dre"])
        self.assertIsNone(data["codigo_etapa_ensino"])
        self.assertIsNone(data["descricao_etapa_ensino"])
        self.assertIsNone(data["serie_resumida"])

    def test_strip_em_strings(self) -> None:
        data = self._make(
            nome=" JOAO ",
            codigo_dre=" DRE01 ",
            codigo_ue=" UE01 ",
            turma=" Turma A ",
        ).to_domain()
        self.assertEqual(data["nome"], "JOAO")
        self.assertEqual(data["codigo_dre"], "DRE01")
        self.assertEqual(data["codigo_ue"], "UE01")
        self.assertEqual(data["turma"], "Turma A")
