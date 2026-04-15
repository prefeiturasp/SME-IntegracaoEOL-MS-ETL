"""Testes para EtlInstitucionalOrquestrador."""

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase

from apps.institucional.orquestrador import EtlInstitucionalOrquestrador


class TestEtlInstitucionalOrquestrador(TestCase):
    """Testes para o orquestrador assíncrono de Institucional."""

    databases = {"default", "eol_db", "institucional_db"}

    def _make_orquestrador(self, **kwargs: Any) -> EtlInstitucionalOrquestrador:
        mock_eol = MagicMock()
        kwargs.setdefault("id_execucao", uuid4())
        return EtlInstitucionalOrquestrador(
            db_alias="institucional_db",
            eol=mock_eol,
            **kwargs,
        )

    @patch("apps.core.libs.base_etl_orquestrador.finalizar_fase")
    @patch("apps.core.libs.base_etl_orquestrador.processar_chunk")
    @patch("apps.core.libs.base_etl_orquestrador.BaseEtlChunk")
    @patch("apps.core.libs.base_etl_orquestrador.group")
    @patch("apps.core.libs.base_etl_orquestrador.chord")
    def test_lancar_publica_chord(
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
    def test_total_fases_no_callback(
        self,
        mock_chord: MagicMock,
        mock_group: MagicMock,
        mock_leitor_cls: MagicMock,
        mock_proc: MagicMock,
        mock_finalizar: MagicMock,
    ) -> None:
        """Valida que as 4 fases são passadas ao callback do chord."""
        mock_leitor = MagicMock()
        mock_leitor.criar_grupo.return_value = ["task1"]
        mock_leitor_cls.return_value = mock_leitor

        orq = self._make_orquestrador()
        orq.lancar()

        self.assertTrue(mock_finalizar.s.called)
        args, _ = mock_finalizar.s.call_args
        meta_dict = args[0]
        self.assertEqual(meta_dict["total_fases"], 4)

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
        """Fase sem chunks dispara apply_async direto, sem chord."""
        mock_leitor = MagicMock()
        mock_leitor.criar_grupo.return_value = []
        mock_leitor_cls.return_value = mock_leitor

        orq = self._make_orquestrador()
        orq.lancar()

        mock_chord.assert_not_called()
        mock_finalizar.apply_async.assert_called_once()

    def test_lancar_com_id_execucao_especifico(self) -> None:
        """Orquestrador mantém o id_execucao fornecido."""
        id_fixo = uuid4()
        orq = self._make_orquestrador(id_execucao=id_fixo)
        self.assertEqual(orq.id_execucao, id_fixo)

    def test_get_meta_fase_1(self) -> None:
        """get_meta resolve metadados corretos para a fase 1 (DRE)."""
        orq = self._make_orquestrador()
        meta = orq.service.get_meta(
            orq.service._fases[0], 1, 4, orq.id_execucao
        )

        self.assertEqual(meta.numero_fase, 1)
        self.assertEqual(meta.nome, "dre")
        self.assertIn("apps.core.tasks.processar_chunk", meta.task_processamento_path)

    def test_get_meta_fase_4(self) -> None:
        """get_meta resolve metadados corretos para a fase 4 (UE)."""
        orq = self._make_orquestrador()
        meta = orq.service.get_meta(
            orq.service._fases[3], 4, 4, orq.id_execucao
        )

        self.assertEqual(meta.numero_fase, 4)
        self.assertEqual(meta.nome, "unidade_educacional")

    def test_dominio_padrao_e_institucional(self) -> None:
        """Orquestrador inicializa com domínio 'institucional' por padrão."""
        orq = self._make_orquestrador()
        self.assertEqual(orq._dominio, "institucional")
