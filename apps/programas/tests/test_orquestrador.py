"""Testes para EtlProgramasOrquestrador."""

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase

from apps.programas.orquestrador import EtlProgramasOrquestrador

_BASE = "apps.core.libs.base_etl_orquestrador"


@patch(f"{_BASE}.finalizar_fase")
@patch(f"{_BASE}.processar_chunk")
@patch(f"{_BASE}.BaseEtlChunk")
@patch(f"{_BASE}.group")
@patch(f"{_BASE}.chord")
class TestEtlProgramasOrquestradorLancamento(TestCase):
    """Cenários de lançamento do chord via EtlProgramasOrquestrador."""

    databases = {"default", "eol_db", "programas_db"}

    def _make_orquestrador(self, **kwargs: Any) -> EtlProgramasOrquestrador:
        kwargs.setdefault("id_execucao", uuid4())
        return EtlProgramasOrquestrador(
            db_alias="programas_db",
            eol=MagicMock(),
            **kwargs,
        )

    def _configurar_leitor(
        self, mock_leitor_cls: MagicMock, tasks: list[str]
    ) -> None:
        """Configura o mock do BaseEtlChunk para retornar tasks dadas."""
        mock_leitor = MagicMock()
        mock_leitor.criar_grupo.return_value = tasks
        mock_leitor_cls.return_value = mock_leitor

    def test_lancar_publica_chord_e_encerra(
        self,
        mock_chord: MagicMock,
        _mock_group: MagicMock,
        mock_leitor_cls: MagicMock,
        _mock_proc: MagicMock,
        mock_finalizar: MagicMock,
    ) -> None:
        """Valida o lançamento inicial da fase 1 via chord."""
        self._configurar_leitor(mock_leitor_cls, ["task1"])

        self._make_orquestrador().lancar()

        mock_chord.assert_called_once()
        mock_finalizar.s.assert_called_once()

    def test_todas_fases_passadas_ao_callback(
        self,
        _mock_chord: MagicMock,
        _mock_group: MagicMock,
        mock_leitor_cls: MagicMock,
        _mock_proc: MagicMock,
        mock_finalizar: MagicMock,
    ) -> None:
        """Valida que todas as 6 fases são passadas ao callback do chord."""
        self._configurar_leitor(mock_leitor_cls, ["task1"])

        self._make_orquestrador().lancar()

        self.assertTrue(mock_finalizar.s.called)
        meta_dict = mock_finalizar.s.call_args.args[0]
        self.assertEqual(meta_dict["total_fases"], 6)

    def test_sem_chunks_nao_lanca_chord(
        self,
        mock_chord: MagicMock,
        _mock_group: MagicMock,
        mock_leitor_cls: MagicMock,
        _mock_proc: MagicMock,
        mock_finalizar: MagicMock,
    ) -> None:
        """Valida que fase sem chunks dispara apply_async direto."""
        self._configurar_leitor(mock_leitor_cls, [])

        self._make_orquestrador().lancar()

        mock_chord.assert_not_called()
        mock_finalizar.apply_async.assert_called_once()


class TestEtlProgramasOrquestradorEstado(TestCase):
    """Cenários de estado/metadata do orquestrador (sem chord)."""

    databases = {"default", "eol_db", "programas_db"}

    def _make_orquestrador(self, **kwargs: Any) -> EtlProgramasOrquestrador:
        kwargs.setdefault("id_execucao", uuid4())
        return EtlProgramasOrquestrador(
            db_alias="programas_db",
            eol=MagicMock(),
            **kwargs,
        )

    def test_lancar_com_id_execucao_especifico(self) -> None:
        """Valida que o orquestrador aceita e mantém um id_execucao."""
        id_fixo = uuid4()
        orq = self._make_orquestrador(id_execucao=id_fixo)
        self.assertEqual(orq.id_execucao, id_fixo)

    def test_get_meta_fase_3(self) -> None:
        """Valida que get_meta resolve corretamente metadados da fase 3."""
        orq = self._make_orquestrador()
        meta = orq.service.get_meta(
            orq.service._fases[2], 3, 5, orq.id_execucao
        )

        self.assertEqual(meta.numero_fase, 3)
        self.assertEqual(meta.nome, "turma_programa")
        self.assertIn(
            "apps.core.tasks.processar_chunk", meta.task_processamento_path
        )
