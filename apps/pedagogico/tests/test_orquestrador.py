from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

from django.test import TestCase

from apps.pedagogico.orquestrador import EtlPedagogicoOrquestrador


class TestEtlPedagogicoOrquestrador(TestCase):
    """Testes específicos do EtlPedagogicoOrquestrador."""

    def _make_orquestrador(self, **kwargs: Any) -> EtlPedagogicoOrquestrador:
        kwargs.setdefault("id_execucao", uuid4())
        return EtlPedagogicoOrquestrador(
            db_alias="pedagogico_db",
            eol=MagicMock(),
            **kwargs,
        )

    def test_dominio_e_15_fases(self) -> None:
        """Pedagógico deve expor as fases ao orquestrador."""
        orq = self._make_orquestrador()
        self.assertEqual(len(orq.service._fases), 15)

    def test_id_execucao_mantido(self) -> None:
        """Valida que o orquestrador aceita e mantém um id_execucao."""
        id_fixo = uuid4()
        orq = self._make_orquestrador(id_execucao=id_fixo)
        self.assertEqual(orq.id_execucao, id_fixo)

    def test_get_meta_fase_10(self) -> None:
        """Valida metadados da fase 10 de agrupamento copiado."""
        orq = self._make_orquestrador()
        meta = orq.service.get_meta(
            orq.service._fases[9], 10, 15, orq.id_execucao
        )

        self.assertEqual(meta.numero_fase, 10)
        self.assertEqual(
            meta.nome,
            "agrupamento_atribuicao_territorio_saber",
        )
        self.assertIn(
            "apps.core.tasks.processar_chunk", meta.task_processamento_path
        )
