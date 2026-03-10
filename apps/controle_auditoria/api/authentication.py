"""Autenticacao por API key para endpoints DRF."""

from dataclasses import dataclass
import secrets

from django.conf import settings
from rest_framework import authentication
from rest_framework import exceptions


@dataclass
class UsuarioApiKey:
    """Representa autenticacao valida por chave de API."""

    username: str = "api_key_user"
    is_authenticated: bool = True
    is_active: bool = True


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """Autentica requests via header de API key."""

    keyword = "X-API-Key"

    def authenticate(self, request):
        chave_esperada = settings.API_KEY
        if not chave_esperada:
            raise exceptions.AuthenticationFailed("API key nao configurada")

        chave_recebida = request.headers.get(self.keyword)
        if not chave_recebida:
            return None

        if not secrets.compare_digest(chave_recebida, chave_esperada):
            raise exceptions.AuthenticationFailed("API key invalida")

        return (UsuarioApiKey(), None)
