from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("professores", "0017_funcionario_unidade_educacional_datas_vinculo"),
    ]

    operations = [
        migrations.AddField(
            model_name="funcionariounidadeeducacional",
            name="origem_vinculo",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
