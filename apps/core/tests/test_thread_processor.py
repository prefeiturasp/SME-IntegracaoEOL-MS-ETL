"""Testes unitários do ThreadPoolProcessor."""

import hashlib
import logging
import time

from django.test import TestCase, override_settings

from apps.core.libs.thread_processor import ThreadPoolProcessor


@override_settings(THREAD_POOL_MAX_WORKERS=4, THREAD_POOL_CHUNK_TIMEOUT=120)
class TestThreadPoolProcessor(TestCase):
    """Cenários obrigatórios do ThreadPoolProcessor."""

    def setUp(self) -> None:
        """Inicializa o processador com prefixo de teste."""
        self.processor = ThreadPoolProcessor(prefixo_log="TEST")

    def test_lista_vazia_retorna_lista_vazia(self) -> None:
        """Lista vazia retorna ``[]`` sem criar threads."""
        resultado = self.processor.processar([], lambda x: x)
        self.assertEqual(resultado, [])

    def test_preserva_ordem_dos_resultados(self) -> None:
        """N itens com função pura preserva a ordem dos resultados."""
        items = list(range(20))
        resultado = self.processor.processar(items, lambda x: x * 2)
        self.assertEqual(resultado, [x * 2 for x in items])

    def test_erro_em_thread_e_propagado(self) -> None:
        """Exceção em uma thread é propagada após as demais concluírem."""

        def func_com_erro(x: int) -> int:
            if x == 5:
                raise ValueError("erro no item 5")
            return x

        logger = logging.getLogger("apps.core.libs.thread_processor")
        logger.disabled = True
        try:
            with self.assertRaises(ValueError, msg="erro no item 5"):
                self.processor.processar(list(range(10)), func_com_erro)
        finally:
            logger.disabled = False

    def test_timeout_lanca_timeout_error(self) -> None:
        """Timeout excedido lança ``TimeoutError``.

        Exige o caminho paralelo: com ``max_workers=1`` o processamento é
        serial e não há future para cancelar por timeout.
        """
        processor = ThreadPoolProcessor(
            max_workers=2, timeout=1, prefixo_log="TEST_TIMEOUT"
        )

        def func_lenta(x: int) -> int:
            time.sleep(3)
            return x

        with self.assertRaises(TimeoutError):
            processor.processar(list(range(5)), func_lenta)

    def test_max_workers_1_resultado_identico_serial(self) -> None:
        """``max_workers=1`` produz resultado idêntico ao processamento serial."""
        processor = ThreadPoolProcessor(
            max_workers=1, prefixo_log="TEST_SERIAL"
        )
        items = list(range(15))
        resultado = processor.processar(items, lambda x: x**2)
        esperado = [x**2 for x in items]
        self.assertEqual(resultado, esperado)

    def test_log_throughput_registrado(self) -> None:
        """Log de throughput é registrado com métricas de itens/s."""
        with self.assertLogs(
            "apps.core.libs.thread_processor", level="INFO"
        ) as logs:
            self.processor.processar([1, 2, 3], lambda x: x)

        mensagens = " ".join(logs.output)
        self.assertIn("throughput:", mensagens)
        self.assertIn("itens/s", mensagens)

    def test_integracao_decoracao_hash_preserva_ordem(self) -> None:
        """Simulação do padrão de uso real em ``_upsert_incremental``.

        Transforma tuplas ``(pk, obj)`` em ``(id_destino, hash, obj)``
        e valida que a ordem é preservada para 10 objetos.
        """
        tabela = "teste_tabela"
        update_fields = ["nome", "valor"]

        objetos = {
            f"pk_{i}": type("Obj", (), {"nome": f"nome_{i}", "valor": i})()
            for i in range(10)
        }

        def _calcular_hash(obj: object, campos: list[str]) -> str:
            conteudo = "|".join(
                f"{f}={getattr(obj, f)}" for f in sorted(campos)
            ).encode("utf-8")
            return hashlib.sha256(conteudo).hexdigest()

        def _decorar(item: tuple) -> tuple:
            pk_val, obj = item
            return (
                f"{tabela}:{pk_val}",
                _calcular_hash(obj, update_fields),
                obj,
            )

        items = list(objetos.items())
        resultado = self.processor.processar(items, _decorar)

        self.assertEqual(len(resultado), 10)

        for i, (pk_val, obj) in enumerate(items):
            id_destino, hash_val, obj_retornado = resultado[i]
            self.assertEqual(id_destino, f"{tabela}:{pk_val}")
            self.assertIsInstance(hash_val, str)
            self.assertEqual(len(hash_val), 64)
            self.assertIs(obj_retornado, obj)
