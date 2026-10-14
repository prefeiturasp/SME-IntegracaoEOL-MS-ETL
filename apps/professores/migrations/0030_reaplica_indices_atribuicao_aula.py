"""Reconcilia os índices existentes de atribuições.

A reversão preserva os índices, pois eles já pertencem ao estado histórico.
"""

from typing import Any

from django.db import NotSupportedError, migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


_INDICES = (
    ("atribuicao_aula_cargo_base_id_5e628a3b", "cargo_base_id"),
    ("idx_aa_turma", "codigo_turma_escola"),
)
_TABELA = "public.atribuicao_aula"


def _inspecionar_indices(
    schema_editor: BaseDatabaseSchemaEditor,
) -> dict[str, dict[str, Any]]:
    """Obtém a definição física dos índices da tabela.

    Args:
        schema_editor: Editor associado ao banco de destino.

    Returns:
        Metadados dos índices, identificados pelo nome.
    """
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT ci.relname, i.indisvalid, i.indisready, i.indislive, "
            "i.indisunique, am.amname, i.indnkeyatts, i.indnatts, "
            "i.indoption::text, pg_get_expr(i.indpred, i.indrelid), "
            "pg_get_expr(i.indexprs, i.indrelid), ARRAY("
            "SELECT a.attname FROM unnest(i.indkey) WITH ORDINALITY "
            "AS k(attnum, posicao) LEFT JOIN pg_attribute a "
            "ON a.attrelid=i.indrelid AND a.attnum=k.attnum "
            "ORDER BY k.posicao), (SELECT bool_and(o.opcdefault) "
            "FROM unnest(i.indclass) AS op(oid) "
            "JOIN pg_opclass o ON o.oid=op.oid) "
            "FROM pg_index i JOIN pg_class ci ON ci.oid=i.indexrelid "
            "JOIN pg_am am ON am.oid=ci.relam "
            "WHERE i.indrelid=to_regclass(%s)",
            [_TABELA],
        )
        campos = (
            "valido", "pronto", "vivo", "unico", "metodo", "chaves",
            "atributos", "opcoes", "predicado", "expressao", "colunas",
            "operadores_padrao",
        )
        return {
            row[0]: dict(zip(campos, row[1:], strict=True))
            for row in cursor.fetchall()
        }


def _definicao_compativel(indice: dict[str, Any], coluna: str) -> bool:
    """Verifica a definição esperada de um índice simples.

    Args:
        indice: Metadados físicos do índice.
        coluna: Coluna prevista no estado histórico.

    Returns:
        Se a definição corresponde ao índice esperado.
    """
    return (
        indice["metodo"] == "btree"
        and indice["chaves"] == indice["atributos"] == 1
        and indice["colunas"] == [coluna]
        and indice["opcoes"] == "0"
        and indice["predicado"] is None
        and indice["expressao"] is None
        and not indice["unico"]
        and indice["operadores_padrao"]
    )


def _validar_indice(
    nome: str, coluna: str, indice: dict[str, Any]
) -> None:
    """Valida um índice existente antes de preservar sua estrutura.

    Args:
        nome: Nome esperado no estado histórico.
        coluna: Coluna prevista para o índice.
        indice: Metadados físicos encontrados.

    Raises:
        RuntimeError: Se o índice está inválido ou é incompatível.
    """
    if not all(indice[key] for key in ("valido", "pronto", "vivo")):
        raise RuntimeError(f"Índice {nome} inválido; exige reconciliação.")
    if not _definicao_compativel(indice, coluna):
        raise RuntimeError(f"Índice {nome} com definição incompatível.")


def reaplicar_indices(
    _apps: object, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    """Restaura índices ausentes e preserva os existentes corretos.

    Args:
        _apps: Registro histórico recebido pelo executor.
        schema_editor: Editor associado ao banco de destino.

    Raises:
        NotSupportedError: Se o banco não é PostgreSQL.
        RuntimeError: Se há transação ou estrutura incompatível.
    """
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        raise NotSupportedError("A reconciliação exige PostgreSQL.")
    if connection.in_atomic_block or not connection.get_autocommit():
        raise RuntimeError("A reconciliação exige execução sem transação.")

    indices = _inspecionar_indices(schema_editor)
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s)", [_TABELA])
        if cursor.fetchone()[0] is None:
            raise RuntimeError("Tabela de atribuições ausente.")
        cursor.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n "
            "ON n.oid=c.relnamespace WHERE n.nspname='public' "
            "AND c.relname = ANY(%s)",
            [[nome for nome, _ in _INDICES]],
        )
        ocupados = {row[0] for row in cursor.fetchall()}

    # Confere todos os candidatos antes de executar qualquer DDL.
    for nome, coluna in _INDICES:
        if nome in indices:
            _validar_indice(nome, coluna, indices[nome])
        elif nome in ocupados:
            raise RuntimeError(f"Nome {nome} ocupado por outra estrutura.")
    for nome, coluna in _INDICES:
        if nome not in indices and any(
            _definicao_compativel(indice, coluna)
            for indice in indices.values()
        ):
            raise RuntimeError(
                f"Índice equivalente a {nome} com outro nome; reconciliar."
            )

    quote = schema_editor.quote_name
    tabela = f"{quote('public')}.{quote('atribuicao_aula')}"
    for nome, coluna in _INDICES:
        if nome in indices:
            continue
        schema_editor.execute(
            f"CREATE INDEX CONCURRENTLY {quote(nome)} "
            f"ON {tabela} ({quote(coluna)})"
        )
        criado = _inspecionar_indices(schema_editor).get(nome)
        if criado is None:
            raise RuntimeError(f"Índice {nome} não encontrado após criação.")
        _validar_indice(nome, coluna, criado)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("professores", "0029_atribuicao_aula_ue_ano"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    reaplicar_indices,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[],
        ),
    ]
