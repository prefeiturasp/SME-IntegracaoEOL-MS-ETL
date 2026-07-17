"""Testes para EtlAlunosOrquestrador."""

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import SimpleTestCase

from apps.alunos.orquestrador import EtlAlunosOrquestrador


class TestEtlAlunosOrquestrador(SimpleTestCase):
    """Testes para o orquestrador assíncrono de Alunos."""

    def _make_orquestrador(self, **kwargs: Any) -> EtlAlunosOrquestrador:
        mock_eol = MagicMock()
        kwargs.setdefault("id_execucao", uuid4())
        return EtlAlunosOrquestrador(
            db_alias="alunos_db",
            eol=mock_eol,
            **kwargs,
        )

    @patch("apps.core.libs.base_etl_orquestrador.finalizar_fase")
    @patch("apps.core.libs.base_etl_orquestrador.processar_chunk")
    @patch("apps.core.libs.base_etl_orquestrador.BaseEtlChunk")
    @patch("apps.core.libs.base_etl_orquestrador.group")
    @patch("apps.core.libs.base_etl_orquestrador.chord")
    def test_lancar_publica_chord_e_encerra(
        self,
        mock_chord: MagicMock,
        mock_group: MagicMock,
        mock_leitor_cls: MagicMock,
        mock_proc: MagicMock,
        mock_finalizar: MagicMock,
    ) -> None:
        """Valida o lançamento inicial da fase 1 via chord."""
        mock_leitor = MagicMock()
        mock_leitor.criar_grupo.return_value = ["task1"]
        mock_leitor_cls.return_value = mock_leitor

        orq = self._make_orquestrador()
        orq.lancar()

        mock_chord.assert_called_once()
        mock_finalizar.s.assert_called_once()

    @patch("apps.core.libs.base_etl_orquestrador.finalizar_fase")
    @patch("apps.core.libs.base_etl_orquestrador.processar_chunk")
    @patch("apps.core.libs.base_etl_orquestrador.BaseEtlChunk")
    @patch("apps.core.libs.base_etl_orquestrador.group")
    @patch("apps.core.libs.base_etl_orquestrador.chord")
    def test_todas_fases_passadas_ao_callback(
        self,
        mock_chord: MagicMock,
        mock_group: MagicMock,
        mock_leitor_cls: MagicMock,
        mock_proc: MagicMock,
        mock_finalizar: MagicMock,
    ) -> None:
        """Valida que todas as fases são passadas ao callback do chord."""
        mock_leitor = MagicMock()
        mock_leitor.criar_grupo.return_value = ["task1"]
        mock_leitor_cls.return_value = mock_leitor

        orq = self._make_orquestrador()
        orq.lancar()

        self.assertTrue(mock_finalizar.s.called)
        args, _ = mock_finalizar.s.call_args
        meta_dict = args[0]
        self.assertEqual(meta_dict["total_fases"], len(orq.service._fases))

    @patch("apps.core.libs.base_etl_orquestrador.finalizar_fase")
    @patch("apps.core.libs.base_etl_orquestrador.processar_chunk")
    @patch("apps.core.libs.base_etl_orquestrador.BaseEtlChunk")
    @patch("apps.core.libs.base_etl_orquestrador.group")
    @patch("apps.core.libs.base_etl_orquestrador.chord")
    def test_sem_chunks_nao_lanca_chord(
        self,
        mock_chord: MagicMock,
        mock_group: MagicMock,
        mock_leitor_cls: MagicMock,
        mock_proc: MagicMock,
        mock_finalizar: MagicMock,
    ) -> None:
        """Valida que fase sem chunks dispara apply_async direto."""
        mock_leitor = MagicMock()
        mock_leitor.criar_grupo.return_value = []
        mock_leitor_cls.return_value = mock_leitor

        orq = self._make_orquestrador()
        orq.lancar()

        mock_chord.assert_not_called()
        mock_finalizar.apply_async.assert_called_once()

    def test_lancar_com_id_execucao_especifico(self) -> None:
        """Valida que o orquestrador aceita e mantém um id_execucao."""
        id_fixo = uuid4()
        orq = self._make_orquestrador(id_execucao=id_fixo)
        self.assertEqual(orq.id_execucao, id_fixo)

    def test_get_meta_fase_3(self) -> None:
        """Valida que get_meta resolve corretamente metadados da fase 3."""
        orq = self._make_orquestrador()
        meta = orq.service.get_meta(
            orq.service._fases[2], 3, 6, orq.id_execucao
        )

        self.assertEqual(meta.numero_fase, 3)
        self.assertEqual(meta.nome, "responsavel_aluno")
        self.assertIn(
            "apps.core.tasks.processar_chunk",
            meta.task_processamento_path,
        )
