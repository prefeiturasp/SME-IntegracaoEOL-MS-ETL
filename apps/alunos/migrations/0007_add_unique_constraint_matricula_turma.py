# ruff: noqa: D100,D101

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("alunos", "0006_datetime_situacao_matricula_turma"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE matricula_turma
                    ADD CONSTRAINT uq_matricula_turma_matricula_turma
                    UNIQUE (codigo_matricula, codigo_turma);
                    """,
                    reverse_sql="""
                    ALTER TABLE matricula_turma
                    DROP CONSTRAINT uq_matricula_turma_matricula_turma;
                    """,
                )
            ],
            state_operations=[],
        )
    ]
