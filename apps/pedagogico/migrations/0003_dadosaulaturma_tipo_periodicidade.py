from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedagogico", "0002_alter_agrupamentoatribuicaoterritoriosaber_cod_agrupamento_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="dadosaulaturma",
            name="tipo_periodicidade",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
