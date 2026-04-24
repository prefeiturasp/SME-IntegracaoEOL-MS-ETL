from datetime import datetime
from queue import Empty
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from apps.core.libs.base_etl_service import PhaseConfig, PipelineMetrics
from apps.pedagogico.dtos.model_in import (
    AtribuicaoTerritorioSaberIn,
    RegenciaComponenteCurricularIn,
)
from apps.pedagogico.queries import SQL_COMPONENTE_CURRICULAR_REGENCIA
from apps.pedagogico.services import (
    _AGRUPAMENTO_ID_INICIAL,
    EtlPedagogicoService,
    _agrupar,
    _build_a3_index,
    _chave_grupo,
    _cod_agrupamento,
    _planejamento_regencia,
)


class TestPedagogicoService(TestCase):
    """Testes para ``EtlPedagogicoService`` e helpers do domínio."""

    def setUp(self) -> None:
        self.mock_eol = MagicMock()
        self.service = EtlPedagogicoService(
            db_alias="default",
            eol=self.mock_eol,
            id_execucao=uuid4(),
        )

    def test_phase_config_e_imutavel(self) -> None:
        config = PhaseConfig(
            nome="teste",
            sql="SELECT 1",
            table_name="tb",
            model_class=None,
            dto_in=None,
            dto_out=None,
            pk_field="id",
            update_fields=("f1",),
            unique_fields=("id",),
        )
        with self.assertRaises(AttributeError):
            config.nome = "mudar"  # type: ignore[misc]

    def test_fases_contem_6_configs_esperados(self) -> None:
        self.assertEqual(len(self.service._fases), 6)
        self.assertEqual(
            [fase.nome for fase in self.service._fases],
            [
                "componente_curricular",
                "componente_por_turma",
                "agrupamento_territorio_saber",
                "componente_regencia",
                "dados_aula_turma",
                "componente_por_ano_letivo",
            ],
        )

    def test_build_a3_index_separa_exact_e_fallback(self) -> None:
        exact, fallback = _build_a3_index(
            [
                RegenciaComponenteCurricularIn(100, 6, "7"),
                RegenciaComponenteCurricularIn(200, None, None),
            ]
        )

        self.assertIn((100, 6, "7"), exact)
        self.assertIn(200, fallback)

    def test_planejamento_regencia_considera_exact_e_fallback(self) -> None:
        exact = {(100, 6, "7")}
        fallback = {200}

        self.assertTrue(_planejamento_regencia(100, 6, "7", exact, fallback))
        self.assertTrue(_planejamento_regencia(200, 1, "1", exact, fallback))
        self.assertFalse(_planejamento_regencia(300, 1, "1", exact, fallback))

    def test_criar_transform_componente_curricular_retorna_tripla(
        self,
    ) -> None:
        config = self.service._fases[0]
        transform = self.service._criar_transform(config)

        result = transform((100, " Arte "))
        assert result is not None
        pk, hash_val, obj = result

        self.assertEqual(pk, "100")
        self.assertEqual(len(hash_val), 64)
        self.assertEqual(obj.descricao, "Arte")

    def test_criar_transform_componente_por_turma_aplica_flags_do_sql(self) -> None:
        self.service._exact = {(513, 6, "7")}
        config = self.service._fases[1]
        transform = self.service._criar_transform(config)

        result = transform(
            (513, " Inglês ", 1, 1, 1, 6, "7", 2025, "T1", "RF1", 0)
        )
        assert result is not None
        pk, _, obj = result

        self.assertEqual(pk, "513-T1-RF1")
        self.assertTrue(obj.regencia)
        self.assertTrue(obj.territorio_saber)
        self.assertTrue(obj.planejamento_regencia)
        self.assertEqual(obj.codigo_componente_curricular_pai, 512)

    def test_criar_transform_comp_por_turma_pula_linha_sem_codigo_ou_turma(
        self,
    ) -> None:
        config = self.service._fases[1]
        transform = self.service._criar_transform(config)

        self.assertIsNone(
            transform((None, " Inglês ", 1, 1, 1, 6, "7", 2025, "T1", "RF1", 0))
        )
        self.assertIsNone(
            transform((513, " Inglês ", 1, 1, 1, 6, "7", 2025, None, "RF1", 0))
        )

    def test_criar_transform_componente_regencia_gera_pk_composta(
        self,
    ) -> None:
        self.service._fallback = {200}
        config = self.service._fases[3]
        transform = self.service._criar_transform(config)

        result = transform(
            (
                200,
                " Ciências ",
                "5",
                2025,
                "T2",
                2,
                5,
                "RF9",
                10,
                20,
                "Território",
                "Experiência",
                "2025-02-01T10:00:00",
                2025,
                None,
                0,
                "2025-12-01T10:00:00",
                34,
            )
        )
        assert result is not None
        pk, _, obj = result

        self.assertEqual(pk, "200-T2-RF9-2025")
        self.assertTrue(obj.componente_planejamento_regencia)
        self.assertTrue(timezone.is_aware(obj.inicio_atribuicao))

    def test_criar_transform_comp_por_ano_letivo_ignora_registro_sem_chave(
        self,
    ) -> None:
        config = self.service._fases[5]
        transform = self.service._criar_transform(config)

        self.assertIsNone(transform((None, "Desc", "1", "1 ano", 1, 5, 2025)))
        self.assertIsNone(transform((100, "Desc", "1", "1 ano", 1, 5, None)))

    @patch.object(EtlPedagogicoService, "sync_batch", return_value=(1, 1))
    def test_processar_batch_filtra_nones_antes_do_sync_batch(
        self, mock_sync: MagicMock
    ) -> None:
        config = self.service._fases[1]

        escritos, ignorados = self.service._processar_batch(
            config=config,
            chunk=[
                (None, "Inválido", 0, 0, 1, 6, "7", 2025, "T1", "RF1", 0),
                (513, " Inglês ", 1, 0, 1, 6, "7", 2025, "T1", "RF1", 0),
            ],
            transform=self.service._criar_transform(config),
            batch_num=0,
        )

        self.assertEqual((escritos, ignorados), (1, 1))
        processed_data = mock_sync.call_args.args[0]
        self.assertEqual(len(processed_data), 1)
        self.assertEqual(processed_data[0][0], "513-T1-RF1")

    def test_anos_letivos_usa_cache_por_instancia(self) -> None:
        self.mock_eol.iter_query.return_value = [[(2024,), (2025,)]]

        anos_1 = self.service._anos_letivos()
        anos_2 = self.service._anos_letivos()

        self.assertEqual(anos_1, [2024, 2025])
        self.assertEqual(anos_2, [2024, 2025])
        self.mock_eol.iter_query.assert_called_once()

    @patch.object(EtlPedagogicoService, "sync_batch")
    def test_executar_agrupamentos_escreve_duas_tabelas(
        self, mock_sync: MagicMock
    ) -> None:
        config = self.service._fases[2]
        self.mock_eol.iter_query.return_value = [
            [
                (
                    100,
                    "T1",
                    2025,
                    "RF1",
                    10,
                    20,
                    "Território",
                    "Experiência",
                    "2025-02-01T10:00:00",
                    None,
                    None,
                    None,
                    0,
                ),
                (
                    101,
                    "T1",
                    2025,
                    "RF1",
                    10,
                    20,
                    "Território",
                    "Experiência",
                    "2025-02-01T10:00:00",
                    None,
                    None,
                    None,
                    0,
                ),
            ]
        ]
        mock_sync.return_value = (1, 0)

        metrics = self.service._executar_agrupamentos(config)

        self.assertEqual(metrics.total_lidos, 2)
        self.assertEqual(metrics.total_escritos, 1)
        self.assertEqual(self.service._total_itens_agrupamento, 1)
        self.assertEqual(
            [call.args[1]["table_name"] for call in mock_sync.call_args_list],
            [
                "agrupamento_atribuicao_territorio_saber",
                "componente_curricular_agrupamento",
            ],
        )

    def test_agrupar_descarta_grupos_com_apenas_um_componente(self) -> None:
        agrupamentos, itens = _agrupar(
            [
                MagicMock(
                    codigo_componente_curricular=100,
                    codigo_turma="T1",
                    ano_letivo=2025,
                    rf_professor="RF1",
                    codigo_territorio_saber=10,
                    codigo_experiencia_pedagogica=20,
                    descricao_territorio_saber="Território",
                    descricao_experiencia_pedagogica="Experiência",
                    data_atribuicao=datetime(2025, 2, 1, 10, 0, 0),
                    data_disponibilizacao=None,
                    codigo_motivo_disponibilizacao=None,
                    data_fim_turma=None,
                )
            ],
            timezone.now(),
        )

        self.assertEqual(agrupamentos, [])
        self.assertEqual(itens, [])

    def test_executar_preenche_duas_chaves_na_fase_3(self) -> None:
        with (
            patch.object(self.service, "_carregar_lookups") as mock_lookups,
            patch.object(self.service, "_executar_fase") as mock_fase,
            patch.object(self.service, "_registrar_auditoria_fase"),
        ):
            mock_fase.return_value = PipelineMetrics(total_escritos=10)
            self.service._total_itens_agrupamento = 7

            resultado = self.service.executar(fase_inicial=3)

        self.assertTrue(mock_lookups.called)
        self.assertEqual(
            resultado["agrupamento_atribuicao_territorio_saber"], 10
        )
        self.assertEqual(resultado["componente_curricular_agrupamento"], 7)
        self.assertIn("dados_aula_turma", resultado)
        self.assertEqual(mock_fase.call_count, 4)

    # ------------------------------------------------------------------
    # Testes para os ajustes do commit feat(144838)
    # ------------------------------------------------------------------

    def test_sql_comp_curricular_regencia_filtra_territorio_nao_utilizado(
        self,
    ) -> None:
        """Ambas as partes da UNION devem excluir cd_territorio_saber = 1."""
        ocorrencias = SQL_COMPONENTE_CURRICULAR_REGENCIA.count(
            "cd_territorio_saber <> 1"
        )
        self.assertEqual(
            ocorrencias,
            2,
            "Esperado filtro em ambas as partes da UNION (SME + Externos)",
        )

    def test_cod_agrupamento_sempre_maior_ou_igual_a_800000(self) -> None:
        """ID de agrupamento não pode colidir com IDs reais de comp EOL."""
        casos = [
            ("T1", 10, 20, "RF1", datetime(2025, 2, 1), [100, 200]),
            ("T2", 5, 3, None, None, [1, 2, 3]),
            ("T999", 0, 0, "RF99", datetime(2024, 1, 1), [799999]),
        ]
        for args in casos:
            with self.subTest(args=args):
                resultado = _cod_agrupamento(*args)
                self.assertGreaterEqual(resultado, _AGRUPAMENTO_ID_INICIAL)

    def test_cod_agrupamento_deterministico(self) -> None:
        """Mesma chave natural deve gerar sempre o mesmo ID."""
        args = ("T1", 10, 20, "RF1", datetime(2025, 2, 1), [100, 200])
        self.assertEqual(_cod_agrupamento(*args), _cod_agrupamento(*args))

    def test_chave_grupo_normaliza_data_disponibilizacao_para_date(
        self,
    ) -> None:
        """Deve ser normalizada para .date() na chave de agr."""
        row_com_hora = MagicMock(spec=AtribuicaoTerritorioSaberIn)
        row_com_hora.codigo_turma = "T1"
        row_com_hora.codigo_territorio_saber = 10
        row_com_hora.codigo_experiencia_pedagogica = 20
        row_com_hora.rf_professor = "RF1"
        row_com_hora.data_atribuicao = datetime(2025, 2, 1)
        row_com_hora.data_disponibilizacao = datetime(2025, 6, 30, 14, 59, 59)

        row_sem_hora = MagicMock(spec=AtribuicaoTerritorioSaberIn)
        row_sem_hora.codigo_turma = "T1"
        row_sem_hora.codigo_territorio_saber = 10
        row_sem_hora.codigo_experiencia_pedagogica = 20
        row_sem_hora.rf_professor = "RF1"
        row_sem_hora.data_atribuicao = datetime(2025, 2, 1)
        row_sem_hora.data_disponibilizacao = datetime(2025, 6, 30, 0, 0, 0)

        # Horas diferentes no mesmo dia → mesma chave (agrupados juntos)
        self.assertEqual(
            _chave_grupo(row_com_hora), _chave_grupo(row_sem_hora)
        )

    def test_chave_grupo_data_disponibilizacao_none(self) -> None:
        """Quando data é None, a chave deve conter None sem erro."""
        row = MagicMock(spec=AtribuicaoTerritorioSaberIn)
        row.codigo_turma = "T1"
        row.codigo_territorio_saber = 10
        row.codigo_experiencia_pedagogica = 20
        row.rf_professor = "RF1"
        row.data_atribuicao = datetime(2025, 2, 1)
        row.data_disponibilizacao = None

        chave = _chave_grupo(row)
        self.assertIsNone(chave[-1])

    @patch("apps.core.libs.base_etl_service.Queue")
    def test_executar_fase_timeout_producer_levanta_runtime_error(
        self, mock_queue: MagicMock
    ) -> None:
        mock_q = MagicMock()
        mock_q.get.side_effect = Empty()
        mock_queue.return_value = mock_q

        config = self.service._fases[0]
        self.mock_eol.iter_query.return_value = iter([])

        with self.assertRaises(RuntimeError) as ctx:
            self.service._executar_fase(config)

        self.assertIn("Producer", str(ctx.exception))
