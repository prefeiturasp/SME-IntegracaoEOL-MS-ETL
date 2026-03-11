# Generated manually for project bootstrap.

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="ConsultaEscolasLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("offset_inicial", models.IntegerField()),
                ("limite", models.IntegerField()),
                ("total_retorno", models.IntegerField()),
                ("executado_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "escolas_consulta_log"},
        )
    ]
