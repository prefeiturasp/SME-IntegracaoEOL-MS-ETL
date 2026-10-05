from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pedagogico", "0019_turmaatribuidadreue_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="componenteturma",
            name="tipo_escola",
            field=models.CharField(
                blank=True,
                max_length=10,
                null=True,
            ),
        ),
    ]
