from datetime import date, datetime
from queue import Empty
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from apps.core.libs.base_etl_service import PhaseConfig, PipelineMetrics
from apps.pedagogico.dtos.model_in import (
    AtribuicaoTerritorioSaberIn,
)
from apps.pedagogico.models import AgrupamentoAtribuicaoTerritorioSaber
from apps.pedagogico.services import (
    _AGRUPAMENTO_ID_INICIAL,
    EtlPedagogicoService,
    _agrupar,
    _chave_grupo,
    _cod_agrupamento,
    _montar_indices_agr_existentes,
)


class TestPedagogicoService(TestCase):
    """Testes para ``EtlPedagogicoService`` e helpers do domínio."""

    databases = {"default", "pedagogico_db"}

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
                "componente_turma",
                "atribuicao_componente",
                "agrupamento_territorio_saber",
                "grade_componente_curricular",
                "turma",
            ],
        )

    def test_criar_transform_componente_curricular_retorna_tripla(
        self,
    ) -> None:
        config = self.service._fases[0]
        transform = self.service._criar_transform(config)

        result = transform((100, " Arte ", 1))
        assert result is not None
        pk, hash_val, obj = result

        self.assertEqual(pk, "100")
        self.assertEqual(len(hash_val), 64)
        self.assertEqual(obj.descricao, "Arte")
        self.assertTrue(obj.regencia)

    def test_criar_transform_componente_turma_mapeia_vinculo_minimo(
        self,
    ) -> None:
        config = self.service._fases[1]
        transform = self.service._criar_transform(config)

        result = transform(("T1", 513, 1105))
        assert result is not None
        pk, _, obj = result

        self.assertEqual(pk, "T1-513")
        self.assertEqual(obj.turma_codigo, "T1")
        self.assertEqual(obj.componente_codigo, 513)
        self.assertEqual(obj.codigo_componente_territorio_saber, 1105)

    def test_criar_transform_componente_turma_pula_linha_sem_codigo_ou_turma(
        self,
    ) -> None:
        config = self.service._fases[1]
        transform = self.service._criar_transform(config)

        self.assertIsNone(transform((None, 513, 1105)))
        self.assertIsNone(transform(("T1", None, 1105)))

    def test_criar_transform_turma_retorna_tripla_com_pk_codigo(
        self,
    ) -> None:
        config = self.service._fases[5]  # fase 6 = turma
        transform = self.service._criar_transform(config)

        row = (
            123456,  # codigo
            2025,  # ano_letivo
            "5",  # ano
            1,  # tipo_turma
            " 5A Manhã ",  # nome_turma
            5,  # duracao_turno
            2,  # tipo_turno
            "2025-02-05T08:00:00",  # data_inicio_turma
            None,  # data_fim
            0,  # extinta
            "O",  # situacao
            "001234",  # ue_codigo
            None,  # data_atualizacao
            None,  # data_status_turma_escola
            " 5o ano ",  # serie_ensino
            50,  # codigo_serie_ensino
            " Fundamental ",  # modalidade
            5,  # codigo_modalidade
            3,  # codigo_tipo_programa
            5,  # codigo_modalidade_etapa
            0,  # semestre
            0,  # ensino_especial
        )
        result = transform(row)
        assert result is not None
        pk, hash_val, obj = result

        self.assertEqual(pk, "123456")
        self.assertEqual(len(hash_val), 64)
        self.assertEqual(obj.codigo, 123456)
        self.assertEqual(obj.nome_turma, "5A Manhã")
        self.assertEqual(obj.serie_ensino, "5o ano")
        self.assertEqual(obj.codigo_serie_ensino, 50)
        self.assertEqual(obj.modalidade, "Fundamental")
        self.assertEqual(obj.codigo_tipo_programa, 3)
        self.assertFalse(obj.extinta)
        self.assertEqual(obj.semestre, 0)

    def test_criar_transform_comp_por_ano_letivo_ignora_registro_sem_chave(
        self,
    ) -> None:
        config = self.service._fases[4]
        transform = self.service._criar_transform(config)

        self.assertIsNone(transform((None, "Desc", "1", "1 ano", 1, 5, 2025)))
        self.assertIsNone(transform((100, "Desc", "1", "1 ano", 1, 5, None)))

    def test_criar_transform_grade_usa_serie_na_chave(self) -> None:
        """Grade usa série na chave e ano turma como campo atualizável."""
        config = self.service._fases[4]
        transform = self.service._criar_transform(config)

        result = transform((100, " Arte ", "1", "1 ano", 88, 5, 2024))
        assert result is not None
        pk, _, obj = result

        self.assertEqual(pk, "100-2024-5-88")
        self.assertEqual(obj.codigo_ano_turma, "1")
        self.assertEqual(obj.codigo_serie_ensino, 88)
        self.assertEqual(
            config.pk_field,
            [
                "codigo_componente_curricular",
                "ano_letivo",
                "modalidade",
                "codigo_serie_ensino",
            ],
        )
        self.assertIn("codigo_ano_turma", config.update_fields)
        self.assertEqual(
            config.unique_fields,
            (
                "codigo_componente_curricular",
                "ano_letivo",
                "modalidade",
                "codigo_serie_ensino",
            ),
        )

    @patch.object(EtlPedagogicoService, "sync_batch", return_value=(1, 1))
    def test_processar_batch_filtra_nones_antes_do_sync_batch(
        self, mock_sync: MagicMock
    ) -> None:
        config = self.service._fases[1]

        escritos, ignorados = self.service._processar_batch(
            config=config,
            chunk=[
                (None, 513, 1105),
                ("T1", 513, 1105),
            ],
            transform=self.service._criar_transform(config),
            batch_num=0,
        )

        self.assertEqual((escritos, ignorados), (1, 1))
        processed_data = mock_sync.call_args.args[0]
        self.assertEqual(len(processed_data), 1)
        self.assertEqual(processed_data[0][0], "T1-513")

    def test_anos_letivos_usa_cache_por_instancia(self) -> None:
        self.mock_eol.iter_query.return_value = [[(2024,), (2025,)]]

        anos_1 = self.service._anos_letivos()
        anos_2 = self.service._anos_letivos()

        self.assertEqual(anos_1, [2024, 2025])
        self.assertEqual(anos_2, [2024, 2025])
        self.mock_eol.iter_query.assert_called_once()

    @patch(
        "apps.pedagogico.services.etl_pedagogico_service"
        ".montar_indices_agrupamentos_existentes",
        return_value=({}, {}, _AGRUPAMENTO_ID_INICIAL),
    )
    @patch.object(EtlPedagogicoService, "sync_batch")
    def test_executar_agrupamentos_escreve_duas_tabelas(
        self, mock_sync: MagicMock, _mock_indices: MagicMock
    ) -> None:
        config = self.service._fases[3]
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

    def test_executar_preenche_duas_chaves_a_partir_da_fase_3(self) -> None:
        with (
            patch.object(self.service, "_executar_fase") as mock_fase,
            patch.object(self.service, "_registrar_auditoria_fase"),
        ):
            mock_fase.return_value = PipelineMetrics(total_escritos=10)
            self.service._total_itens_agrupamento = 7

            resultado = self.service.executar(fase_inicial=3)

        self.assertEqual(
            resultado["agrupamento_atribuicao_territorio_saber"], 10
        )
        self.assertEqual(resultado["componente_curricular_agrupamento"], 7)
        self.assertIn("grade_componente_curricular", resultado)
        self.assertIn("turma", resultado)
        self.assertEqual(mock_fase.call_count, 4)

    def test_cod_agrupamento_gera_proximo_sequencial_quando_novo(self) -> None:
        """Novo agrupamento deve receber o próximo ID acima do piso."""
        resultado, ultimo = _cod_agrupamento(
            "T1",
            10,
            20,
            "RF1",
            datetime(2025, 2, 1),
            [100, 200],
            {},
            {},
            _AGRUPAMENTO_ID_INICIAL,
        )
        self.assertEqual(resultado, _AGRUPAMENTO_ID_INICIAL + 1)
        self.assertEqual(ultimo, _AGRUPAMENTO_ID_INICIAL + 1)

    def test_cod_agrupamento_reutiliza_id_exato_existente(self) -> None:
        """Agrupamento idêntico deve manter o mesmo ID já persistido."""
        exatos = {
            (
                "T1",
                10,
                20,
                "RF1",
                datetime(2025, 2, 1).date(),
                "100,200",
            ): 900123
        }
        resultado, ultimo = _cod_agrupamento(
            "T1",
            10,
            20,
            "RF1",
            datetime(2025, 2, 1),
            [100, 200],
            exatos,
            {},
            900123,
        )
        self.assertEqual(resultado, 900123)
        self.assertEqual(ultimo, 900123)

    def test_cod_agrupamento_reutiliza_id_historico_mesmos_componentes(
        self,
    ) -> None:
        """Mudando RF/data, o ETL deve reaproveitar o ID histórico do grupo."""
        historicos = {("T1", 10, 20, "100,200"): 900555}
        resultado, ultimo = _cod_agrupamento(
            "T1",
            10,
            20,
            "RF2",
            datetime(2025, 3, 1),
            [100, 200],
            {},
            historicos,
            900555,
        )
        self.assertEqual(resultado, 900555)
        self.assertEqual(ultimo, 900555)

    def test_agrupar_reutiliza_cod_agrupamento_existente_do_banco(
        self,
    ) -> None:
        """A fase 3 deve manter compatibilidade com IDs já persistidos."""
        db = "pedagogico_db"
        AgrupamentoAtribuicaoTerritorioSaber.objects.using(db).create(
            cod_agrupamento=800777,
            cod_territorio_saber=10,
            cod_experiencia_pedagogica=20,
            dt_inicio_atribuicao=timezone.make_aware(datetime(2025, 2, 1)),
            ano_atribuicao=2025,
            dt_fim_atribuicao=None,
            dt_fim_turma=timezone.make_aware(datetime(2025, 12, 20)),
            rf_professor="RF_ANTIGO",
            cod_turma="T1",
            cod_componentes_curriculares="100,200",
            ano_letivo=2025,
            cod_motivo_disponibilizacao=None,
            desc_territorio_saber="TS",
            desc_experiencia_pedagogica="EP",
            encerramento_atribuicao_agrupamento_atualizado=None,
            transferido_em=timezone.now(),
        )
        rows = [
            AtribuicaoTerritorioSaberIn(
                100,
                "T1",
                2025,
                "RF_NOVO",
                10,
                20,
                "TS",
                "EP",
                datetime(2025, 3, 1),
                None,
                None,
                datetime(2025, 12, 20),
                0,
            ),
            AtribuicaoTerritorioSaberIn(
                200,
                "T1",
                2025,
                "RF_NOVO",
                10,
                20,
                "TS",
                "EP",
                datetime(2025, 3, 1),
                None,
                None,
                datetime(2025, 12, 20),
                0,
            ),
        ]

        exatos, historicos, ultimo = _montar_indices_agr_existentes(db)
        agrupamentos, _ = _agrupar(
            rows,
            timezone.now(),
            agrupamentos_exatos=exatos,
            agrupamentos_historicos=historicos,
            ultimo_id_gerado=ultimo,
        )

        self.assertEqual(len(agrupamentos), 1)
        self.assertEqual(agrupamentos[0].cod_agrupamento, 800777)

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
        """Quando data é None, a chave deve conter sentinela comparável."""
        row = MagicMock(spec=AtribuicaoTerritorioSaberIn)
        row.codigo_turma = "T1"
        row.codigo_territorio_saber = 10
        row.codigo_experiencia_pedagogica = 20
        row.rf_professor = "RF1"
        row.data_atribuicao = datetime(2025, 2, 1)
        row.data_disponibilizacao = None

        chave = _chave_grupo(row)
        self.assertEqual(chave[-1], date.min)

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
