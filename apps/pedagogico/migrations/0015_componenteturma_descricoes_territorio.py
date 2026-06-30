from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pedagogico", "0014_agrupamento_multiplos_professores"),
    ]

    operations = [
        migrations.AddField(
            model_name="componenteturma",
            name="desc_territorio_saber",
            field=models.CharField(
                blank=True,
                max_length=200,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="componenteturma",
            name="desc_experiencia_pedagogica",
            field=models.CharField(
                blank=True,
                max_length=200,
                null=True,
            ),
        ),
    ]
