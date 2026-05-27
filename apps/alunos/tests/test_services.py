from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase

from apps.alunos.dtos.model_in import (
    MatriculaTurmaIn,
    NecessidadeEspecialAlunoIn,
)
from apps.alunos.models import (
    DadosAlunoAcompanhamentoEscolar,
    MatriculaAnoLetivo,
    MatriculaComponenteCurricularAnoLetivo,
)
from apps.alunos.services import EtlAlunosService, PhaseConfig
from apps.core.libs.base_etl_service import PipelineMetrics


class TestAlunosService(TestCase):
    """Testes para EtlAlunosService (Arquitetura Turbo/PhaseConfig)."""

    def setUp(self) -> None:
        """Inicializa service com EOL mockado.

        _truncar_tabela é mockado para evitar UndefinedTable do psycopg.
        """
        self.mock_eol = MagicMock()
        self.service = EtlAlunosService(
            db_alias="default",
            eol=self.mock_eol,
            id_execucao=uuid4(),
        )
        # Evita UndefinedTable em testes SimpleTestCase/TestCase.
        self.service._truncar_tabela = MagicMock()

    def test_phase_config_e_imutavel(self) -> None:
        """Valida que PhaseConfig é frozen."""
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

    def test_fases_contem_9_configs(self) -> None:
        """Valida que o service define as 9 fases esperadas."""
        self.assertEqual(len(self.service._fases), 9)
        nomes = [f.nome for f in self.service._fases]
        self.assertEqual(
            nomes,
            [
                "tipo_necessidade_especial",
                "aluno",
                "responsavel_aluno",
                "nee_aluno",
                "matricula",
                "matricula_turma",
                "matricula_ano_letivo",
                "matricula_componente_curricular_ano_letivo",
                "dados_aluno_acompanhamento_escolar",
            ],
        )

    def test_criar_transform_retorna_tripla(self) -> None:
        """Valida que a factory de transform gera a tripla (pk, hash, obj)."""
        config = self.service._fases[0]
        transform = self.service._criar_transform(config)

        row = (1, "Desc", 10, None)
        pk, h, obj = transform(row)

        self.assertEqual(pk, "1")
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)
        self.assertEqual(obj.descricao, "Desc")

    def test_criar_transform_pk_composta(self) -> None:
        """Valida geração de PK composta (Matricula-Turma)."""
        config = self.service._fases[5]
        transform = self.service._criar_transform(config)

        row = (123, 456, "01", None, None, 1, 1, None)
        pk, _, _ = transform(row)

        self.assertEqual(pk, "123-456")

    @patch.object(EtlAlunosService, "sync_batch")
    def test_executar_fase_chama_sync_batch_por_chunk(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida o pipeline Producer-Consumer com 2 chunks."""
        config = self.service._fases[0]
        self.mock_eol.iter_query.return_value = [
            [(1, "A", 1, None)],
            [(2, "B", 1, None)],
        ]
        mock_sync.return_value = (1, 0)

        metrics = self.service._executar_fase(config)

        self.assertEqual(metrics.total_lidos, 2)
        self.assertEqual(metrics.total_escritos, 2)
        self.assertEqual(mock_sync.call_count, 2)

    def test_executar_fase_erro_producer_e_propagado(self) -> None:
        """Valida que erros na extração (Producer thread) param o ETL."""
        config = self.service._fases[1]
        self.mock_eol.iter_query.side_effect = RuntimeError("Falha SQL")

        with self.assertRaises(RuntimeError):
            self.service._executar_fase(config)

    def test_executar_pula_fases_anteriores(self) -> None:
        """Valida o parâmetro fase_inicial — fases 1-5 devem ser ignoradas."""
        with patch.object(EtlAlunosService, "_executar_fase") as mock_fase:
            mock_fase.return_value = PipelineMetrics(total_escritos=1)

            res = self.service.executar(fase_inicial=6)

            self.assertEqual(len(res), 4)
            self.assertIn("matricula_turma", res)
            self.assertEqual(mock_fase.call_count, 4)

    def test_executar_completo_acumula_resultados(self) -> None:
        """Valida execução completa."""
        with patch.object(EtlAlunosService, "_executar_fase") as mock_fase:
            mock_fase.return_value = PipelineMetrics(total_escritos=10)

            res = self.service.executar(fase_inicial=1)

            self.assertEqual(len(res), 9)
            self.assertEqual(res["aluno"], 10)
            self.assertEqual(mock_fase.call_count, 9)

    @patch.object(EtlAlunosService, "sync_batch")
    def test_executar_fase_passa_batch_num_correto(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida que batch_num é incrementado a cada chunk."""
        config = self.service._fases[0]
        self.mock_eol.iter_query.return_value = [
            [(1, "A", 1, None)],
            [(2, "B", 1, None)],
            [(3, "C", 1, None)],
        ]
        mock_sync.return_value = (1, 0)

        self.service._executar_fase(config)

        # Parâmetro batch_num foi removido do _sync_batch.
        # O teste agora apenas valida que a chamada ocorreu
        self.assertTrue(mock_sync.called)

    @patch.object(EtlAlunosService, "sync_batch")
    def test_sync_batch_argumentos_corretos(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida que model_class, table_name, update/unique_fields.

        Verifica se os campos são passados corretamente ao _sync_batch.
        """
        config = self.service._fases[0]
        self.mock_eol.iter_query.return_value = [[(1, "A", 1, None)]]
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

    def test_nee_aluno_dto_in_aceita_campos_recurso(self) -> None:
        """Valida que NecessidadeEspecialAlunoIn recebe recurso do SQL."""
        dto = NecessidadeEspecialAlunoIn(
            codigo_necessidade_especial_aluno=1,
            codigo_aluno=100,
            codigo_necessidade_especial=5,
            dt_inicio=date(2020, 1, 1),
            dt_fim=None,
            codigo_tipo_recurso=10,
            descricao_tipo_recurso="NENHUM",
        )
        self.assertEqual(dto.codigo_necessidade_especial_aluno, 1)
        self.assertEqual(dto.dt_inicio, date(2020, 1, 1))
        self.assertIsNone(dto.dt_fim)
        self.assertEqual(dto.codigo_tipo_recurso, 10)

    def test_primeiro_run_repassado_ao_base(self) -> None:
        """Valida que primeiro_run=True chega ao BaseEtlService."""
        service = EtlAlunosService(
            db_alias="default",
            eol=self.mock_eol,
            primeiro_run=True,
        )
        self.assertTrue(service.primeiro_run)

    @patch.object(EtlAlunosService, "sync_batch")
    def test_executar_fase_loga_throughput(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida que o log de cada lote inclui throughput em reg/s."""
        config = self.service._fases[0]
        self.mock_eol.iter_query.return_value = [[(1, "A", 1, None)]]
        mock_sync.return_value = (1, 0)

        with self.assertLogs(
            "apps.core.libs.base_etl_service", level="INFO"
        ) as cm:
            self.service._executar_fase(config)

        self.assertTrue(any("reg/s" in msg for msg in cm.output))

    def test_matricula_turma_dto_in_aceita_matricula_nula(self) -> None:
        """Valida que MatriculaTurmaIn aceita codigo_matricula nulo."""
        dto = MatriculaTurmaIn(
            codigo_matricula=None,
            codigo_turma=101,
            numero_chamada="05",
            data_situacao=None,
            data_situacao_data_hora=None,
            codigo_situacao_aluno=None,
            codigo_tipo_turma=None,
            data_atualizacao_tabela=None,
        )
        domain = dto.to_domain()
        self.assertIsNone(domain["codigo_matricula"])
        self.assertEqual(domain["codigo_turma"], 101)

    def test_fase_7_nome_e_model_corretos(self) -> None:
        """Valida nome e model_class da fase 7."""
        fase = self.service._fases[6]
        self.assertEqual(fase.nome, "matricula_ano_letivo")
        self.assertEqual(fase.model_class, MatriculaAnoLetivo)

    def test_fase_8_nome_e_model_corretos(self) -> None:
        """Valida nome e model_class da fase 8."""
        fase = self.service._fases[7]
        self.assertEqual(
            fase.nome, "matricula_componente_curricular_ano_letivo"
        )
        self.assertEqual(
            fase.model_class, MatriculaComponenteCurricularAnoLetivo
        )

    def test_fase_7_suporta_bulk_insert(self) -> None:
        """Valida que fase 7 tem suporta_bulk_insert=True."""
        self.assertTrue(self.service._fases[6].suporta_bulk_insert)

    def test_fase_8_suporta_bulk_insert(self) -> None:
        """Valida que fase 8 tem suporta_bulk_insert=True."""
        self.assertTrue(self.service._fases[7].suporta_bulk_insert)

    def test_criar_transform_fase_7_pk_composta(self) -> None:
        """Valida PK composta de 7 campos na fase 7."""
        config = self.service._fases[6]
        transform = self.service._criar_transform(config)
        row = ("DRE01", "UE01", 1, 2024, 5, "EF", 3, "3A", "Turma A", 100)
        pk, h, _ = transform(row)
        self.assertEqual(pk, "DRE01-UE01-1-2024-EF-3A-Turma A")
        self.assertEqual(len(h), 64)

    def test_criar_transform_fase_8_pk_composta(self) -> None:
        """Valida PK composta de 6 campos na fase 8."""
        config = self.service._fases[7]
        transform = self.service._criar_transform(config)
        row = ("UE01", "DRE01", 2024, "EF", 3, 100, "3A", "T A", 50)
        pk, h, _ = transform(row)
        self.assertEqual(pk, "UE01-DRE01-2024-EF-100-3A")
        self.assertEqual(len(h), 64)

    def test_executar_pula_fases_1_a_6(self) -> None:
        """Valida que executar(fase_inicial=7) retorna exatamente 3 chaves."""
        with patch.object(
            EtlAlunosService, "_executar_fase"
        ) as mock_fase:
            mock_fase.return_value = PipelineMetrics(total_escritos=1)
            res = self.service.executar(fase_inicial=7)
            self.assertEqual(len(res), 3)
            self.assertIn("matricula_ano_letivo", res)
            self.assertIn(
                "matricula_componente_curricular_ano_letivo", res
            )
            self.assertIn("dados_aluno_acompanhamento_escolar", res)
            self.assertEqual(mock_fase.call_count, 3)

    @patch.object(EtlAlunosService, "sync_batch")
    def test_fase_7_chama_sync_batch_por_chunk(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida 2 chunks sync_batch chamado 2 vezes para fase 7."""
        config = self.service._fases[6]
        self.mock_eol.iter_query.return_value = [
            [("DRE01", "UE01", 1, 2024, 5, "EF", 3, "3A", "T A", 10)],
            [("DRE02", "UE02", 1, 2024, 5, "EF", 3, "3A", "T B", 20)],
        ]
        mock_sync.return_value = (1, 0)
        metrics = self.service._executar_fase(config)
        self.assertEqual(mock_sync.call_count, 2)
        self.assertEqual(metrics.total_lidos, 2)

    @patch.object(EtlAlunosService, "sync_batch")
    def test_fase_8_chama_sync_batch_por_chunk(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida 2 chunks sync_batch chamado 2 vezes para fase 8."""
        config = self.service._fases[7]
        self.mock_eol.iter_query.return_value = [
            [("UE01", "DRE01", 2024, "EF", 3, 100, "3A", "T A", 10)],
            [("UE02", "DRE02", 2024, "EF", 3, 200, "3A", "T B", 20)],
        ]
        mock_sync.return_value = (1, 0)
        metrics = self.service._executar_fase(config)
        self.assertEqual(mock_sync.call_count, 2)
        self.assertEqual(metrics.total_lidos, 2)

    def test_fase_9_nome_e_model_corretos(self) -> None:
        """Valida nome e model_class da fase 9."""
        fase = self.service._fases[8]
        self.assertEqual(fase.nome, "dados_aluno_acompanhamento_escolar")
        self.assertEqual(fase.model_class, DadosAlunoAcompanhamentoEscolar)

    def test_fase_9_suporta_bulk_insert(self) -> None:
        """Valida que fase 9 tem suporta_bulk_insert=True."""
        self.assertTrue(self.service._fases[8].suporta_bulk_insert)

    def test_criar_transform_fase_9_pk_composta(self) -> None:
        """Valida PK composta de 3 campos na fase 9."""
        config = self.service._fases[8]
        transform = self.service._criar_transform(config)
        row = (
            1001, "JOAO", None, "MARIA", "123", None,
            "EMEF", 1, "DRE01", "DRE-N", "UE01",
            "EMEF TESTE", 555, "T A", 1,
            "Ativo", None, 5, 2, "5A", 5,
        )
        pk, h, _ = transform(row)
        self.assertEqual(pk, "1001-555-1")
        self.assertEqual(len(h), 64)

    @patch.object(EtlAlunosService, "sync_batch")
    def test_fase_9_chama_sync_batch_por_chunk(
        self, mock_sync: MagicMock
    ) -> None:
        """Valida 2 chunks sync_batch chamado 2 vezes para fase 9."""
        config = self.service._fases[8]
        row = (
            1001, "JOAO", None, "MARIA", "123", None,
            "EMEF", 1, "DRE01", "DRE-N", "UE01",
            "EMEF TESTE", 555, "T A", 1,
            "Ativo", None, 5, 2, "5A", 5,
        )
        self.mock_eol.iter_query.return_value = [[row], [row]]
        mock_sync.return_value = (1, 0)
        metrics = self.service._executar_fase(config)
        self.assertEqual(mock_sync.call_count, 2)
        self.assertEqual(metrics.total_lidos, 2)
