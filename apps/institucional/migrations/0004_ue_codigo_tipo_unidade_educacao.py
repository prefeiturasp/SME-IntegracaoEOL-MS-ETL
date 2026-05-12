from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "institucional",
            "0003_ue_codigo_logradouro_codigo_tp_equipamento",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="unidadeeducacional",
            name="codigo_tipo_unidade_educacao",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
