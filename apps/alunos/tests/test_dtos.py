"""Testes dos DTOs de entrada do domínio Alunos."""

from datetime import date, datetime

from django.test import SimpleTestCase

from apps.alunos.dtos.model_in import (
    AlunoIn,
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
            raca_cor=" Branca ",
            nome_mae=" Maria ",
            cns="789",
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
            possui_deficiencia=None,
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
            data_nascimento="2007-07-04T09:01:00",  # String com tempo
            sexo=1,
            nacionalidade="BR",
            nis=None,
            cpf=None,
            raca_cor=None,
            nome_mae=None,
            cns=None,
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
            autoriza_sms=1,
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
            data_situacao_matricula=date(2023, 2, 2),
            data_situacao_matricula_data_hora=datetime(2023, 2, 2, 10, 20, 30),
            ano_letivo=2023,
            codigo_situacao_matricula=1,
            origem_atual=True,
        )
        data = dto.to_domain()
        self.assertEqual(data["codigo_matricula"], 1000)
        self.assertEqual(data["aluno_id"], 1)
        self.assertEqual(data["situacao_matricula"], "Ativo")

    def test_situacao_fora_do_dominio(self) -> None:
        dto = MatriculaIn(
            codigo_matricula=1001,
            codigo_aluno=2,
            codigo_ue="UE123",
            data_situacao_matricula=None,
            data_situacao_matricula_data_hora=None,
            ano_letivo=2023,
            codigo_situacao_matricula=99,
            origem_atual=False,
        )
        data = dto.to_domain()
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
            data_atualizacao_tabela=None,
        )
        data = dto.to_domain()
        self.assertEqual(data["codigo_matricula"], 1000)
        self.assertEqual(data["codigo_turma"], 55)
        self.assertEqual(data["numero_chamada"], "A1")
        self.assertEqual(
            data["data_situacao_aluno_data_hora"],
            datetime(2023, 3, 3, 10, 20, 30),
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
