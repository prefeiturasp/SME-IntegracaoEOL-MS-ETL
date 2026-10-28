"""Valida as transições de carga que protegem as leituras do domínio."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

from django.db import connections
from django.test import TestCase, TransactionTestCase

from apps.professores.controle_cache import registrar_carga
from apps.professores.models import ControleCargaProfessores


class ControleCacheTest(TestCase):
    """Confere isolamento de gerações, falhas e cargas sobrepostas."""

    databases = ["default", "professores_db"]

    def estado(self):
        return ControleCargaProfessores.objects.using("professores_db").get(
            pk=1
        )

    def test_primeira_carga_completa_libera_fontes_so_ao_final(self):
        with registrar_carga(completa=True):
            estado = self.estado()
            self.assertEqual(len(estado.cargas_ativas), 1)
            geracao = estado.geracao

        estado = self.estado()
        self.assertEqual(estado.cargas_ativas, [])
        self.assertFalse(estado.falha)
        self.assertNotEqual(estado.geracao, geracao)

    def test_falha_bloqueia_ate_carga_completa_bem_sucedida(self):
        with (
            self.assertRaisesRegex(ValueError, "origem"),
            registrar_carga(completa=True),
        ):
            raise ValueError("origem")
        self.assertTrue(self.estado().falha)

        with registrar_carga(completa=False):
            pass
        self.assertTrue(self.estado().falha)

        with registrar_carga(completa=True):
            pass
        self.assertFalse(self.estado().falha)

    def test_conclusao_de_uma_carga_nao_libera_outra_ativa(self):
        with registrar_carga(completa=True):
            with registrar_carga(completa=True):
                self.assertEqual(len(self.estado().cargas_ativas), 2)
            self.assertEqual(len(self.estado().cargas_ativas), 1)
        self.assertEqual(self.estado().cargas_ativas, [])

    def test_falha_concorrente_nao_e_apagada_pela_outra_conclusao(self):
        with (
            registrar_carga(completa=True),
            self.assertRaises(ValueError),
            registrar_carga(completa=True),
        ):
            raise ValueError("origem")
        self.assertTrue(self.estado().falha)

    def test_primeira_carga_parcial_nao_declara_dominio_completo(self):
        with registrar_carga(completa=False):
            pass
        self.assertTrue(self.estado().falha)

    def test_amostra_nao_relibera_fontes_previamente_completas(self):
        with registrar_carga(completa=True):
            pass
        with registrar_carga(completa=False, amostral=True):
            pass
        self.assertTrue(self.estado().falha)


class ConcorrenciaControleCacheTest(TransactionTestCase):
    """Confere registros de cargas em conexões independentes."""

    databases = ["default", "professores_db"]

    def test_cargas_concorrentes_preservam_todos_os_registros(self):
        barreira = Barrier(4)
        liberar = Event()

        def executar():
            try:
                with registrar_carga(completa=True):
                    barreira.wait(timeout=10)
                    liberar.wait(timeout=10)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=3) as pool:
            futuros = [pool.submit(executar) for _ in range(3)]
            try:
                barreira.wait(timeout=10)
                estado = ControleCargaProfessores.objects.using(
                    "professores_db"
                ).get(pk=1)
                self.assertEqual(len(estado.cargas_ativas), 3)
            finally:
                liberar.set()
            for futuro in futuros:
                futuro.result(timeout=10)
        estado.refresh_from_db(using="professores_db")
        self.assertEqual(estado.cargas_ativas, [])
        self.assertFalse(estado.falha)
