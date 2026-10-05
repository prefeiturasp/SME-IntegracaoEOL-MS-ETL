# Generated 2026-05-07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("institucional", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipoescola",
            name="data_atualizacao",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="unidadeeducacional",
            name="eh_ceu",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="unidadeeducacional",
            name="data_atualizacao",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
