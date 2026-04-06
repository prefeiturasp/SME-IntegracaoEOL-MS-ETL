"""Interface para acesso ao KeyDB/Redis."""

import logging
from typing import Any, cast

import redis  # type: ignore
from django.conf import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Encapsula operações comuns no KeyDB/Redis."""

    def __init__(self, url: str | None = None) -> None:
        """Inicializa o serviço de cache com a URL configurada ou fornecida."""
        self.url = url or getattr(settings, "URL_KEYDB", "redis://localhost:6379/0")
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        """Retorna o cliente Redis (lazy loading)."""
        if self._client is None:
            self._client = redis.from_url(self.url, decode_responses=True)
        return self._client

    def set_hash(
        self, key: str, mapping: dict[str, Any], expire_seconds: int = 3600
    ) -> None:
        """Salva um dicionário como hash no Redis."""
        try:
            self.client.hset(key, mapping=mapping)
            self.client.expire(key, expire_seconds)
        except Exception as e:
            logger.warning("Erro ao salvar hash no cache %s: %s", key, str(e))

    def get_hash(self, key: str) -> dict[str, str]:
        """Recupera um hash completo do Redis."""
        try:
            return cast(dict[str, str], self.client.hgetall(key))
        except Exception as e:
            logger.warning("Erro ao recuperar hash do cache %s: %s", key, str(e))
            return {}

    def get_hash_value(self, key: str, field: str) -> str | None:
        """Recupera um valor específico de um hash."""
        try:
            return cast(str | None, self.client.hget(key, field))
        except Exception as e:
            logger.warning(
                "Erro ao recuperar campo %s do hash %s: %s", field, key, str(e)
            )
            return None

    def exist_hash_value(self, key: str) -> bool:
        """Verifica se uma chave existe no Redis."""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.warning("Erro ao verificar existência da chave %s: %s", key, str(e))
            return False
