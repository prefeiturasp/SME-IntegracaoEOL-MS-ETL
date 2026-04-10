from django.test import SimpleTestCase
from datetime import date
from apps.alunos.dtos.model_in import (
    TipoNecessidadeEspecialIn, AlunoIn, ResponsavelAlunoIn,
    NecessidadeEspecialAlunoIn, MatriculaIn, MatriculaTurmaIn
)
from apps.alunos.dtos.model_out import (
    TipoNecessidadeEspecialOut, AlunoOut, ResponsavelAlunoOut,
    NecessidadeEspecialAlunoOut, MatriculaOut, MatriculaTurmaOut,
    _strip
)

class AlunosDtosTest(SimpleTestCase):
    """Testes para cobrir DTOs e helpers de transformação."""

    def test_strip_helper(self) -> None:
        self.assertEqual(_strip("  text  "), "text")
        self.assertEqual(_strip("text\x00"), "text")
        self.assertIsNone(_strip(None))
        self.assertIsNone(_strip(""))
        self.assertEqual(_strip(123), "123")

    def test_aluno_dto(self) -> None:
        dto_in = AlunoIn(
            codigo_aluno=1, nome=" João  ", nome_social=None,
            data_nascimento=date(2010, 1, 1), sexo=1,
            nacionalidade=" Brasileira ", nis="123", cpf="456",
            raca_cor=" Branca "
        )
        data = AlunoOut.to_dict(dto_in)
        self.assertEqual(data["nome"], "João")
        self.assertEqual(data["nacionalidade"], "Brasileira")
        self.assertEqual(data["raca_cor"], "Branca")
        self.assertEqual(data["sexo"], 1)

        # Edge case: fallback defaults
        dto_empty = AlunoIn(
            codigo_aluno=1, nome="", nome_social="",
            data_nascimento=None, sexo=None,
            nacionalidade="", nis="", cpf="",
            raca_cor=""
        )
        data_empty = AlunoOut.to_dict(dto_empty)
        self.assertEqual(data_empty["nome"], "NÃO INFORMADO")
        self.assertEqual(data_empty["sexo"], "U")
        self.assertEqual(data_empty["nacionalidade"], "0")
        self.assertEqual(data_empty["raca_cor"], "NÃO INFORMADA")

    def test_tipo_nee_dto(self) -> None:
        dto_in = TipoNecessidadeEspecialIn(
            codigo_necessidade_especial=10, 
            descricao=" NEE ", 
            codigo_estado=1, 
            dt_cancelamento=None
        )
        data = TipoNecessidadeEspecialOut.to_dict(dto_in)
        self.assertEqual(data["descricao"], "NEE")
        self.assertTrue(data["ativo"])

        dto_cancel = TipoNecessidadeEspecialIn(
            codigo_necessidade_especial=10, 
            descricao="NEE", 
            codigo_estado=1, 
            dt_cancelamento=date(2023, 1, 1)
        )
        data_cancel = TipoNecessidadeEspecialOut.to_dict(dto_cancel)
        self.assertFalse(data_cancel["ativo"])

    def test_responsavel_dto(self) -> None:
        dto_in = ResponsavelAlunoIn(
            codigo_responsavel=100, codigo_aluno=1, tipo_responsavel=1,
            nome="Pai", cpf="111", email="pai@email.com",
            ddd_celular="11", numero_celular="999", autoriza_sms=1,
            logradouro="Rua X", cep=12345, data_fim_vinculo_aluno=None
        )
        data = ResponsavelAlunoOut.to_dict(dto_in)
        self.assertEqual(data["codigo_responsavel"], 100)
        self.assertEqual(data["aluno_id"], 1)
        self.assertEqual(data["email"], "pai@email.com")

    def test_nee_aluno_dto(self) -> None:
        dto_in = NecessidadeEspecialAlunoIn(
            codigo_necessidade_especial_aluno=500,
            codigo_aluno=1,
            codigo_necessidade_especial=10,
            dt_inicio=date(2020, 1, 1),
            dt_fim=None
        )
        data = NecessidadeEspecialAlunoOut.to_dict(dto_in)
        self.assertEqual(data["codigo_necessidade_especial_aluno"], 500)
        self.assertEqual(data["aluno_id"], 1)
        self.assertEqual(data["necessidade_especial_id"], 10)

    def test_matricula_dto(self) -> None:
        dto_in = MatriculaIn(
            codigo_matricula=1000, codigo_aluno=1, codigo_ue="UE123",
            data_status=date(2023, 2, 2), ano_letivo=2023,
            codigo_situacao_matricula=1, situacao_matricula=" Ativa "
        )
        data = MatriculaOut.to_dict(dto_in)
        self.assertEqual(data["codigo_matricula"], 1000)
        self.assertEqual(data["aluno_id"], 1)
        self.assertEqual(data["codigo_ue"], "UE123")
        self.assertEqual(data["situacao_matricula"], "Ativa")

    def test_matricula_turma_dto(self) -> None:
        dto_in = MatriculaTurmaIn(
            codigo_matricula=1000, codigo_turma=55,
            numero_chamada=" A1 ", data_situacao=date(2023, 3, 3)
        )
        data = MatriculaTurmaOut.to_dict(dto_in)
        self.assertEqual(data["matricula_id"], 1000)
        self.assertEqual(data["codigo_turma"], 55)
        self.assertEqual(data["numero_chamada"], "A1")
        self.assertEqual(data["data_situacao_aluno"], date(2023, 3, 3))
