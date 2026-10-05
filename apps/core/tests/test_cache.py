"""Testes para o serviço de cache."""

from unittest.mock import patch

from django.test import TestCase

from apps.core.libs.cache import CacheService


class CacheServiceTestCase(TestCase):
    """Valida operações de cache no Redis."""

    def setUp(self) -> None:
        """Mocka o cliente Redis."""
        self.patcher = patch("apps.core.libs.cache.redis.from_url")
        self.mock_from_url = self.patcher.start()
        self.mock_client = self.mock_from_url.return_value
        self.service = CacheService()

    def tearDown(self) -> None:
        """Encerra mocks."""
        self.patcher.stop()

    def test_set_e_get_hash(self) -> None:
        """Verifica persistência de dicionário no cache."""
        dados = {"a": "1", "b": "2"}
        self.mock_client.hgetall.return_value = dados

        self.service.set_hash("teste", dados)
        self.mock_client.hset.assert_called_with("teste", mapping=dados)

        resultado = self.service.get_hash("teste")
        self.assertEqual(resultado, dados)

    def test_get_hash_value_individual(self) -> None:
        """Verifica recuperação de campo específico."""
        self.mock_client.hget.return_value = "100"
        self.assertEqual(self.service.get_hash_value("teste", "a"), "100")

        self.mock_client.hget.return_value = None
        self.assertIsNone(self.service.get_hash_value("teste", "invalido"))

    def test_get_hash_vazio_em_erro(self) -> None:
        """Verifica que erros não derrubam a aplicação e retornam vazio/None."""
        self.mock_client.hgetall.side_effect = Exception("Redis Down")
        self.assertEqual(self.service.get_hash("err"), {})

        self.mock_client.hget.side_effect = Exception("Redis Down")
        self.assertIsNone(self.service.get_hash_value("err", "f"))

        self.mock_client.hset.side_effect = Exception("Redis Down")
        # Não deve dar raise
        self.service.set_hash("err", {"x": "y"})

    def test_exist_hash_value(self) -> None:
        """Verifica se a chave existe no cache."""
        # Sucesso: existe
        self.mock_client.exists.return_value = 1
        self.assertTrue(self.service.exist_hash_value("teste"))
        self.mock_client.exists.assert_called_with("teste")

        # Sucesso: não existe
        self.mock_client.exists.return_value = 0
        self.assertFalse(self.service.exist_hash_value("vazio"))

        # Erro de conexão
        self.mock_client.exists.side_effect = Exception("Redis Down")
        self.assertFalse(self.service.exist_hash_value("err"))
