"""Testes para o RepositorioCoreSSO."""

from unittest.mock import MagicMock

from django.test import TestCase

from apps.institucional.libs.repositorio_core_sso import RepositorioCoreSSO


class TestRepositorioCoreSSO(TestCase):
    """Testes unitários para RepositorioCoreSSO."""

    def setUp(self) -> None:
        """Configura o repositório com mock da factory."""
        self.mock_factory = MagicMock()
        self.repo = RepositorioCoreSSO(factory=self.mock_factory)

    def test_obter_codigos_integracao_vazio_nao_consulta(self) -> None:
        """Valida que lista vazia retorna lista vazia imediatamente."""
        resultado = self.repo.obter_codigos_integracao_ues([])
        self.assertEqual(resultado, [])
        self.mock_factory.executar_consulta.assert_not_called()

    def test_obter_codigos_integracao_com_chunking(self) -> None:
        """Valida que lista grande e dividida em lotes de 1000."""
        # Cria 2500 IDs para forçar 3 chamadas (1000 + 1000 + 500)
        codigo_ues = [str(i) for i in range(2500)]

        # Simula retornos para cada chamada
        self.mock_factory.executar_consulta.side_effect = [
            [(str(i), "UE", "INT") for i in range(1000)],
            [(str(i), "UE", "INT") for i in range(1000, 2000)],
            [(str(i), "UE", "INT") for i in range(2000, 2500)],
        ]

        resultado = self.repo.obter_codigos_integracao_ues(codigo_ues)

        self.assertEqual(len(resultado), 2500)
        self.assertEqual(self.mock_factory.executar_consulta.call_count, 3)

        # Valida que o SQL de cada chamada tem a quantidade correta
        # Primeira chamada (1000 placeholders)
        args_primeira = self.mock_factory.executar_consulta.call_args_list[0]
        sql_primeira = args_primeira[0][0]
        self.assertEqual(sql_primeira.count("%s"), 1000)

        # Terceira chamada (500 placeholders)
        args_terceira = self.mock_factory.executar_consulta.call_args_list[2]
        sql_terceira = args_terceira[0][0]
        self.assertEqual(sql_terceira.count("%s"), 500)
