"""Testes basicos de CRUD dos modelos do app escolas."""

from django.test import TestCase

from apps.escolas.models import ConsultaEscolasLog


class ConsultaEscolasLogCrudTestCase(TestCase):
    """Valida operacoes basicas de persistencia de log de consulta."""

    def test_crud_consulta_escolas_log(self) -> None:
        """Cria, atualiza e remove log de consulta."""
        log = ConsultaEscolasLog.objects.create(
            offset_inicial=0,
            limite=100,
            total_retorno=100,
        )
        log.total_retorno = 80
        log.save()

        salvo = ConsultaEscolasLog.objects.get(pk=log.pk)
        self.assertEqual(salvo.total_retorno, 80)

        log.delete()
        self.assertFalse(ConsultaEscolasLog.objects.filter(pk=log.pk).exists())
