# ruff: noqa: D100,D101

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("alunos", "0007_add_unique_constraint_matricula_turma"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE aluno
                    ALTER COLUMN data_atualizacao_contato
                    TYPE timestamp with time zone
                    USING data_atualizacao_contato::timestamp with time zone;
                    """,
                    reverse_sql="""
                    ALTER TABLE aluno
                    ALTER COLUMN data_atualizacao_contato
                    TYPE date
                    USING data_atualizacao_contato::date;
                    """,
                )
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="aluno",
                    name="data_atualizacao_contato",
                    field=models.DateTimeField(blank=True, null=True),
                ),
            ],
        )
    ]
