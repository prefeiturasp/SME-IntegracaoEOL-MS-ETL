# ruff: noqa: D100,D101

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("alunos", "0005_alunos_legado_campos_complementares"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE matricula
                    ADD COLUMN IF NOT EXISTS
                    data_situacao_matricula_data_hora timestamp with time zone;

                    ALTER TABLE matricula_turma
                    ADD COLUMN IF NOT EXISTS
                    data_situacao_aluno_data_hora timestamp with time zone;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="matricula",
                    name="data_situacao_matricula_data_hora",
                    field=models.DateTimeField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="matriculaturma",
                    name="data_situacao_aluno_data_hora",
                    field=models.DateTimeField(blank=True, null=True),
                ),
            ],
        )
    ]
