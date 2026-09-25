# ruff: noqa: D100,D101

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "professores",
            "0026_atribuicaoaula_dt_disponibilizacao_aulas_origem_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="Cargo",
            fields=[
                (
                    "codigo_cargo",
                    models.IntegerField(primary_key=True, serialize=False),
                ),
                ("nome_cargo", models.CharField(max_length=100)),
                ("dt_cancelamento", models.DateField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "cargo",
                "verbose_name_plural": "cargos",
                "db_table": "cargo",
            },
        ),
        migrations.AddIndex(
            model_name="cargo",
            index=models.Index(
                fields=["dt_cancelamento"], name="idx_cargo_cancel"
            ),
        ),
    ]
