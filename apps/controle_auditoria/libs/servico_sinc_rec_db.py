"""Servicos do dominio SINC_REC_DB."""

import json

from django.db import connection


def exibir_validacao_sinc_rec_db() -> None:
    """Imprime validacao de estrutura de tabelas gerenciada pelo Django."""
    esperadas = {
        "etl_execucao",
        "etl_execucao_tabela_lida",
        "etl_execucao_tabela_escrita",
        "etl_checkpoint_dominio",
        "escolas_consulta_log",
    }
    existentes = set(connection.introspection.table_names())
    tabelas = sorted(esperadas.intersection(existentes))

    print("=== DOMINIO SINC_REC_DB ===")
    print("tabelas_controle_encontradas:")
    print(json.dumps(tabelas, ensure_ascii=True, indent=2))
