# ruff: noqa: D100,D101

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("alunos", "0012_alter_matriculaturma_unique_together_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE matricula_turma
                DROP CONSTRAINT IF EXISTS
                    uq_matricula_turma_matricula_turma;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
