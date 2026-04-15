"""Testes do EtlProgramasService (arquitetura BaseEtlService/PhaseConfig)."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase

from apps.core.libs.base_etl_service import PhaseConfig, PipelineMetrics
from apps.programas.services import EtlProgramasService


class TestProgramasService(TestCase):
    """Testes para EtlProgramasService."""

    def setUp(self) -> None:
        """Inicializa service com EOL mockado."""
        self.mock_eol = MagicMock()
        self.service = EtlProgramasService(
            db_alias="programas_db",
            eol=self.mock_eol,
            id_execucao=uuid4(),
        )
        self.service._truncar_tabela = MagicMock()

    def test_phase_config_e_imutavel(self) -> None:
        """Valida que PhaseConfig é frozen."""
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

    def test_fases_contem_5_configs(self) -> None:
        """Valida que o service define as 5 fases esperadas."""
        self.assertEqual(len(self.service._fases), 5)
        nomes = [f.nome for f in self.service._fases]
        self.assertEqual(
            nomes,
            [
                "tipo_programa",
                "componente_curricular_programa",
                "turma_programa",
                "turma_programa_componente_curricular",
                "matricula_turma_programa",
            ],
        )

    def test_iter_chunks_delega_ao_eol(self) -> None:
        """Valida que _iter_chunks usa eol.iter_query."""
        self.mock_eol.iter_query.return_value = iter([[("a",)]])
        list(self.service._iter_chunks("SELECT 1"))
        self.mock_eol.iter_query.assert_called_once_with("SELECT 1")

    def test_criar_transform_retorna_tripla(self) -> None:
        """Valida que a factory de transform gera a tripla (pk, hash, obj)."""
        config = self.service._fases[0]  # tipo_programa
        transform = self.service._criar_transform(config)

        row = (649, "PAP-RECUP", "PAP Recuperação")
        pk, h, obj = transform(row)

        self.assertEqual(pk, "649")
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)
        self.assertEqual(obj.codigo_tipo_programa, 649)

    def test_criar_transform_pk_composta_turma_componente(self) -> None:
        """Valida geração de PK composta para turma_programa_componente."""
        config = self.service._fases[3]  # turma_programa_componente_curricular
        transform = self.service._criar_transform(config)

        row = (12345, 1322, "PAP Rec")
        pk, _, _ = transform(row)

        self.assertEqual(pk, "12345-1322")

    def test_criar_transform_pk_composta_matricula(self) -> None:
        """Valida geração de PK composta de 3 campos para matricula."""
        import datetime

        config = self.service._fases[4]  # matricula_turma_programa
        transform = self.service._criar_transform(config)

        row = (
            99999,  # codigo_aluno
            12345,  # codigo_turma
            1322,  # codigo_componente_curricular
            "PAP Rec",  # nome_componente_curricular
            1,  # codigo_situacao_matricula
            datetime.date(2025, 2, 1),  # data_matricula
            None,  # data_situacao
            2025,  # ano_letivo
            "000001",  # codigo_ue
            "108900",  # codigo_dre
            649,  # codigo_tipo_programa
        )
        pk, _, _ = transform(row)
        
        self.assertEqual(pk, "12345-99999-1322")

    @patch.object(EtlProgramasService, "sync_batch")
    def test_executar_fase_chama_sync_batch_por_chunk(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida o pipeline Producer-Consumer com 2 chunks."""
        config = self.service._fases[0]
        self.mock_eol.iter_query.return_value = [
            [(649, "PAP-RECUP", "PAP Recuperação")],
            [(650, "PAP-COL", "PAP Colaborativo")],
        ]
        mock_sync.return_value = (1, 0)

        metrics = self.service._executar_fase(config)

        self.assertEqual(metrics.total_lidos, 2)
        self.assertEqual(metrics.total_escritos, 2)
        self.assertEqual(mock_sync.call_count, 2)

    def test_executar_fase_erro_producer_e_propagado(self) -> None:
        """Valida que erros na extração (Producer thread) param o ETL."""
        config = self.service._fases[0]
        self.mock_eol.iter_query.side_effect = RuntimeError("Falha SQL")

        with self.assertRaises(RuntimeError):
            self.service._executar_fase(config)

    def test_executar_pula_fases_anteriores(self) -> None:
        """Valida o parâmetro fase_inicial."""
        with patch.object(EtlProgramasService, "_executar_fase") as mock_fase:
            mock_fase.return_value = PipelineMetrics(total_escritos=1)

            res = self.service.executar(fase_inicial=5)

            self.assertEqual(len(res), 1)
            self.assertIn("matricula_turma_programa", res)
            self.assertEqual(mock_fase.call_count, 1)

    def test_executar_completo_acumula_resultados(self) -> None:
        """Valida execução completa das 5 fases."""
        with patch.object(EtlProgramasService, "_executar_fase") as mock_fase:
            mock_fase.return_value = PipelineMetrics(total_escritos=10)

            res = self.service.executar(fase_inicial=1)

            self.assertEqual(len(res), 5)
            self.assertEqual(res["tipo_programa"], 10)
            self.assertEqual(mock_fase.call_count, 5)

    @patch.object(EtlProgramasService, "sync_batch")
    def test_sync_batch_argumentos_corretos(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida que model_class, table_name, update/unique_fields são passados."""
        config = self.service._fases[0]
        self.mock_eol.iter_query.return_value = [
            [(649, "PAP-RECUP", "PAP Recuperação")]
        ]
        mock_sync.return_value = (1, 0)

        self.service._executar_fase(config)

        args, _ = mock_sync.call_args
        fase_meta = args[1]
        self.assertEqual(fase_meta["model_class"], config.model_class)
        self.assertEqual(
            fase_meta["update_fields"], list(config.update_fields)
        )
        self.assertEqual(
            fase_meta["unique_fields"], list(config.unique_fields)
        )
        self.assertEqual(fase_meta["modo_escrita"], config.modo_escrita)
        self.assertEqual(fase_meta["table_name"], "tipo_programa")

    def test_primeiro_run_repassado_ao_base(self) -> None:
        """Valida que primeiro_run=True chega ao BaseEtlService."""
        service = EtlProgramasService(
            db_alias="programas_db",
            eol=self.mock_eol,
            primeiro_run=True,
        )
        self.assertTrue(service.primeiro_run)

    def test_modo_escrita_upsert_em_todas_fases(self) -> None:
        """Todas as fases de programas usam upsert (sem full_refresh)."""
        for fase in self.service._fases:
            with self.subTest(fase=fase.nome):
                self.assertEqual(fase.modo_escrita, "upsert")

    def test_source_table_diferentes_de_table_name(self) -> None:
        """As fases ETL leem de tabelas EOL diferentes do destino."""
        # tipo_programa lê de tipo_programa (mesmo nome — dado de seed)
        # mas turma_programa lê de turma_escola
        turma_fase = self.service._fases[2]
        self.assertEqual(turma_fase.table_name, "turma_programa")
        self.assertEqual(turma_fase.source_table, "turma_escola")
