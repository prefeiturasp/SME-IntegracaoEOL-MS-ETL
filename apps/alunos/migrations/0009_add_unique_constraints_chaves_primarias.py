# ruff: noqa: D100,D101

from django.db import migrations

_TABELAS_COLUNAS = {
    "aluno": "codigo_aluno",
    "responsavel_aluno": "codigo_responsavel",
    "necessidade_especial_aluno": "codigo_necessidade_especial_aluno",
}


def _sql_criar(tabela: str, coluna: str) -> str:
    return f"""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = '{tabela}'
              AND c.contype IN ('p', 'u')
        ) THEN
            ALTER TABLE {tabela}
                ADD CONSTRAINT uq_{tabela}_{coluna}
                UNIQUE ({coluna});
        END IF;
    END $$;
    """


def _sql_reverter(tabela: str, coluna: str) -> str:
    return f"""
    ALTER TABLE {tabela}
        DROP CONSTRAINT IF EXISTS uq_{tabela}_{coluna};
    """


class Migration(migrations.Migration):
    """Garante unique nas chaves naturais usadas pelo upsert (ON CONFLICT).

    Em ambientes provisionados por script externo as tabelas foram criadas
    sem chave primária e as migrations foram aplicadas com ``--fake-initial``,
    deixando o banco sem o índice único que o ``bulk_create`` com
    ``update_conflicts`` exige. A constraint só é criada quando a tabela
    ainda não possui nenhuma PK/unique.
    """

    dependencies = [
        ("alunos", "0008_responsavel_aluno_dados_resumidos"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=_sql_criar(tabela, coluna),
                    reverse_sql=_sql_reverter(tabela, coluna),
                )
                for tabela, coluna in _TABELAS_COLUNAS.items()
            ],
            state_operations=[],
        )
    ]
