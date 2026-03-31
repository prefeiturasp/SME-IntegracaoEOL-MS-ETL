"""Testes de string representation dos modelos de programas."""

from django.test import TestCase
from apps.programas.models import Parametro, ComponenteCurricularApi

class ProgramasModelsTest(TestCase):
    """Testes para cobrir métodos __str__ do app programas."""

    def test_parametro_str(self) -> None:
        """Verifica representação de parâmetros."""
        p = Parametro(nome="versao", valor="1.0")
        self.assertEqual(str(p), "versao=1.0")

    def test_componente_api_str(self) -> None:
        """Verifica representação de componentes da API."""
        c = ComponenteCurricularApi(codigo_componente=123, descricao="MATEMATICA")
        self.assertEqual(str(c), "123 - MATEMATICA")
