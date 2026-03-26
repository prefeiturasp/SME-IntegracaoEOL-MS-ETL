"""Testes de biblioteca do app escolas."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.escolas.libs.cliente_legado import ClienteLegadoEscolas
from apps.escolas.libs.servico_offset import ServicoEscolasOffset
from apps.escolas.models import ConsultaEscolasLog


class ClienteLegadoEscolasTestCase(TestCase):
    """Valida cliente de leitura no banco legado."""

    @patch("apps.escolas.libs.cliente_legado.EOLConnectionFactory")
    def test_deve_listar_por_offset(self, factory_mock: MagicMock) -> None:
        """Converte linhas do cursor em lista de dicionários."""
        cursor = MagicMock()
        cursor.description = [("codigo_escola",), ("nome_escola",)]
        cursor.fetchall.return_value = [
            ("000001", "Escola A"),
            ("000002", "Escola B"),
        ]

        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor

        factory = MagicMock()
        factory.obter_conexao.return_value = conn

        factory_mock.return_value = factory

        cliente = ClienteLegadoEscolas()
        resultado = cliente.listar_por_offset(limite=2, offset=0)

        self.assertEqual(
            resultado,
            [
                {"codigo_escola": "000001", "nome_escola": "Escola A"},
                {"codigo_escola": "000002", "nome_escola": "Escola B"},
            ],
        )


class ServicoEscolasOffsetTestCase(TestCase):
    """Valida paginação e logs de execução do serviço."""

    @patch("apps.escolas.libs.servico_offset.ClienteLegadoEscolas")
    def test_deve_parar_quando_lote_vazio(self, cliente_cls_mock: MagicMock) -> None:
        """Quando cliente retorna vazio, serviço finaliza sem logs."""
        cliente = MagicMock()
        cliente.listar_por_offset.return_value = []
        cliente_cls_mock.return_value = cliente

        servico = ServicoEscolasOffset()
        resultado = servico.listar_volume(volume=100, offset_inicial=0)

        self.assertEqual(resultado, [])
        self.assertEqual(ConsultaEscolasLog.objects.count(), 0)

    @patch("apps.escolas.libs.servico_offset.ClienteLegadoEscolas")
    def test_deve_ler_em_multiplas_paginas(self, cliente_cls_mock: MagicMock) -> None:
        """Lê em blocos e cria log para cada bloco."""
        cliente = MagicMock()
        cliente.listar_por_offset.side_effect = [
            [{"codigo_escola": "1"}] * 100,
            [{"codigo_escola": "2"}] * 50,
        ]
        cliente_cls_mock.return_value = cliente

        servico = ServicoEscolasOffset()
        resultado = servico.listar_volume(volume=150, offset_inicial=0)

        self.assertEqual(len(resultado), 150)
        self.assertEqual(ConsultaEscolasLog.objects.count(), 2)
        primeiro_log = ConsultaEscolasLog.objects.order_by("id").first()
        self.assertEqual(primeiro_log.offset_inicial, 0)
        self.assertEqual(primeiro_log.limite, 100)

    @patch("apps.escolas.libs.servico_offset.ClienteLegadoEscolas")
    def test_deve_parar_quando_lote_menor_que_limite(
        self, cliente_cls_mock: MagicMock
    ) -> None:
        """Interrompe quando retorna menos registros do que o limite."""
        cliente = MagicMock()
        cliente.listar_por_offset.return_value = [{"codigo_escola": "1"}] * 30
        cliente_cls_mock.return_value = cliente

        servico = ServicoEscolasOffset()
        resultado = servico.listar_volume(volume=100, offset_inicial=0)

        self.assertEqual(len(resultado), 30)
        self.assertEqual(ConsultaEscolasLog.objects.count(), 1)
