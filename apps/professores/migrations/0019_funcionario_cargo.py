from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("professores", "0018_funcionario_unidade_educacional_origem_vinculo"),
    ]

    operations = [
        migrations.CreateModel(
            name="FuncionarioCargo",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("codigo_rf", models.CharField(max_length=20)),
                ("nome", models.CharField(max_length=200)),
                ("data_inicio", models.DateTimeField(blank=True, null=True)),
                ("data_fim", models.DateTimeField(blank=True, null=True)),
                ("cargo", models.CharField(max_length=100)),
                ("codigo_cargo", models.IntegerField()),
            ],
            options={
                "verbose_name": "funcionario por cargo",
                "verbose_name_plural": "funcionarios por cargo",
                "db_table": "funcionario_cargo",
            },
        ),
        migrations.AddIndex(
            model_name="funcionariocargo",
            index=models.Index(
                fields=["codigo_cargo"], name="idx_funcionario_cargo_codigo"
            ),
        ),
        migrations.AddIndex(
            model_name="funcionariocargo",
            index=models.Index(
                fields=["codigo_rf"], name="idx_funcionario_cargo_rf"
            ),
        ),
        migrations.AddConstraint(
            model_name="funcionariocargo",
            constraint=models.UniqueConstraint(
                fields=[
                    "codigo_rf",
                    "codigo_cargo",
                    "data_inicio",
                    "data_fim",
                    "cargo",
                ],
                name="uq_funcionario_cargo_vinculo",
                nulls_distinct=False,
            ),
        ),
    ]
