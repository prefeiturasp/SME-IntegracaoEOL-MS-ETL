from datetime import UTC, date, datetime
from queue import Empty
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from apps.core.libs.base_etl_service import (
    PhaseConfig,
    PipelineMetrics,
    TransformFase,
)
from apps.pedagogico.dtos.model_in import (
    AtribuicaoTerritorioSaberIn,
)
from apps.pedagogico.models import (
    AgrupamentoAtribuicaoTerritorioSaber,
    ComponenteCurricularAgrupamento,
)
from apps.pedagogico.queries import (
    SQL_API_EOL_COMPONENTE_CURRICULAR,
    SQL_API_EOL_COMPONENTE_CURRICULAR_HIERARQUIA,
)
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
        self.mock_api_eol = MagicMock()
        self.service = EtlPedagogicoService(
            db_alias="pedagogico_db",
            eol=self.mock_eol,
            api_eol=self.mock_api_eol,
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

    def test_fases_contem_15_configs_esperados(self) -> None:
        self.assertEqual(len(self.service._fases), 15)
        self.assertEqual(
            [fase.nome for fase in self.service._fases],
            [
                "componente_curricular",
                "componente_turma",
                "atribuicao_componente",
                "atribuicao_territorio_saber",
                "componente_curricular_api_eol",
                "componentecurricularhierarquia",
                "componentecurricularpap",
                "componentecurricularplanejamentoregencia",
                "turmaitinerarioensinomedio",
                "agrupamento_atribuicao_territorio_saber",
                "grade_componente_curricular",
                "turma",
                "turma_atribuida_dre_ue",
                "etapa_ensino",
                "ciclo_ensino",
            ],
        )

    def test_criar_transform_ciclo_ensino(self) -> None:
        """Transforma o catálogo de ciclos com chave pelo código."""
        config = next(
            fase for fase in self.service._fases if fase.nome == "ciclo_ensino"
        )
        transform = self.service._criar_transform(config)
        data_atualizacao = datetime(2026, 8, 20, 10, 30, tzinfo=UTC)

        result = transform((5, 4, 3, "Alfabetização", data_atualizacao))

        assert result is not None
        pk, hash_val, obj = result
        self.assertEqual(pk, "3")
        self.assertEqual(len(hash_val), 64)
        self.assertEqual(obj.codigo_modalidade_ensino, 5)
        self.assertEqual(obj.codigo_etapa_ensino, 4)
        self.assertEqual(obj.descricao, "Alfabetização")
        self.assertEqual(obj.data_atualizacao, data_atualizacao)

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

        result = transform(("T1", 513, 1105, "Território", "Experiência"))
        assert result is not None
        pk, _, obj = result

        self.assertEqual(pk, "T1-513")
        self.assertEqual(obj.turma_codigo, "T1")
        self.assertEqual(obj.componente_codigo, 513)
        self.assertEqual(obj.codigo_componente_territorio_saber, 1105)
        self.assertEqual(obj.desc_territorio_saber, "Território")
        self.assertEqual(obj.desc_experiencia_pedagogica, "Experiência")

    def test_criar_transform_componente_turma_pula_linha_sem_codigo_ou_turma(
        self,
    ) -> None:
        config = self.service._fases[1]
        transform = self.service._criar_transform(config)

        self.assertIsNone(transform((None, 513, 1105)))
        self.assertIsNone(transform(("T1", None, 1105)))

    def test_criar_transform_atribuicao_territorio_saber(self) -> None:
        config = self.service._fases[3]
        transform = self.service._criar_transform(config)

        result = transform(
            (
                1216,
                "T1",
                2025,
                "RF1",
                4,
                116,
                "III - ORIENTAÇÃO",
                "CLUBE",
                datetime(2025, 2, 3, tzinfo=UTC),
                None,
                None,
                datetime(2025, 12, 19, tzinfo=UTC),
                False,
            )
        )
        assert result is not None
        pk, _, obj = result

        self.assertIn("T1-1216-RF1-4-116", pk)
        self.assertEqual(obj.turma_codigo, "T1")
        self.assertEqual(obj.componente_codigo, 1216)
        self.assertEqual(obj.professor, "RF1")
        self.assertEqual(obj.codigo_territorio_saber, 4)

    def test_criar_transform_turma_retorna_tripla_com_pk_codigo(
        self,
    ) -> None:
        config = self.service._fases[11]  # fase 12 = turma
        transform = self.service._criar_transform(config)

        row = (
            123456,  # codigo
            2025,  # ano_letivo
            "5",  # ano
            1,  # tipo_turma
            " 5A Manhã ",  # nome_turma
            5,  # duracao_turno
            2,  # tipo_turno
            "2025-02-04T00:00:00",  # data_inicio
            "2025-02-05T08:00:00",  # data_inicio_turma
            None,  # data_fim
            None,  # data_fim_turma
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
            5,  # codigo_etapa_ensino
            3,  # codigo_ciclo_ensino
            7,  # tipo_escola
            42,  # codigo_grade_programa
            " Programa Mais Educação ",  # descricao_grade_programa
            9,  # tipo_grade_programa
            1,  # codigo_tipo_periodicidade
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
        self.assertEqual(obj.tipo_escola, 7)
        self.assertEqual(obj.codigo_grade_programa, 42)
        self.assertEqual(
            obj.descricao_grade_programa, "Programa Mais Educação"
        )
        self.assertEqual(obj.tipo_grade_programa, 9)
        self.assertEqual(obj.codigo_tipo_periodicidade, 1)

    def test_criar_transform_comp_por_ano_letivo_ignora_registro_sem_chave(
        self,
    ) -> None:
        config = self.service._fases[10]
        transform = self.service._criar_transform(config)

        self.assertIsNone(transform((None, "Desc", "1", "1 ano", 1, 5, 2025)))
        self.assertIsNone(transform((100, "Desc", "1", "1 ano", 1, 5, None)))

    def test_criar_transform_grade_usa_serie_na_chave(self) -> None:
        """Grade usa série na chave e ano turma como campo atualizável."""
        config = self.service._fases[10]
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

    def test_criar_transform_api_eol_usa_transform_generico(
        self,
    ) -> None:
        """Fase API EOL usa transform genérico da base."""
        config = self.service._fases[5]
        transform = cast(TransformFase, self.service._criar_transform(config))

        result = transform((1, 512, 513, "2021-12-31T00:00:00"))
        assert result is not None
        pk, _, payload = result
        obj = transform.materializar(payload)

        self.assertEqual(pk, "1")
        self.assertEqual(obj.id_componente_curricular_pai, 512)
        self.assertEqual(obj.id_componente_curricular, 513)
        self.assertIsNotNone(obj.transferido_em)

    def test_criar_transform_regencia_api_eol_usa_chave_composta(
        self,
    ) -> None:
        """Regência da API EOL não depende de id físico de origem."""
        config = self.service._fases[7]
        transform = cast(TransformFase, self.service._criar_transform(config))

        result = transform((218, 4, 5))
        assert result is not None
        pk, _, payload = result
        obj = transform.materializar(payload)

        self.assertEqual(pk, "218-4-5")
        self.assertEqual(obj.id_componente_curricular, 218)
        self.assertEqual(obj.turno, 4)
        self.assertEqual(obj.ano, 5)

    def test_fase_turma_inclui_campos_grade_programa(self) -> None:
        """Campos de grade de programa entram na dedup da fase turma."""
        config = next(
            fase for fase in self.service._fases if fase.nome == "turma"
        )

        self.assertIn("tipo_escola", config.update_fields)
        self.assertIn("codigo_grade_programa", config.update_fields)
        self.assertIn("descricao_grade_programa", config.update_fields)
        self.assertIn("tipo_grade_programa", config.update_fields)

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

    @patch.object(EtlPedagogicoService, "sync_batch", return_value=(1, 0))
    def test_processar_batch_repassa_materializacao_do_transform_generico(
        self, mock_sync: MagicMock
    ) -> None:
        """Transform genérico precisa materializar payload antes do bulk."""
        config = self.service._fases[5]
        transform = self.service._criar_transform(config)

        self.service._processar_batch(
            config=config,
            chunk=[(1, 512, 513, "2021-12-31T00:00:00")],
            transform=transform,
            batch_num=0,
        )

        meta = mock_sync.call_args.args[1]
        self.assertTrue(callable(meta["materializar"]))

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
    @patch.object(EtlPedagogicoService, "_bulk_create_em_lotes")
    def test_executar_agrupamentos_escreve_duas_tabelas(
        self, mock_bulk: MagicMock, _mock_indices: MagicMock
    ) -> None:
        config = self.service._fase_agrupamento_gerado()
        self.service._cache_anos = [2025]
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
        mock_bulk.side_effect = [1, 1]

        metrics = self.service._executar_agrupamentos(config)

        self.assertEqual(metrics.total_lidos, 2)
        self.assertEqual(metrics.total_escritos, 1)
        self.assertEqual(self.service._total_itens_agrupamento, 1)
        self.assertEqual(
            [call.args[0] for call in mock_bulk.call_args_list],
            [
                AgrupamentoAtribuicaoTerritorioSaber,
                ComponenteCurricularAgrupamento,
            ],
        )

    def test_bulk_create_em_lotes_fragmenta_em_batches_de_500(self) -> None:
        """Bulk create é executado em lotes de 500 objetos."""

        class FakeManager:
            def __init__(self) -> None:
                self.batch_sizes: list[int] = []

            def bulk_create(
                self,
                lote: list[object],
                batch_size: int,
            ) -> None:
                self.batch_sizes.append(len(lote))
                self.batch_size = batch_size

        class FakeObjects:
            def __init__(self) -> None:
                self.manager = FakeManager()

            def using(self, db_alias: str) -> FakeManager:
                self.db_alias = db_alias
                return self.manager

        class FakeModel:
            objects = FakeObjects()

        total = self.service._bulk_create_em_lotes(
            FakeModel,
            [object() for _ in range(1001)],
        )

        self.assertEqual(total, 1001)
        self.assertEqual(FakeModel.objects.db_alias, "pedagogico_db")
        self.assertEqual(FakeModel.objects.manager.batch_sizes, [500, 500, 1])
        self.assertEqual(FakeModel.objects.manager.batch_size, 500)

    @patch.object(EtlPedagogicoService, "_bulk_create_em_lotes")
    @patch.object(EtlPedagogicoService, "_anos_letivos", return_value=[2025])
    def test_executar_atribuicoes_territorio_deduplica_e_descarta_invalidos(
        self,
        _mock_anos: MagicMock,
        mock_bulk: MagicMock,
    ) -> None:
        """Fase de atribuição materializa apenas linhas válidas e únicas."""
        config = self.service._fases[3]
        row_valida = (
            1216,
            "T1",
            2025,
            "RF1",
            4,
            116,
            "TS",
            "EP",
            datetime(2025, 2, 3, tzinfo=UTC),
            None,
            None,
            datetime(2025, 12, 19, tzinfo=UTC),
            False,
        )
        row_sem_rf = (
            1217,
            "T1",
            2025,
            None,
            4,
            116,
            "TS",
            "EP",
            datetime(2025, 2, 3, tzinfo=UTC),
            None,
            None,
            datetime(2025, 12, 19, tzinfo=UTC),
            False,
        )
        self.mock_eol.iter_query.return_value = [[row_valida, row_valida]]
        mock_bulk.side_effect = lambda _model, objs: len(objs)

        with patch(
            "apps.pedagogico.services.etl_pedagogico_service"
            ".AtribuicaoTerritorioSaber"
        ) as mock_model:
            mock_model.objects.using.return_value.filter.return_value.delete.return_value = (  # noqa: E501
                0,
                {},
            )
            mock_model.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
            self.mock_eol.iter_query.return_value = [
                [row_valida, row_valida, row_sem_rf]
            ]

            metrics = self.service._executar_atribuicoes_territorio(config)

        self.assertEqual(metrics.total_lidos, 3)
        self.assertEqual(metrics.total_escritos, 1)
        mock_model.objects.using.assert_called_with("pedagogico_db")
        mock_model.objects.using.return_value.filter.assert_called_once_with(
            ano_letivo__in=[2025]
        )
        mock_bulk.assert_called_once()
        objetos_criados = mock_bulk.call_args.args[1]
        self.assertEqual(len(objetos_criados), 1)

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
        with patch.object(self.service, "_executar_fase") as mock_fase:
            mock_fase.return_value = PipelineMetrics(total_escritos=10)
            self.service._total_itens_agrupamento = 7

            resultado = self.service.executar(fase_inicial=3)

        self.assertEqual(
            resultado["agrupamento_atribuicao_territorio_saber"], 10
        )
        self.assertNotIn("componente_curricular_agrupamento", resultado)
        self.assertIn("grade_componente_curricular", resultado)
        self.assertIn("turma", resultado)
        self.assertEqual(mock_fase.call_count, 13)
        self.assertEqual(mock_fase.call_args_list[0].kwargs["numero_fase"], 3)

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

    def test_agrupar_mantem_professores_distintos_com_mesmo_id_historico(
        self,
    ) -> None:
        """RFs distintos podem compartilhar o mesmo cod_agrupamento legado."""
        rows = [
            AtribuicaoTerritorioSaberIn(
                1216,
                "3035027",
                2026,
                "8253251",
                9,
                66,
                "TS",
                "EP",
                datetime(2026, 6, 1),
                datetime(2026, 6, 16, 14, 26, 4, 757000),
                64,
                datetime(2026, 12, 22),
                0,
            ),
            AtribuicaoTerritorioSaberIn(
                1217,
                "3035027",
                2026,
                "8253251",
                9,
                66,
                "TS",
                "EP",
                datetime(2026, 6, 1),
                datetime(2026, 6, 16, 14, 26, 4, 727000),
                64,
                datetime(2026, 12, 22),
                0,
            ),
            AtribuicaoTerritorioSaberIn(
                1216,
                "3035027",
                2026,
                "9364528",
                9,
                66,
                "TS",
                "EP",
                datetime(2026, 6, 16),
                None,
                None,
                datetime(2026, 12, 22),
                0,
            ),
            AtribuicaoTerritorioSaberIn(
                1217,
                "3035027",
                2026,
                "9364528",
                9,
                66,
                "TS",
                "EP",
                datetime(2026, 6, 16),
                None,
                None,
                datetime(2026, 12, 22),
                0,
            ),
        ]

        agrupamentos, itens = _agrupar(
            rows,
            timezone.now(),
            agrupamentos_exatos={},
            agrupamentos_historicos={("3035027", 9, 66, "1216,1217"): 815274},
            ultimo_id_gerado=815274,
        )

        self.assertEqual(len(agrupamentos), 2)
        self.assertEqual(
            {a.rf_professor for a in agrupamentos}, {"8253251", "9364528"}
        )
        self.assertEqual({a.cod_agrupamento for a in agrupamentos}, {815274})
        self.assertEqual(len(itens), 4)
        self.assertEqual(
            {i.rf_professor for i in itens}, {"8253251", "9364528"}
        )

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

    def test_iter_chunks_substitui_placeholder_por_ano_letivo(self) -> None:
        """SQL com ``?`` itera uma vez por ano letivo do EOL."""
        self.service._cache_anos = [2024, 2025]
        self.mock_eol.iter_query.side_effect = [
            [[("a",)]],
            [[("b",)]],
        ]

        chunks = list(self.service._iter_chunks("SELECT * WHERE ano = ?"))

        self.assertEqual(chunks, [[("a",)], [("b",)]])
        self.assertEqual(
            [c.args[0] for c in self.mock_eol.iter_query.call_args_list],
            ["SELECT * WHERE ano = 2024", "SELECT * WHERE ano = 2025"],
        )

    def test_iter_chunks_sem_placeholder_executa_query_unica(self) -> None:
        """SQL sem ``?`` é repassado direto ao EOL."""
        self.mock_eol.iter_query.return_value = [[("x",)]]

        chunks = list(self.service._iter_chunks("SELECT 1"))

        self.assertEqual(chunks, [[("x",)]])
        self.mock_eol.iter_query.assert_called_once_with("SELECT 1")

    def test_iter_chunks_api_eol_usa_servico_api_eol(self) -> None:
        """SQL da API EOL é repassado ao serviço Postgres específico."""
        self.mock_api_eol.iter_query.return_value = [[("api",)]]

        chunks = list(
            self.service._iter_chunks(
                SQL_API_EOL_COMPONENTE_CURRICULAR_HIERARQUIA
            )
        )

        self.assertEqual(chunks, [[("api",)]])
        self.mock_api_eol.iter_query.assert_called_once_with(
            SQL_API_EOL_COMPONENTE_CURRICULAR_HIERARQUIA
        )
        self.mock_eol.iter_query.assert_not_called()

    def test_componente_curricular_api_eol_preserva_linha_sem_pai(
        self,
    ) -> None:
        config = self.service._fases[4]
        transform = cast(TransformFase, self.service._criar_transform(config))

        result = transform((None, 513, True, False, " Arte ", None, None))
        assert result is not None
        pk, _, payload = result
        obj = transform.materializar(payload)

        self.assertEqual(pk, "None-513")
        self.assertIsNone(obj.id_relacao_origem)
        self.assertEqual(obj.id_componente_curricular, 513)
        self.assertEqual(obj.descricao, "Arte")
        self.assertIsNone(obj.id_componente_curricular_pai)
        self.assertIsNone(obj.vigencia)
        self.assertEqual(config.modo_escrita, "full_refresh")
        self.assertTrue(config.truncate_on_full_sync)

    def test_iter_chunks_componente_curricular_usa_api_eol(self) -> None:
        self.mock_api_eol.iter_query.return_value = [[("api",)]]

        chunks = list(
            self.service._iter_chunks(SQL_API_EOL_COMPONENTE_CURRICULAR)
        )

        self.assertEqual(chunks, [[("api",)]])
        self.mock_api_eol.iter_query.assert_called_once_with(
            SQL_API_EOL_COMPONENTE_CURRICULAR
        )
        self.mock_eol.iter_query.assert_not_called()

    def test_parametros_abrangencia_le_chave_valor(self) -> None:
        """Lê a tabela ``parametros`` (api_eol_db) como dict nome->valor."""
        self.mock_api_eol.iter_query.return_value = [
            [
                ("tipo_escola_sgp", "1,2,3"),
                ("tipo_escola_infantil_sgp", "2,11"),
            ],
            [("etapas_por_modalidade", '{"1": [1, 10]}')],
        ]

        parametros = self.service._parametros_abrangencia()

        self.assertEqual(
            parametros,
            {
                "tipo_escola_sgp": "1,2,3",
                "tipo_escola_infantil_sgp": "2,11",
                "etapas_por_modalidade": '{"1": [1, 10]}',
            },
        )

    def test_sql_turmas_atribuidas_dre_ue_formata_placeholders(self) -> None:
        """Monta a SQL de abrangência com os parâmetros vigentes."""
        self.mock_api_eol.iter_query.return_value = [
            [
                ("tipo_escola_sgp", "1,2,3,4"),
                ("tipo_escola_infantil_sgp", "2,11"),
                (
                    "etapas_por_modalidade",
                    '{"1": [1, 10], "3": [2, 3, 11], '
                    '"5": [4, 5, 12, 13], "6": [6, 7, 8]}',
                ),
            ]
        ]

        sql = self.service._sql_turmas_atribuidas_dre_ue()

        self.assertIn("esc.tp_escola IN (1,2,3,4)", sql)
        self.assertIn("tp_escola IN (2,11)", sql)
        self.assertIn("ee.cd_etapa_ensino IN (1,10)", sql)
        self.assertIn("ee.cd_etapa_ensino IN (2,3,11)", sql)
        self.assertIn("ee.cd_etapa_ensino IN (4,5,12,13)", sql)
        self.assertIn("ee.cd_etapa_ensino IN (6,7,8)", sql)
        self.assertNotIn("{tipos_escola}", sql)
        self.assertNotIn("{etapas_infantil}", sql)

    def test_executar_fase_turma_atribuida_dre_ue_monta_sql_antes_de_delegar(
        self,
    ) -> None:
        """Fase de abrangência troca o SQL pelo montado em tempo real."""
        config = next(
            f
            for f in self.service._fases
            if f.nome == "turma_atribuida_dre_ue"
        )
        sql_montado = "SELECT 1 -- sql montado"

        with (
            patch.object(
                self.service,
                "_sql_turmas_atribuidas_dre_ue",
                return_value=sql_montado,
            ),
            patch.object(
                self.service.__class__.__bases__[0], "_executar_fase"
            ) as mock_base,
        ):
            self.service._executar_fase(config, numero_fase=13)

        mock_base.assert_called_once()
        config_chamado = mock_base.call_args.args[0]
        self.assertEqual(config_chamado.sql, sql_montado)
        self.assertEqual(config_chamado.nome, "turma_atribuida_dre_ue")
        self.mock_api_eol.iter_query.assert_not_called()

    def test_criar_transform_fase_sem_factory_usa_implementacao_base(
        self,
    ) -> None:
        """Fase sem transform específico cai no transform da base."""
        config = self.service._fases[2]  # atribuicao_componente
        config_sem_factory = PhaseConfig(
            nome="fase_generica",
            sql=config.sql,
            table_name=config.table_name,
            model_class=config.model_class,
            dto_in=config.dto_in,
            pk_field=config.pk_field,
            update_fields=config.update_fields,
            unique_fields=config.unique_fields,
        )

        with patch.object(
            self.service.__class__.__bases__[0], "_criar_transform"
        ) as mock_base:
            self.service._criar_transform(config_sem_factory)

        mock_base.assert_called_once_with(config_sem_factory)

    def test_criar_transform_atribuicao_componente_monta_pk_composta(
        self,
    ) -> None:
        """Transform de atribuição compõe PK turma-componente-professor."""
        config = self.service._fases[2]
        transform = self.service._criar_transform(config)

        result = transform(
            ("T1", 513, "RF9", False, 2025, None, None, None, None, None)
        )
        assert result is not None
        pk, hash_val, obj = result

        self.assertEqual(pk, "T1-513-RF9")
        self.assertEqual(len(hash_val), 64)
        self.assertEqual(obj.turma_codigo, "T1")
        self.assertEqual(obj.componente_codigo, 513)
        self.assertEqual(obj.professor, "RF9")

    def test_criar_transform_atribuicao_componente_pula_sem_chave(
        self,
    ) -> None:
        """Atribuição sem turma ou professor é descartada."""
        config = self.service._fases[2]
        transform = self.service._criar_transform(config)

        self.assertIsNone(
            transform(
                (None, 513, "RF9", False, 2025, None, None, None, None, None)
            )
        )
        self.assertIsNone(
            transform(
                ("T1", 513, None, False, 2025, None, None, None, None, None)
            )
        )

    def test_processar_batch_sem_itens_validos_retorna_zero_escritos(
        self,
    ) -> None:
        """Lote com apenas linhas inválidas não chama sync_batch."""
        config = self.service._fases[1]

        with patch.object(self.service, "sync_batch") as mock_sync:
            escritos, ignorados = self.service._processar_batch(
                config=config,
                chunk=[(None, 513, 1105), ("T1", None, 1105)],
                transform=self.service._criar_transform(config),
                batch_num=0,
            )

        self.assertEqual((escritos, ignorados), (0, 2))
        mock_sync.assert_not_called()

    def test_anos_letivos_filtra_lista_exata(self) -> None:
        """Quando ``anos_letivos`` é informado, só esses anos são usados."""
        service = EtlPedagogicoService(
            db_alias="pedagogico_db",
            eol=self.mock_eol,
            id_execucao=uuid4(),
            anos_letivos=[2024, 2026],
        )
        self.mock_eol.iter_query.return_value = [
            [(2023,), (2024,), (2025,), (2026,)]
        ]

        anos = service._anos_letivos()

        self.assertEqual(anos, [2024, 2026])

    def test_executar_fase_roteia_agrupamentos_para_metodo_dedicado(
        self,
    ) -> None:
        """Fase de agrupamento é tratada pelo método dedicado."""
        config = self.service._fase_agrupamento_gerado()

        with patch.object(
            self.service, "_executar_agrupamentos"
        ) as mock_agrup:
            mock_agrup.return_value = PipelineMetrics(total_escritos=5)
            metrics = self.service._executar_fase(config, numero_fase=4)

        mock_agrup.assert_called_once_with(config)
        self.assertEqual(metrics.total_escritos, 5)

    def test_executar_fase_roteia_atribuicao_territorio_para_metodo_dedicado(
        self,
    ) -> None:
        """Fase de atribuição de território é tratada pelo método dedicado."""
        config = self.service._fases[3]

        with patch.object(
            self.service, "_executar_atribuicoes_territorio"
        ) as mock_atribuicoes:
            mock_atribuicoes.return_value = PipelineMetrics(total_escritos=4)
            metrics = self.service._executar_fase(config, numero_fase=4)

        mock_atribuicoes.assert_called_once_with(config)
        self.assertEqual(metrics.total_escritos, 4)

    def test_fase_backup_gerada_entra_apenas_quando_selecionada(
        self,
    ) -> None:
        """Agrupamento gerado fica disponível sem rodar no fluxo padrão."""
        service = EtlPedagogicoService(
            db_alias="pedagogico_db",
            eol=self.mock_eol,
            id_execucao=uuid4(),
            fases=["agrupamento_territorio_saber_gerado"],
        )

        self.assertEqual(len(service._fases), 16)
        self.assertEqual(
            service._fases[-1].nome,
            "agrupamento_territorio_saber_gerado",
        )

    def test_executar_ignora_fases_anteriores_e_nao_selecionadas(
        self,
    ) -> None:
        """``executar`` pula fases abaixo do início e fora da seleção."""
        self.service._fases_selecionadas = ["turma"]

        with patch.object(self.service, "_executar_fase") as mock_fase:
            mock_fase.return_value = PipelineMetrics(total_escritos=3)
            resultado = self.service.executar(fase_inicial=2)

        self.assertEqual(mock_fase.call_count, 1)
        self.assertEqual(mock_fase.call_args.kwargs["numero_fase"], 12)
        self.assertEqual(resultado, {"turma": 3})

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
