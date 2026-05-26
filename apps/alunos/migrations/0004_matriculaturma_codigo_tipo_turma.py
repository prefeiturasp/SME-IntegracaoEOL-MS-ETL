# ruff: noqa: D100,D101

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alunos", "0003_dadosalunoacompanhamentoescolar_matriculaanoletivo_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE matricula_turma "
                        "ADD COLUMN IF NOT EXISTS codigo_tipo_turma smallint;"
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="matriculaturma",
                    name="codigo_tipo_turma",
                    field=models.SmallIntegerField(blank=True, null=True),
                ),
            ],
        ),
    ]
