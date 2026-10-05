from typing import Any

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies: list[Any] = [
        ("institucional", "0004_ue_codigo_tipo_unidade_educacao"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dre",
            name="sigla",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
