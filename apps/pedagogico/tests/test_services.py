from datetime import datetime
from queue import Empty
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from apps.core.libs.base_etl_service import (
    BaseEtlService,
    PhaseConfig,
    PipelineMetrics,
)
from apps.pedagogico.dtos.model_in import RegenciaComponenteCurricularIn
from apps.pedagogico.services import (
    EtlPedagogicoService,
    _agrupar,
    _build_a3_index,
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

        pk, hash_val, obj = transform((100, " Arte "))

        self.assertEqual(pk, "100")
        self.assertEqual(len(hash_val), 64)
        self.assertEqual(obj.descricao, "Arte")

    def test_criar_transform_componente_por_turma_aplica_lookups(self) -> None:
        self.service._a2 = {
            513: MagicMock(eh_regencia=1, eh_territorio=1),
        }
        self.service._exact = {(513, 6, "7")}
        config = self.service._fases[1]
        transform = self.service._criar_transform(config)

        pk, _, obj = transform(
            (513, " Inglês ", 1, 6, "7", 2025, "T1", "RF1", 0)
        )

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
            transform((None, " Inglês ", 1, 6, "7", 2025, "T1", "RF1", 0))
        )
        self.assertIsNone(
            transform((513, " Inglês ", 1, 6, "7", 2025, None, "RF1", 0))
        )

    def test_criar_transform_componente_regencia_gera_pk_composta(
        self,
    ) -> None:
        self.service._fallback = {200}
        config = self.service._fases[3]
        transform = self.service._criar_transform(config)

        pk, _, obj = transform(
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

    @patch.object(BaseEtlService, "_sync_batch")
    def test_sync_batch_filtra_nones_antes_de_delegar(
        self, mock_sync: MagicMock
    ) -> None:
        mock_sync.return_value = (1, 0)

        resultado = self.service._sync_batch(
            processed_data=[None, ("1", "h", MagicMock())],
            table_name="tb",
            model_class=MagicMock(),
            update_fields=["descricao"],
            unique_fields=["codigo"],
            batch_num=0,
        )

        self.assertEqual(resultado, (1, 0))
        self.assertEqual(len(mock_sync.call_args.kwargs["processed_data"]), 1)

    def test_processar_batch_filtra_nones_antes_do_sync_batch(self) -> None:
        config = self.service._fases[1]
        self.service._a2 = {
            513: MagicMock(eh_regencia=1, eh_territorio=0),
        }
        self.service.sync_batch = MagicMock(return_value=(1, 1))

        escritos, ignorados = self.service._processar_batch(
            config=config,
            chunk=[
                (None, "Inválido", 1, 6, "7", 2025, "T1", "RF1", 0),
                (513, " Inglês ", 1, 6, "7", 2025, "T1", "RF1", 0),
            ],
            transform=self.service._criar_transform(config),
            batch_num=0,
        )

        self.assertEqual((escritos, ignorados), (1, 1))
        processed_data = self.service.sync_batch.call_args.args[0]
        self.assertEqual(len(processed_data), 1)
        self.assertEqual(processed_data[0][0], "513-T1-RF1")

    def test_anos_letivos_usa_cache_por_instancia(self) -> None:
        self.mock_eol.iter_query.return_value = [[(2024,), (2025,)]]

        anos_1 = self.service._anos_letivos()
        anos_2 = self.service._anos_letivos()

        self.assertEqual(anos_1, [2024, 2025])
        self.assertEqual(anos_2, [2024, 2025])
        self.mock_eol.iter_query.assert_called_once()

    @patch.object(EtlPedagogicoService, "_sync_batch")
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
            [call.kwargs["table_name"] for call in mock_sync.call_args_list],
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

    def test_get_partition_sql_preserva_casing(self) -> None:
        service = EtlPedagogicoService(
            db_alias="default",
            eol=self.mock_eol,
        )
        sql = "SELECT codigo FROM componente_curricular ORDER BY codigo"

        resultado = service._get_partition_sql(sql, "codigo")

        self.assertIn("SELECT", resultado)
        self.assertIn("FROM componente_curricular", resultado)
        self.assertIn("ORDER BY codigo", resultado)
        self.assertIn("BETWEEN 1 AND 1000", resultado)

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
