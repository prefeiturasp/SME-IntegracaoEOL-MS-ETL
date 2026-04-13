"""Utilitários de particionamento para ETL paralelo."""

def dividir_range(
    id_min: int, id_max: int, n: int
) -> list[tuple[int, int]]:
    """Divide um range [id_min, id_max] em N partes iguais sem lacunas."""
    if n <= 1:
        return [(id_min, id_max)]

    tamanho = (id_max - id_min + 1) // n
    partes = []
    atual = id_min
    for i in range(n):
        fim = atual + tamanho - 1 if i < n - 1 else id_max
        partes.append((atual, fim))
        atual = fim + 1
    return partes


def dividir_range_balanceado(
    hist: list[tuple[int, int]],
    id_min: int,
    id_max: int,
    n_partes: int,
    bucket_size: int = 100_000,
) -> list[tuple[int, int]]:
    """Divide um range de IDs em N partições equilibradas via histograma.

    Usa contagens por bucket para encontrar cortes que equilibram o volume
    de registros por partição, evitando concentração de dados em sub-ranges.
    """
    if n_partes <= 1:
        return [(id_min, id_max)]

    total = sum(c for _, c in hist)
    if not hist or total <= 0 or len(hist) < n_partes:
        return dividir_range(id_min, id_max, n_partes)

    hist_sorted = sorted(hist, key=lambda x: x[0])
    partes = _calcular_particoes(
        hist_sorted, id_min, id_max, n_partes, bucket_size, total
    )

    # Fallback se a lógica de balanço falhar em gerar todas as partições
    if len(partes) != n_partes:
        return dividir_range(id_min, id_max, n_partes)

    return partes


def _calcular_particoes(
    hist_sorted: list[tuple[int, int]],
    id_min: int,
    id_max: int,
    n: int,
    bucket_size: int,
    total: float,
) -> list[tuple[int, int]]:
    """Implementação interna do loop de balanceamento (Complexidade < 15)."""
    alvo = total / n
    partes: list[tuple[int, int]] = []
    acumulado = 0
    p_min = id_min

    for i, (b_idx, count) in enumerate(hist_sorted):
        acumulado += count
        is_last = i == len(hist_sorted) - 1

        if acumulado >= alvo * (len(partes) + 1) or is_last:
            bucket_fim_id = (b_idx + 1) * bucket_size - 1
            p_max = id_max if is_last else min(bucket_fim_id, id_max)

            partes.append((p_min, p_max))
            p_min = p_max + 1

            # Se já preenchemos n-1 partições, a última pega o resto
            if len(partes) == n - 1:
                partes.append((p_min, id_max))
                break
    return partes
