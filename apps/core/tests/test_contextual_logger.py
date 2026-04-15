"""Testes para o ContextualLogger."""

import logging
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.core.libs.contextual_logger import ContextualLogger


class ContextualLoggerInitTestCase(TestCase):
    def test_extra_none_vira_dict_vazio(self):
        base_logger = logging.getLogger("test")
        cl = ContextualLogger(base_logger, None)
        self.assertEqual(cl.extra, {})

    def test_extra_nao_dict_levanta_value_error(self):
        base_logger = logging.getLogger("test")
        with self.assertRaises(ValueError):
            ContextualLogger(base_logger, "invalido")


class ContextualLoggerProcessTestCase(TestCase):
    def setUp(self):
        base_logger = logging.getLogger("test")
        self.cl = ContextualLogger(base_logger, {"execution_id": "uuid-1", "dominio": "institucional"})

    def test_merge_contexto_fixo_com_extra_por_chamada(self):
        _, kwargs = self.cl.process("msg", {"extra": {"etapa": "leitura"}})
        self.assertEqual(kwargs["extra"]["execution_id"], "uuid-1")
        self.assertEqual(kwargs["extra"]["dominio"], "institucional")
        self.assertEqual(kwargs["extra"]["etapa"], "leitura")

    def test_extra_por_chamada_tem_precedencia_sobre_fixo(self):
        _, kwargs = self.cl.process("msg", {"extra": {"dominio": "professores"}})
        self.assertEqual(kwargs["extra"]["dominio"], "professores")

    def test_extra_ausente_usa_apenas_contexto_fixo(self):
        _, kwargs = self.cl.process("msg", {})
        self.assertEqual(kwargs["extra"]["execution_id"], "uuid-1")

    def test_extra_nao_dict_levanta_value_error(self):
        with self.assertRaises(ValueError):
            self.cl.process("msg", {"extra": "invalido"})


class ContextualLoggerUpdateContextTestCase(TestCase):
    def setUp(self):
        base_logger = logging.getLogger("test")
        self.cl = ContextualLogger(base_logger, {"dominio": "institucional"})

    def test_adiciona_novo_campo(self):
        self.cl.update_context(execution_id="uuid-99")
        self.assertEqual(self.cl.extra["execution_id"], "uuid-99")

    def test_modifica_campo_existente(self):
        self.cl.update_context(dominio="alunos")
        self.assertEqual(self.cl.extra["dominio"], "alunos")

    def test_preserva_campos_nao_modificados(self):
        self.cl.update_context(batch_id=3)
        self.assertEqual(self.cl.extra["dominio"], "institucional")


class ContextualLoggerGetEtlLoggerTestCase(TestCase):
    def test_prefixo_etl_no_nome_do_logger(self):
        cl = ContextualLogger.get_etl_logger("apps.core.libs.base_etl_command", dominio="x")
        self.assertEqual(cl.logger.name, "etl_apps.core.libs.base_etl_command")

    def test_campos_none_sao_filtrados(self):
        cl = ContextualLogger.get_etl_logger("mod", dominio="x", execution_id=None)
        self.assertNotIn("execution_id", cl.extra)
        self.assertIn("dominio", cl.extra)

    def test_retorna_instancia_de_contextual_logger(self):
        cl = ContextualLogger.get_etl_logger("mod")
        self.assertIsInstance(cl, ContextualLogger)
