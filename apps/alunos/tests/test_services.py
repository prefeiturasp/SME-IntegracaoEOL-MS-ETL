from unittest.mock import MagicMock, patch
from uuid import uuid4
from django.test import TestCase
from apps.alunos.services import (
    EtlAlunosService, SQL_TIPO_NEE
)
from apps.core.libs.base_etl_service import PipelineMetrics

class TestAlunosService(TestCase):
    """Testes de integração e unidade para EtlAlunosService."""

    def setUp(self) -> None:
        self.mock_eol = MagicMock()
        self.service = EtlAlunosService(eol=self.mock_eol, id_execucao=uuid4())

    def test_popular_tipos_nee(self) -> None:
        self.mock_eol.iter_query.return_value = iter([[(1, 'Desc', 1, None)]])
        with patch.object(EtlAlunosService, "sync_table") as mock_sync:
            mock_sync.return_value = PipelineMetrics(total_lidos=1)
            self.service.popular_tipos_nee()
            self.assertTrue(self.mock_eol.iter_query.called)
            self.assertTrue(mock_sync.called)

    def test_popular_alunos(self) -> None:
        self.mock_eol.iter_query.return_value = iter([[(1, 'N', 'S', None, 1, 'Na', 'Ni', 'Cp', 'Ra')]])
        with patch.object(EtlAlunosService, "sync_table") as mock_sync:
            mock_sync.return_value = PipelineMetrics(total_lidos=1)
            self.service.popular_alunos()
            self.assertTrue(mock_sync.called)

    def test_popular_responsaveis(self) -> None:
        self.mock_eol.iter_query.return_value = iter([[(1, 1, 1, 'N', 'C', 'E', 'D', 'N', 1, 'L', 1, None)]])
        with patch.object(EtlAlunosService, "sync_table") as mock_sync:
            mock_sync.return_value = PipelineMetrics(total_lidos=1)
            self.service.popular_responsaveis()
            self.assertTrue(mock_sync.called)

    def test_popular_nee_alunos(self) -> None:
        self.mock_eol.iter_query.return_value = iter([[(1, 1, 1, None, None)]])
        with patch.object(EtlAlunosService, "sync_table") as mock_sync:
            mock_sync.return_value = PipelineMetrics(total_lidos=1)
            self.service.popular_nee_alunos()
            self.assertTrue(mock_sync.called)

    def test_popular_matriculas(self) -> None:
        self.mock_eol.iter_query.return_value = iter([[(1, 1, 'UE', None, 2023, 1, 'Ativa')]])
        with patch.object(EtlAlunosService, "sync_table") as mock_sync:
            mock_sync.return_value = PipelineMetrics(total_lidos=1)
            self.service.popular_matriculas()
            self.assertTrue(mock_sync.called)

    def test_popular_matricula_turma(self) -> None:
        self.mock_eol.iter_query.return_value = iter([[(1, 55, 'A1', None)]])
        with patch.object(EtlAlunosService, "sync_table") as mock_sync:
            mock_sync.return_value = PipelineMetrics(total_lidos=1)
            self.service.popular_matricula_turmas()
            self.assertTrue(mock_sync.called)

    def test_executar_completo(self) -> None:
        with patch.object(EtlAlunosService, "popular_tipos_nee") as m1, \
             patch.object(EtlAlunosService, "popular_alunos") as m2, \
             patch.object(EtlAlunosService, "popular_responsaveis") as m3, \
             patch.object(EtlAlunosService, "popular_nee_alunos") as m4, \
             patch.object(EtlAlunosService, "popular_matriculas") as m5, \
             patch.object(EtlAlunosService, "popular_matricula_turmas") as m6:
            
            for m in [m1, m2, m3, m4, m5, m6]:
                m.return_value = PipelineMetrics(total_escritos=1)
            
            res = self.service.executar(fase_inicial=1)
            self.assertEqual(len(res), 6)
            self.assertEqual(sum(res.values()), 6)

    def test_executar_fase_intermediaria(self) -> None:
        with patch.object(EtlAlunosService, "popular_tipos_nee") as m1, \
             patch.object(EtlAlunosService, "popular_matricula_turmas") as m6:
            
            m6.return_value = PipelineMetrics(total_escritos=5)
            res = self.service.executar(fase_inicial=6)
            
            self.assertNotIn("tipo_nee", res)
            self.assertEqual(res["matricula_turma"], 5)
            self.assertFalse(m1.called)
            self.assertTrue(m6.called)
