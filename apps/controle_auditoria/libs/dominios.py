"""Regras de domínio para execução parametrizada do ETL."""

COMANDOS_POR_DOMINIO: dict[str, str] = {
    "institucional": "etl_institucional",
    "professores": "etl_professores",
    "alunos": "etl_alunos",
    "pedagogico": "etl_pedagogico",
    "programas": "etl_programas",
}

DOMINIOS_VALIDOS = [*COMANDOS_POR_DOMINIO.keys()]
DOMINIOS_COM_ANO_LETIVO = frozenset({"pedagogico"})
DOMINIOS_COM_FASES = frozenset({"pedagogico"})


def validar_parametros_dominio(
    dominio: str,
    ano_letivo: int | None = None,
    fases: list[str] | None = None,
) -> str | None:
    """Retorna mensagem de erro quando o domínio não aceita parâmetros."""
    if dominio not in DOMINIOS_VALIDOS:
        return f"Domínio inválido. Use: {', '.join(DOMINIOS_VALIDOS)}"

    if ano_letivo is not None and dominio not in DOMINIOS_COM_ANO_LETIVO:
        return f"O domínio '{dominio}' não aceita o parâmetro ano_letivo."

    if fases and dominio not in DOMINIOS_COM_FASES:
        return f"O domínio '{dominio}' não aceita o parâmetro fases."

    return None
