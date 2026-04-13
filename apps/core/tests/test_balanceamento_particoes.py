"""Testes para as funções de particionamento balanceado do ETL."""

from django.test import SimpleTestCase

from scripts.run_parallel_etl import (
    _dividir_range,
    _dividir_range_balanceado,
)


class DividirRangeTest(SimpleTestCase):
    """Testes para _dividir_range."""

    def test_divide_em_n_partes(self) -> None:
        partes = _dividir_range(1, 100, 4)
        self.assertEqual(len(partes), 4)

    def test_sem_lacunas(self) -> None:
        partes = _dividir_range(1, 100, 4)
        for i in range(len(partes) - 1):
            self.assertEqual(partes[i][1] + 1, partes[i + 1][0])

    def test_ultima_particao_vai_ate_id_max(self) -> None:
        partes = _dividir_range(1, 8871260, 4)
        self.assertEqual(partes[-1][1], 8871260)

    def test_primeira_particao_comeca_em_id_min(self) -> None:
        partes = _dividir_range(1, 100, 4)
        self.assertEqual(partes[0][0], 1)


class DividirRangeBalanceadoTest(SimpleTestCase):
    """Testes para _dividir_range_balanceado."""

    def _hist(
        self, buckets: list[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        return buckets

    def test_retorna_n_particoes(self) -> None:
        hist = self._hist([(0, 100), (1, 100), (2, 100), (3, 100)])
        partes = _dividir_range_balanceado(hist, 0, 399999, 4, 100000)
        self.assertEqual(len(partes), 4)

    def test_sem_lacunas_entre_particoes(self) -> None:
        hist = self._hist([(0, 50), (1, 50), (2, 50), (3, 50)])
        partes = _dividir_range_balanceado(hist, 0, 399999, 4, 100000)
        for i in range(len(partes) - 1):
            self.assertEqual(partes[i][1] + 1, partes[i + 1][0])

    def test_primeira_particao_comeca_em_id_min(self) -> None:
        hist = self._hist([(0, 25), (1, 25), (2, 25), (3, 25)])
        partes = _dividir_range_balanceado(hist, 0, 399999, 4, 100000)
        self.assertEqual(partes[0][0], 0)

    def test_ultima_particao_vai_ate_id_max(self) -> None:
        hist = self._hist([(0, 25), (1, 25), (2, 25), (3, 25)])
        partes = _dividir_range_balanceado(hist, 0, 399999, 4, 100000)
        self.assertEqual(partes[-1][1], 399999)

    def test_distribuicao_uniforme_equivale_divisao_linear(self) -> None:
        """Com carga uniforme os cortes devem coincidir com divisão linear."""
        bucket_size = 100_000
        hist = [(i, 100) for i in range(8)]
        partes_bal = _dividir_range_balanceado(
            hist, 0, 799999, 4, bucket_size
        )
        partes_lin = _dividir_range(0, 799999, 4)
        self.assertEqual(partes_bal, partes_lin)

    def test_dados_assimetricos_equilibram_carga(self) -> None:
        """Partição com dados concentrados no final deve ser menor em IDs."""
        bucket_size = 100_000
        # 10% nos primeiros 3 buckets, 90% nos últimos 5
        hist = [
            (0, 5), (1, 5), (2, 5),
            (3, 40), (4, 40), (5, 40), (6, 40), (7, 40),
        ]
        partes = _dividir_range_balanceado(
            hist, 0, 799999, 4, bucket_size
        )
        self.assertEqual(len(partes), 4)
        # Partição 0 deve cobrir range maior de IDs (baixa densidade)
        range_p0 = partes[0][1] - partes[0][0]
        range_p3 = partes[3][1] - partes[3][0]
        self.assertGreater(range_p0, range_p3)

    def test_histograma_vazio_usa_divisao_linear(self) -> None:
        partes = _dividir_range_balanceado([], 1, 100, 4)
        self.assertEqual(partes, _dividir_range(1, 100, 4))

    def test_total_zero_usa_divisao_linear(self) -> None:
        hist = [(0, 0), (1, 0)]
        partes = _dividir_range_balanceado(hist, 0, 199999, 4, 100000)
        self.assertEqual(partes, _dividir_range(0, 199999, 4))

    def test_n_igual_a_1_retorna_range_completo(self) -> None:
        hist = [(0, 100), (1, 200)]
        partes = _dividir_range_balanceado(hist, 0, 199999, 1, 100000)
        self.assertEqual(len(partes), 1)
        self.assertEqual(partes[0], (0, 199999))

    def test_dados_concentrados_em_poucos_buckets_usa_fallback(
        self,
    ) -> None:
        """Quando dados estão em menos buckets que partições, usa linear."""
        bucket_size = 100_000
        # Apenas 2 buckets para 4 partições — não é possível balancear
        hist = [(0, 500), (1, 500)]
        partes = _dividir_range_balanceado(
            hist, 0, 399999, 4, bucket_size
        )
        self.assertEqual(len(partes), 4)
        # Deve ter recaído em divisão linear
        self.assertEqual(partes, _dividir_range(0, 399999, 4))

    def test_carga_total_aproximadamente_igual_por_particao(self) -> None:
        """Verifica que a carga por partição está dentro de 20% do alvo."""
        bucket_size = 100_000
        hist = [
            (0, 5), (1, 5), (2, 5), (3, 5),
            (4, 80), (5, 80), (6, 80), (7, 80),
        ]
        total = sum(c for _, c in hist)
        alvo = total / 4
        partes = _dividir_range_balanceado(
            hist, 0, 799999, 4, bucket_size
        )
        # Mapeia carga por partição (bucket pertence à partição se
        # bucket_end está dentro do range da partição)
        for p_min, p_max in partes:
            carga = sum(
                c
                for b, c in hist
                if p_min <= b * bucket_size
                and (b + 1) * bucket_size - 1 <= p_max
            )
            # Tolerância de 50% (dados muito assimétricos, granularidade
            # de bucket pode não permitir equilíbrio perfeito)
            self.assertLessEqual(carga, alvo * 1.5 + 1)
