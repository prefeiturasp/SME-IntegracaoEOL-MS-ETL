from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pedagogico", "0003_dadosaulaturma_tipo_periodicidade"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="componentecurricularporturma",
            index=models.Index(
                fields=["professor", "ano_letivo"],
                name="idx_ccpt_prof_ano",
            ),
        ),
    ]
