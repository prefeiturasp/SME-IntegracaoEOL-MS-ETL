# ruff: noqa: D100,D101,E501

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("alunos", "0007_add_unique_constraint_matricula_turma"),
    ]

    state_operations = [
        migrations.AddField(
            model_name="responsavelaluno",
            name="data_nascimento",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="responsavelaluno",
            name="nome_mae",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE responsavel_aluno ADD COLUMN IF NOT EXISTS data_nascimento date;
                    ALTER TABLE responsavel_aluno ADD COLUMN IF NOT EXISTS nome_mae varchar(200);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=state_operations,
        )
    ]
