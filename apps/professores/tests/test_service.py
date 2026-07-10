"""Testes de _row_to_*, _full_refresh e EtlProfessoresService."""

import datetime
from typing import Any, cast
from unittest.mock import MagicMock, patch

from django.db.models.query import QuerySet
from django.test import TestCase
from django.utils import timezone

from apps.professores.dtos.model_in import FuncionarioUnidadeEducacionalIn
from apps.professores.models import FuncionarioUnidadeEducacional, Professor
from apps.professores.queries import (
    CARGOS_PROFESSOR,
    SQL_ATRIBUICOES_AULA,
    SQL_DISCIPLINAS_TURMAS_ATRIBUIDAS_UE,
    SQL_FUNCIONARIOS_UNIDADE_EDUCACIONAL,
    SQL_TURMAS_ATRIBUIDAS_UE,
)
from apps.professores.services import (
    EtlProfessoresService,
    _full_refresh,
    _params_cargo,
    _row_to_atribuicao_aula,
    _row_to_atribuicao_externo,
    _row_to_cargo_base,
    _row_to_cargo_sobreposto,
    _row_to_contrato_externo,
    _row_to_funcao_atividade,
    _row_to_funcionario,
    _row_to_laudo,
    _row_to_lotacao,
    _row_to_pessoa,
    _row_to_professor,
    _upsert_incremental,
)

_BulkCreateChamadas = list[
    tuple[list[FuncionarioUnidadeEducacional], dict[str, object]]
]


def _capturar_bulk_create_funcionario() -> tuple[_BulkCreateChamadas, Any]:
    """Captura bulk_create de funcionario e preserva hashes reais."""
    original_bulk_create = QuerySet.bulk_create
    chamadas: _BulkCreateChamadas = []

    def fake_bulk_create(
        queryset: QuerySet,
        objs: list[object],
        *args: object,
        **kwargs: object,
    ) -> list[object]:
        if isinstance(objs[0], FuncionarioUnidadeEducacional):
            chamadas.append(
                (cast(list[FuncionarioUnidadeEducacional], objs), kwargs)
            )
            return []
        return cast(
            list[object],
            original_bulk_create(queryset, objs, *args, **kwargs),
        )

    return chamadas, patch.object(
        QuerySet,
        "bulk_create",
        autospec=True,
        side_effect=fake_bulk_create,
    )


class EtlProfessoresServiceFiltroAnoLetivoTest(TestCase):
    """Testes do filtro de ano letivo nas consultas."""

    def test_sem_ano_letivo_remove_marcadores(self) -> None:
        """Valida consulta sem restrição quando ano não é informado."""
        srv = EtlProfessoresService(eol=MagicMock())

        sql = srv._sql_com_filtro_ano_letivo(SQL_TURMAS_ATRIBUIDAS_UE)

        self.assertNotIn("FILTRO_ANO_LETIVO_TURMAS_ATRIBUIDAS_UE", sql)
        self.assertNotIn("AnoLetivo IN (2025, 2026)", sql)
        self.assertNotIn("AnoLetivo =", sql)

    def test_ano_letivo_aplica_igualdade(self) -> None:
        """Valida filtro pelo ano informado."""
        srv = EtlProfessoresService(eol=MagicMock(), ano_letivo=2026)

        sql_turmas = srv._sql_com_filtro_ano_letivo(SQL_TURMAS_ATRIBUIDAS_UE)
        sql_disciplinas = srv._sql_com_filtro_ano_letivo(
            SQL_DISCIPLINAS_TURMAS_ATRIBUIDAS_UE
        )
        sql_atribuicoes = srv._sql_com_filtro_ano_letivo(SQL_ATRIBUICOES_AULA)

        self.assertIn("AND AnoLetivo = 2026", sql_turmas)
        self.assertIn("AND tau.AnoLetivo = 2026", sql_disciplinas)
        self.assertIn("AND aa.an_atribuicao = 2026", sql_atribuicoes)
        self.assertNotIn("AnoLetivo IN (2025, 2026)", sql_turmas)
        self.assertNotIn("AnoLetivo >= 2026", sql_turmas)


class RowToProfessorTest(TestCase):
    """Testes para a função _row_to_professor."""

    def test_campos(self) -> None:
        """Verifica que os campos do professor são extraídos corretamente."""
        row = ("012345", "ANA SILVA", "Ana", "123.456.789-00")
        r = _row_to_professor(row)
        self.assertEqual(r["codigo_rf"], "012345")
        self.assertEqual(r["nome"], "ANA SILVA")
        self.assertEqual(r["nome_social"], "Ana")
        self.assertEqual(r["cpf"], "123.456.789-00")

    def test_nome_social_none(self) -> None:
        """Verifica que nome_social None é preservado."""
        row = ("012345", "ANA SILVA", None, None)
        r = _row_to_professor(row)
        self.assertIsNone(r["nome_social"])
        self.assertIsNone(r["cpf"])

    def test_rf_stripped(self) -> None:
        """Verifica que o código RF tem espaços removidos."""
        row = ("  012345  ", "ANA SILVA", None, None)
        r = _row_to_professor(row)
        self.assertEqual(r["codigo_rf"], "012345")


class RowToCargoBaseTest(TestCase):
    """Testes para a função _row_to_cargo_base."""

    def test_campos(self) -> None:
        """Verifica que os campos do cargo base são extraídos corretamente."""
        dt = datetime.date(2020, 1, 1)
        row = (
            1001,
            "012345",
            3239,
            "PROF DE EDUC BASICA I",
            6,
            dt,
            None,
            None,
        )
        r = _row_to_cargo_base(row)
        self.assertEqual(r["id"], 1001)
        self.assertEqual(r["professor_id"], "012345")
        self.assertEqual(r["codigo_cargo"], 3239)
        self.assertEqual(r["descricao_cargo"], "PROF DE EDUC BASICA I")
        self.assertEqual(r["situacao_funcional"], 6)
        self.assertEqual(r["dt_posse"], dt)

    def test_descricao_cargo_none(self) -> None:
        """Verifica que dc_cargo None resulta em descricao_cargo None."""
        dt = datetime.date(2020, 1, 1)
        row = (1002, "012346", 3247, None, 6, dt, None, None)
        r = _row_to_cargo_base(row)
        self.assertIsNone(r["descricao_cargo"])

    def test_situacao_funcional_none(self) -> None:
        """Verifica que situacao_funcional None é preservado."""
        dt = datetime.date(2020, 1, 1)
        row = (1002, "012346", 3247, "PROF BASICA II", None, dt, None, None)
        r = _row_to_cargo_base(row)
        self.assertIsNone(r["situacao_funcional"])


class RowToLotacaoTest(TestCase):
    """Testes para a função _row_to_lotacao."""

    def test_campos(self) -> None:
        """Verifica que os campos da lotação são extraídos corretamente."""
        row = (1001, "000001", datetime.date(2020, 1, 1), None)
        r = _row_to_lotacao(row)
        self.assertEqual(r["cargo_base_id"], 1001)
        self.assertEqual(r["codigo_unidade_educacao"], "000001")
        self.assertIsNone(r["dt_fim"])


class RowToCargoSobrepostoTest(TestCase):
    """Testes para a função _row_to_cargo_sobreposto."""

    def test_campos(self) -> None:
        """Verifica que os campos do cargo sobreposto são extraídos."""
        row = (1001, 3247, "000001", datetime.date(2024, 12, 31))
        r = _row_to_cargo_sobreposto(row)
        self.assertEqual(r["cargo_base_id"], 1001)
        self.assertEqual(r["codigo_cargo"], 3247)
        self.assertEqual(r["codigo_unidade_local_servico"], "000001")


class RowToFuncaoAtividadeTest(TestCase):
    """Testes para a função _row_to_funcao_atividade."""

    def test_campos(self) -> None:
        """Verifica que os campos da função de atividade são extraídos."""
        row = (1001, "000001", datetime.date(2024, 6, 30))
        r = _row_to_funcao_atividade(row)
        self.assertEqual(r["cargo_base_id"], 1001)
        self.assertEqual(r["codigo_unidade_local_servico"], "000001")


class RowToLaudoTest(TestCase):
    """Testes para a função _row_to_laudo."""

    def test_campos(self) -> None:
        """Verifica que os campos do laudo médico são extraídos."""
        row = (1001,)
        r = _row_to_laudo(row)
        self.assertEqual(r["cargo_base_id"], 1001)


class RowToPessoaTest(TestCase):
    """Testes para a função _row_to_pessoa."""

    def test_campos(self) -> None:
        """Verifica que os campos da pessoa são extraídos corretamente."""
        row = (500, "123.456.789-00", "JOSE", None)
        r = _row_to_pessoa(row)
        self.assertEqual(r["codigo_pessoa"], 500)
        self.assertEqual(r["cpf"], "123.456.789-00")
        self.assertEqual(r["nome"], "JOSE")
        self.assertIsNone(r["nome_social"])


class RowToContratoExternoTest(TestCase):
    """Testes para a função _row_to_contrato_externo."""

    def test_campos(self) -> None:
        """Verifica que os campos do contrato externo são extraídos."""
        row = (800, 500, 10, "000001", None, None)
        r = _row_to_contrato_externo(row)
        self.assertEqual(r["codigo_contrato"], 800)
        self.assertEqual(r["pessoa_id"], 500)
        self.assertEqual(r["codigo_tipo_funcao"], 10)
        self.assertEqual(r["codigo_unidade_educacao"], "000001")


class RowToAtribuicaoAulaTest(TestCase):
    """Testes para a função _row_to_atribuicao_aula."""

    def test_campos(self) -> None:
        """Verifica que os campos da atribuição de aula são extraídos."""
        dt = datetime.date(2024, 2, 1)
        dt_inicio_turma = datetime.date(2024, 2, 5)
        row = (
            9001,
            1001,
            "000001",
            9999,
            "1A",
            None,
            100,
            10,
            "MATEMATICA",
            200,
            "1",
            2024,
            1,
            dt,
            dt_inicio_turma,
            dt,
            None,
            None,
            None,
            "108600",
            "DRE PENHA",
            "PE",
            "EMEF TESTE",
            1,
            2,
            "Fundamental",
            5,
            0,
            5,
            1,
        )
        r = _row_to_atribuicao_aula(row)
        self.assertEqual(r["id"], 9001)
        self.assertEqual(r["cargo_base_id"], 1001)
        self.assertEqual(r["codigo_turma_escola"], 9999)
        self.assertEqual(r["ano_atribuicao"], 2024)
        self.assertEqual(r["descricao_turma_escola"], "1A")
        self.assertEqual(r["descricao_componente_curricular"], "MATEMATICA")
        self.assertEqual(r["ano_escolar"], "1")
        self.assertEqual(r["codigo_etapa_ensino"], 1)
        self.assertEqual(r["dt_inicio_turma"], dt_inicio_turma)
        self.assertIsNone(r["dt_cancelamento"])
        self.assertEqual(r["codigo_dre"], "108600")
        self.assertEqual(r["nome_dre"], "DRE PENHA")
        self.assertEqual(r["abreviacao_dre"], "PE")
        self.assertEqual(r["nome_unidade_educacional"], "EMEF TESTE")
        self.assertEqual(r["codigo_tipo_escola"], 1)
        self.assertEqual(r["codigo_tipo_turma"], 2)
        self.assertEqual(r["modalidade"], "Fundamental")
        self.assertEqual(r["codigo_modalidade"], 5)
        self.assertEqual(r["semestre"], 0)
        self.assertEqual(r["duracao_turno"], 5)
        self.assertEqual(r["tipo_turno"], 1)

    def test_campos_sem_dados_de_abrangencia(self) -> None:
        """Verifica leitura da linha sem dados complementares."""
        dt = datetime.date(2024, 2, 1)
        dt_inicio_turma = datetime.date(2024, 2, 5)
        row = (
            9001,
            1001,
            "000001",
            9999,
            "1A",
            None,
            100,
            10,
            "MATEMATICA",
            200,
            "1",
            2024,
            1,
            dt,
            dt_inicio_turma,
            dt,
            None,
            None,
        )

        r = _row_to_atribuicao_aula(row)

        self.assertEqual(r["id"], 9001)
        self.assertEqual(r["codigo_turma_escola"], 9999)
        self.assertIsNone(r["dt_cancelamento"])
        self.assertIsNone(r["codigo_dre"])
        self.assertIsNone(r["codigo_tipo_turma"])


class RowToAtribuicaoExternoTest(TestCase):
    """Testes para a função _row_to_atribuicao_externo."""

    def test_campos(self) -> None:
        """Verifica que os campos da atribuição externo são extraídos."""
        dt = datetime.date(2024, 2, 1)
        dt_inicio_turma = datetime.date(2024, 2, 5)
        row = (
            9002,
            800,
            "000001",
            5555,
            "EXT",
            100,
            10,
            "PORTUGUES",
            200,
            None,
            "2",
            2024,
            1,
            dt,
            dt_inicio_turma,
            dt,
            None,
            None,
            None,
        )
        r = _row_to_atribuicao_externo(row)
        self.assertEqual(r["id"], 9002)
        self.assertEqual(r["contrato_externo_id"], 800)
        self.assertEqual(r["codigo_turma_escola"], 5555)
        self.assertEqual(r["ano_atribuicao"], 2024)
        self.assertEqual(r["descricao_turma_escola"], "EXT")
        self.assertEqual(r["descricao_componente_curricular"], "PORTUGUES")
        self.assertEqual(r["ano_escolar"], "2")
        self.assertEqual(r["codigo_etapa_ensino"], 1)
        self.assertEqual(r["dt_inicio_turma"], dt_inicio_turma)
        self.assertIsNone(r["dt_cancelamento"])

    def test_codigo_turma_escola_none(self) -> None:
        """Verifica que codigo_turma_escola None é preservado."""
        dt = datetime.date(2024, 2, 1)
        row = (
            9003,
            801,
            "000002",
            None,
            None,
            101,
            11,
            "CIENCIAS",
            201,
            None,
            "2",
            2024,
            1,
            dt,
            None,
            dt,
            None,
            None,
            None,
        )
        r = _row_to_atribuicao_externo(row)
        self.assertIsNone(r["codigo_turma_escola"])
        self.assertIsNone(r["dt_cancelamento"])

    def test_campos_sem_cancelamento(self) -> None:
        """Verifica leitura da linha sem cancelamento."""
        dt = datetime.date(2024, 2, 1)
        row = (
            9002,
            800,
            "000001",
            5555,
            "EXT",
            100,
            10,
            "PORTUGUES",
            200,
            None,
            "2",
            2024,
            1,
            dt,
            None,
            dt,
            None,
            None,
        )

        r = _row_to_atribuicao_externo(row)

        self.assertEqual(r["id"], 9002)
        self.assertIsNone(r["dt_cancelamento"])


class RowToFuncionarioTest(TestCase):
    """Testes para a funcao _row_to_funcionario."""

    def test_model_in_permite_campos_nulos(self) -> None:
        """Permite que o DTO de entrada propague nulos da origem."""
        dto = FuncionarioUnidadeEducacionalIn(
            "ANA",
            None,
            None,
            "7506988",
            "019372",
            timezone.now(),
            None,
            None,
            None,
            None,
            0,
            0,
            None,
            None,
        ).to_domain()

        self.assertIsNone(dto.data_fim)
        self.assertIsNone(dto.codigo_cargo)
        self.assertIsNone(dto.codigo_tipo_funcao_atividade)

    def test_campos_normalizados_e_hash(self) -> None:
        """Verifica normalizacao, defaults e chave SHA-256."""
        dt = datetime.datetime(2026, 2, 1, 7, 30)
        row = (
            " ANA ",
            " Ana ",
            " 123 ",
            " 7506988 ",
            " 019372 ",
            dt,
            None,
            3239,
            " PROFESSOR ",
            None,
            1,
            0,
            None,
            None,
        )

        r = _row_to_funcionario(row)

        self.assertNotIn("id", r)
        self.assertEqual(r["nome"], "ANA")
        self.assertEqual(r["nome_social"], "Ana")
        self.assertEqual(r["cpf"], "123")
        self.assertEqual(r["codigo_rf"], "7506988")
        self.assertEqual(r["codigo_ue"], "019372")
        self.assertTrue(timezone.is_aware(r["data_inicio"]))
        self.assertIsNone(r["data_fim"])
        self.assertEqual(r["codigo_cargo"], 3239)
        self.assertEqual(r["cargo"], "PROFESSOR")
        self.assertEqual(r["codigo_tipo_funcao_atividade"], 0)
        self.assertTrue(r["eh_professor"])
        self.assertFalse(r["esta_afastado"])
        self.assertEqual(r["funcao_externo"], 0)
        self.assertEqual(r["tipo_funcao_externo"], 0)

    def test_normaliza_bool_texto_e_preserva_datetime_aware(self) -> None:
        """Cobre indicadores textuais e datas ja aware."""
        dt = timezone.now()
        row = (
            "ANA",
            None,
            None,
            "7506988",
            "019372",
            dt,
            None,
            None,
            None,
            "",
            "sim",
            "false",
            "",
            "",
        )

        r = _row_to_funcionario(row)

        self.assertIs(r["data_inicio"], dt)
        self.assertIsNone(r["data_fim"])
        self.assertIsNone(r["codigo_cargo"])
        self.assertTrue(r["eh_professor"])
        self.assertFalse(r["esta_afastado"])


class ParamsCargoTest(TestCase):
    """Testes para a função _params_cargo."""

    def test_retorna_lista(self) -> None:
        """Verifica que _params_cargo retorna uma lista."""
        params = _params_cargo()
        self.assertIsInstance(params, list)
        self.assertTrue(len(params) > 0)

    def test_valores_sao_cargos_professor(self) -> None:
        """Verifica que os valores correspondem à lista CARGOS_PROFESSOR."""
        params = _params_cargo()
        self.assertEqual(params, list(CARGOS_PROFESSOR))


class FullRefreshTest(TestCase):
    """Testes para a função _full_refresh."""

    databases = ["default", "professores_db"]

    def test_lista_vazia_retorna_zero(self) -> None:
        """Verifica que _full_refresh retorna zero para lista vazia."""
        from apps.professores.models import Professor

        resultado = _full_refresh(Professor, [])
        self.assertEqual(resultado, 0)

    def test_cria_registros(self) -> None:
        """Verifica que _full_refresh cria os registros fornecidos."""
        from apps.professores.models import Professor

        objs = [Professor(codigo_rf="T01", nome="TESTE")]
        resultado = _full_refresh(Professor, objs)
        self.assertEqual(resultado, 1)
        self.assertEqual(Professor.objects.using("professores_db").count(), 1)

    def test_substitui_registros_existentes(self) -> None:
        """_full_refresh substitui completamente os registros existentes."""
        from apps.professores.models import Professor

        _full_refresh(Professor, [Professor(codigo_rf="T01", nome="ANTIGA")])
        resultado = _full_refresh(
            Professor, [Professor(codigo_rf="T02", nome="NOVA")]
        )
        self.assertEqual(resultado, 1)
        self.assertFalse(
            Professor.objects.using("professores_db")
            .filter(codigo_rf="T01")
            .exists()
        )
        self.assertTrue(
            Professor.objects.using("professores_db")
            .filter(codigo_rf="T02")
            .exists()
        )


class UpsertIncrementalTest(TestCase):
    """Testes do upsert incremental."""

    databases = ["default", "professores_db"]

    @patch("apps.professores.services.EtlAuditoriaLinha.objects.bulk_create")
    @patch("apps.professores.services.Professor.objects")
    def test_remove_chave_primaria_dos_campos_de_update(
        self,
        mock_manager: MagicMock,
        mock_hash_bulk_create: MagicMock,
    ) -> None:
        """Evita erro do Django ao atualizar conflito pela propria PK."""
        mock_manager.using.return_value.bulk_create.return_value = None
        mock_filter = MagicMock()
        mock_filter.values_list.return_value = []
        mock_manager.filter.return_value = mock_filter

        total = _upsert_incremental(
            Professor,
            "professor",
            [
                {
                    "codigo_rf": "7506988",
                    "nome": "ANA",
                    "nome_social": None,
                    "cpf": None,
                }
            ],
            ["codigo_rf", "nome", "nome_social", "cpf"],
        )

        self.assertEqual(total, 1)
        _, kwargs = mock_manager.using.return_value.bulk_create.call_args
        self.assertEqual(kwargs["unique_fields"], ["codigo_rf"])
        self.assertEqual(
            kwargs["update_fields"], ["nome", "nome_social", "cpf"]
        )
        mock_hash_bulk_create.assert_called_once()

    @patch("apps.professores.services.EtlAuditoriaLinha.objects.bulk_create")
    @patch("apps.professores.services.FuncionarioUnidadeEducacional.objects")
    def test_usa_chave_natural_composta_para_funcionario(
        self,
        mock_manager: MagicMock,
        mock_hash_bulk_create: MagicMock,
    ) -> None:
        """Permite o mesmo RF e UE com cargos distintos no upsert."""
        dt = timezone.now()
        dt_fim = dt + datetime.timedelta(days=1)
        mock_manager.using.return_value.bulk_create.return_value = None
        mock_filter = MagicMock()
        mock_filter.values_list.return_value = []
        mock_manager.filter.return_value = mock_filter

        total = _upsert_incremental(
            FuncionarioUnidadeEducacional,
            "funcionario_unidade_educacional",
            [
                {
                    "codigo_rf": "7506988",
                    "codigo_ue": "019372",
                    "codigo_cargo": 3239,
                    "codigo_tipo_funcao_atividade": 0,
                    "data_inicio": dt,
                    "data_fim": dt_fim,
                    "funcao_externo": 0,
                    "tipo_funcao_externo": 0,
                    "nome": "ANA",
                },
                {
                    "codigo_rf": "7506988",
                    "codigo_ue": "019372",
                    "codigo_cargo": 3247,
                    "codigo_tipo_funcao_atividade": 0,
                    "data_inicio": dt,
                    "data_fim": dt_fim,
                    "funcao_externo": 0,
                    "tipo_funcao_externo": 0,
                    "nome": "ANA",
                },
            ],
            [
                "codigo_rf",
                "codigo_ue",
                "codigo_cargo",
                "codigo_tipo_funcao_atividade",
                "data_inicio",
                "data_fim",
                "funcao_externo",
                "tipo_funcao_externo",
                "nome",
            ],
            [
                "codigo_rf",
                "codigo_ue",
                "codigo_cargo",
                "codigo_tipo_funcao_atividade",
                "data_inicio",
                "data_fim",
                "funcao_externo",
                "tipo_funcao_externo",
            ],
        )

        self.assertEqual(total, 2)
        _, kwargs = mock_manager.using.return_value.bulk_create.call_args
        self.assertEqual(
            kwargs["unique_fields"],
            [
                "codigo_rf",
                "codigo_ue",
                "codigo_cargo",
                "codigo_tipo_funcao_atividade",
                "data_inicio",
                "data_fim",
                "funcao_externo",
                "tipo_funcao_externo",
            ],
        )
        self.assertEqual(kwargs["update_fields"], ["nome"])
        mock_hash_bulk_create.assert_called_once()

    def test_reinsere_chave_composta_quando_destino_sumiu(self) -> None:
        """Reinsere registro quando hash existe mas destino foi removido."""
        dt = timezone.now()
        row = {
            "codigo_rf": "7506988",
            "codigo_ue": "019372",
            "codigo_cargo": 3239,
            "codigo_tipo_funcao_atividade": 0,
            "data_inicio": dt,
            "data_fim": None,
            "funcao_externo": 0,
            "tipo_funcao_externo": 0,
            "nome": "ANA",
        }
        update_fields = [
            "codigo_rf",
            "codigo_ue",
            "codigo_cargo",
            "codigo_tipo_funcao_atividade",
            "data_inicio",
            "data_fim",
            "funcao_externo",
            "tipo_funcao_externo",
            "nome",
        ]
        unique_fields = [
            "codigo_rf",
            "codigo_ue",
            "codigo_cargo",
            "codigo_tipo_funcao_atividade",
            "data_inicio",
            "data_fim",
            "funcao_externo",
            "tipo_funcao_externo",
        ]

        chamadas_bulk, mock_bulk_create = _capturar_bulk_create_funcionario()
        with mock_bulk_create:
            queryset = FuncionarioUnidadeEducacional.objects.using(
                "professores_db"
            )
            queryset.all().delete()

            _upsert_incremental(
                FuncionarioUnidadeEducacional,
                "funcionario_unidade_educacional",
                [row],
                update_fields,
                unique_fields,
            )

            total = _upsert_incremental(
                FuncionarioUnidadeEducacional,
                "funcionario_unidade_educacional",
                [row],
                update_fields,
                unique_fields,
            )

        self.assertEqual(total, 1)
        self.assertEqual(len(chamadas_bulk), 2)
        obj_reinserido = chamadas_bulk[-1][0][0]
        self.assertEqual(obj_reinserido.codigo_rf, row["codigo_rf"])
        self.assertEqual(obj_reinserido.data_fim, row["data_fim"])

    def test_mantem_funcoes_distintas_na_mesma_ue_e_cargo(self) -> None:
        """Persiste duas funcoes para o mesmo funcionario, UE e cargo."""
        base = {
            "codigo_rf": "7506988",
            "codigo_ue": "019372",
            "codigo_cargo": 3239,
            "data_inicio": timezone.now(),
            "data_fim": timezone.now(),
            "funcao_externo": 0,
            "tipo_funcao_externo": 0,
            "nome": "ANA",
        }
        rows = [
            {
                **base,
                "codigo_tipo_funcao_atividade": 0,
                "cargo": "PROFESSOR",
            },
            {
                **base,
                "codigo_tipo_funcao_atividade": 10,
                "cargo": "PROFESSOR",
            },
        ]
        update_fields = [
            "codigo_rf",
            "codigo_ue",
            "codigo_cargo",
            "codigo_tipo_funcao_atividade",
            "data_inicio",
            "data_fim",
            "funcao_externo",
            "tipo_funcao_externo",
            "nome",
            "cargo",
        ]

        unique_fields = [
            "codigo_rf",
            "codigo_ue",
            "codigo_cargo",
            "codigo_tipo_funcao_atividade",
            "data_inicio",
            "data_fim",
            "funcao_externo",
            "tipo_funcao_externo",
        ]

        chamadas_bulk, mock_bulk_create = _capturar_bulk_create_funcionario()
        with mock_bulk_create:
            total = _upsert_incremental(
                FuncionarioUnidadeEducacional,
                "funcionario_unidade_educacional",
                rows,
                update_fields,
                unique_fields,
            )

        self.assertEqual(total, 2)
        objs, kwargs = chamadas_bulk[-1]
        funcoes = {obj.codigo_tipo_funcao_atividade for obj in objs}
        self.assertEqual(funcoes, {0, 10})
        self.assertEqual(kwargs["unique_fields"], unique_fields)

    def test_mantem_funcoes_externas_distintas_na_mesma_ue(self) -> None:
        """Persiste funcoes externas distintas para o mesmo CPF e UE."""
        base = {
            "codigo_rf": "12345678900",
            "codigo_ue": "019372",
            "codigo_cargo": None,
            "codigo_tipo_funcao_atividade": 0,
            "data_inicio": timezone.now(),
            "data_fim": None,
            "nome": "ANA",
        }
        rows = [
            {
                **base,
                "funcao_externo": 101,
                "tipo_funcao_externo": 1,
            },
            {
                **base,
                "funcao_externo": 102,
                "tipo_funcao_externo": 1,
            },
        ]
        campos_chave = [
            "codigo_rf",
            "codigo_ue",
            "codigo_cargo",
            "codigo_tipo_funcao_atividade",
            "data_inicio",
            "data_fim",
            "funcao_externo",
            "tipo_funcao_externo",
        ]

        chamadas_bulk, mock_bulk_create = _capturar_bulk_create_funcionario()
        with mock_bulk_create:
            total = _upsert_incremental(
                FuncionarioUnidadeEducacional,
                "funcionario_unidade_educacional",
                rows,
                [*campos_chave, "nome"],
                campos_chave,
            )

        self.assertEqual(total, 2)
        objs, kwargs = chamadas_bulk[-1]
        funcoes = {obj.funcao_externo for obj in objs}
        self.assertEqual(funcoes, {101, 102})
        self.assertEqual(kwargs["unique_fields"], campos_chave)


_EOL_PATCH = "apps.professores.services.EOLService"
_UPSERT_PATCH = "apps.professores.services._upsert_incremental"
_FULL_REFRESH_PATCH = "apps.professores.services._full_refresh_por_lote"


class EtlProfessoresServiceFase1Test(TestCase):
    """Testes dos métodos de população da fase 1 do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    @patch(_UPSERT_PATCH, return_value=4)
    @patch(_EOL_PATCH)
    def test_popular_professores(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_professores retorna a contagem correta."""
        mock_eol.return_value.iter_query.return_value = [
            [("012345", "ANA SILVA", None, "123.456.789-00")]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_professores()
        self.assertEqual(resultado, 4)

    @patch(_UPSERT_PATCH, return_value=1)
    @patch(_EOL_PATCH)
    def test_popular_pessoas(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_pessoas retorna a contagem correta."""
        mock_eol.return_value.iter_query.return_value = [
            [(500, "123.456.789-00", "JOSE", None)]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_pessoas()
        self.assertEqual(resultado, 1)


class EtlProfessoresServiceFase2Test(TestCase):
    """Testes dos métodos de população da fase 2 do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    @patch(_UPSERT_PATCH, return_value=10)
    @patch(_EOL_PATCH)
    def test_popular_cargos_base(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_cargos_base retorna a contagem correta."""
        dt = datetime.date(2020, 1, 1)
        mock_eol.return_value.iter_query.return_value = [
            [
                (
                    1001,
                    "012345",
                    3239,
                    "PROF DE EDUC BASICA I",
                    6,
                    dt,
                    None,
                    None,
                    None,
                    "108600",
                    "DRE PENHA",
                    "PE",
                    "EMEF TESTE",
                    1,
                    2,
                    "Fundamental",
                    5,
                    0,
                    5,
                    1,
                )
            ]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_cargos_base()
        self.assertEqual(resultado, 10)

    @patch(_UPSERT_PATCH, return_value=3)
    @patch(_EOL_PATCH)
    def test_popular_contratos_externos(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_contratos_externos retorna contagem correta."""
        mock_eol.return_value.iter_query.return_value = [
            [(800, 500, 10, "000001", None, None)]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_contratos_externos()
        self.assertEqual(resultado, 3)


class EtlProfessoresServiceFase3Test(TestCase):
    """Testes dos métodos de população da fase 3 do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    @patch(_FULL_REFRESH_PATCH, return_value=5)
    @patch(_EOL_PATCH)
    def test_popular_lotacoes(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica que popular_lotacoes retorna a contagem correta."""
        srv = EtlProfessoresService()
        resultado = srv.popular_lotacoes()
        self.assertEqual(resultado, 5)

    @patch(_FULL_REFRESH_PATCH, return_value=3)
    @patch(_EOL_PATCH)
    def test_popular_cargos_sobrepostos(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica que popular_cargos_sobrepostos retorna contagem correta."""
        srv = EtlProfessoresService()
        resultado = srv.popular_cargos_sobrepostos()
        self.assertEqual(resultado, 3)

    @patch(_FULL_REFRESH_PATCH, return_value=4)
    @patch(_EOL_PATCH)
    def test_popular_funcoes_atividade(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica que popular_funcoes_atividade retorna contagem correta."""
        srv = EtlProfessoresService()
        resultado = srv.popular_funcoes_atividade()
        self.assertEqual(resultado, 4)

    @patch(_FULL_REFRESH_PATCH, return_value=1)
    @patch(_EOL_PATCH)
    def test_popular_laudos(
        self, mock_eol: MagicMock, mock_refresh: MagicMock
    ) -> None:
        """Verifica que popular_laudos retorna a contagem correta."""
        srv = EtlProfessoresService()
        resultado = srv.popular_laudos()
        self.assertEqual(resultado, 1)

    @patch(_UPSERT_PATCH, return_value=20)
    @patch(_EOL_PATCH)
    def test_popular_atribuicoes_aula(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica que popular_atribuicoes_aula retorna a contagem correta."""
        dt = datetime.date(2024, 2, 1)
        mock_eol.return_value.iter_query.return_value = [
            [
                (
                    9001,
                    1001,
                    "000001",
                    9999,
                    "1A",
                    None,
                    100,
                    10,
                    "MATEMATICA",
                    200,
                    "1",
                    2024,
                    1,
                    dt,
                    dt,
                    dt,
                    None,
                    None,
                    None,
                    "108600",
                    "DRE PENHA",
                    "PE",
                    "EMEF TESTE",
                    1,
                    2,
                    "Fundamental",
                    5,
                    0,
                    5,
                    1,
                )
            ]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_atribuicoes_aula()
        self.assertEqual(resultado, 20)

    @patch(_UPSERT_PATCH, return_value=8)
    @patch(_EOL_PATCH)
    def test_popular_atribuicoes_externo(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica popular_atribuicoes_externo retorna contagem correta."""
        dt = datetime.date(2024, 2, 1)
        mock_eol.return_value.iter_query.return_value = [
            [
                (
                    9002,
                    800,
                    "000001",
                    5555,
                    "EXT",
                    100,
                    10,
                    "PORTUGUES",
                    200,
                    None,
                    "2",
                    2024,
                    1,
                    dt,
                    dt,
                    dt,
                    None,
                    None,
                )
            ]
        ]
        srv = EtlProfessoresService()
        resultado = srv.popular_atribuicoes_externo()
        self.assertEqual(resultado, 8)


class EtlProfessoresServiceFase4Test(TestCase):
    """Testes da fase final de funcionarios."""

    databases = ["default", "professores_db"]

    @patch(_UPSERT_PATCH, return_value=2)
    @patch(_EOL_PATCH)
    def test_popular_funcionarios(
        self, mock_eol: MagicMock, mock_upsert: MagicMock
    ) -> None:
        """Verifica query, parametros e persistencia incremental."""
        dt = datetime.datetime(2026, 2, 1, 7, 30)
        mock_eol.return_value.iter_query.return_value = [
            [
                (
                    "ANA",
                    None,
                    None,
                    "7506988",
                    "019372",
                    dt,
                    None,
                    3239,
                    "PROFESSOR",
                    0,
                    1,
                    0,
                    0,
                    0,
                )
            ]
        ]

        srv = EtlProfessoresService()
        resultado = srv.popular_funcionarios()

        self.assertEqual(resultado, 2)
        mock_eol.return_value.iter_query.assert_called_once_with(
            SQL_FUNCIONARIOS_UNIDADE_EDUCACIONAL, _params_cargo()
        )
        self.assertEqual(
            mock_upsert.call_args.args[1],
            "funcionario_unidade_educacional",
        )
        self.assertEqual(
            mock_upsert.call_args.args[4],
            [
                "codigo_rf",
                "codigo_ue",
                "codigo_cargo",
                "codigo_tipo_funcao_atividade",
                "data_inicio",
                "data_fim",
                "funcao_externo",
                "tipo_funcao_externo",
            ],
        )


class EtlProfessoresServiceExecutarTest(TestCase):
    """Testes para o método executar do EtlProfessoresService."""

    databases = ["default", "professores_db"]

    def _make_service_com_populares_mockados(
        self, retorno: int = 0
    ) -> EtlProfessoresService:
        """Cria serviço com todos os métodos popular_* mockados."""
        with patch(_EOL_PATCH):
            srv = EtlProfessoresService()
        metodos_popular = [m for m in dir(srv) if m.startswith("popular_")]
        for nome in metodos_popular:
            setattr(srv, nome, MagicMock(return_value=retorno))
        return srv

    def test_executar_fase1_completa_todas_as_fases(self) -> None:
        """Verifica que executar com fase_inicial=1 completa todas as fases."""
        srv = self._make_service_com_populares_mockados(1)
        resultado = srv.executar(fase_inicial=1)
        self.assertEqual(srv.ultima_fase_concluida, 4)
        self.assertIn("professor", resultado)
        self.assertIn("atribuicao_aula", resultado)
        self.assertIn("funcionario_unidade_educacional", resultado)

    def test_executar_fase2_pula_fase1(self) -> None:
        """Verifica que executar com fase_inicial=2 pula os dados da fase 1."""
        srv = self._make_service_com_populares_mockados(1)
        resultado = srv.executar(fase_inicial=2)
        self.assertEqual(srv.ultima_fase_concluida, 4)
        self.assertNotIn("professor", resultado)
        self.assertIn("cargo_base_servidor", resultado)

    def test_executar_fase3_pula_fases_1_e_2(self) -> None:
        """Verifica que executar com fase_inicial=3 pula as fases 1 e 2."""
        srv = self._make_service_com_populares_mockados(1)
        resultado = srv.executar(fase_inicial=3)
        self.assertNotIn("professor", resultado)
        self.assertNotIn("cargo_base_servidor", resultado)
        self.assertIn("atribuicao_aula", resultado)

    def test_executar_fase4_pula_fases_anteriores(self) -> None:
        """Verifica que fase 4 executa apenas tabelas finais."""
        srv = self._make_service_com_populares_mockados(1)

        resultado = srv.executar(fase_inicial=4)

        self.assertEqual(srv.ultima_fase_concluida, 4)
        self.assertEqual(
            resultado,
            {
                "funcionario_unidade_educacional": 1,
                "turma_atribuida_ue": 1,
                "disciplina_turma_atribuida_ue": 1,
            },
        )

    def test_executar_retorna_soma_de_registros(self) -> None:
        """Verifica que executar retorna a soma de registros por tabela."""
        srv = self._make_service_com_populares_mockados(3)
        resultado = srv.executar(fase_inicial=1)
        self.assertTrue(all(v == 3 for v in resultado.values()))

    def test_iter_lotes_aplica_offset_e_callback(self) -> None:
        """Verifica offset e callback de lote na iteracao rastreada."""
        srv = self._make_service_com_populares_mockados()
        original = MagicMock(return_value=iter([["lote-1"], ["lote-2"]]))
        lotes: list[tuple[str, int]] = []
        contador = [1]

        resultado = list(
            srv._iter_lotes(
                "select 1",
                None,
                original,
                1,
                "professor",
                contador,
                lambda tabela, lote: lotes.append((tabela, lote)),
            )
        )

        self.assertEqual(resultado, [["lote-2"]])
        self.assertEqual(lotes, [("professor", 2)])

    def test_executar_com_lote_inicial_rastreia_iter_query(self) -> None:
        """Retomada por lote substitui iter_query durante a tabela."""
        srv = self._make_service_com_populares_mockados(0)
        srv.eol.iter_query = MagicMock(  # type: ignore[method-assign]
            return_value=iter([[1], [2]])
        )
        lotes: list[tuple[str, int]] = []
        tabelas: list[tuple[str, int]] = []

        def popular_professores() -> int:
            return sum(len(chunk) for chunk in srv.eol.iter_query("sql"))

        srv.popular_professores = popular_professores  # type: ignore[method-assign]

        resultado = srv.executar(
            fase_inicial=1,
            lote_inicial=1,
            on_lote=lambda tabela, lote: lotes.append((tabela, lote)),
            on_tabela_concluida=lambda tabela, linhas: tabelas.append(
                (tabela, linhas)
            ),
        )

        self.assertEqual(resultado["professor"], 1)
        self.assertIn(("professor", 2), lotes)
        self.assertIn(("professor", 1), tabelas)
        self.assertIsInstance(srv.eol.iter_query, MagicMock)

    def test_executar_pula_ate_tabela_informada(self) -> None:
        """Retomada por tabela pula ate a tabela concluida."""
        srv = self._make_service_com_populares_mockados(1)

        resultado = srv.executar(fase_inicial=1, pular_ate="professor")

        self.assertNotIn("professor", resultado)
        self.assertIn("pessoa", resultado)
