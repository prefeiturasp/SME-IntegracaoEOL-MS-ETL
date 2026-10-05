from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("pedagogico", "0016_atribuicao_territorio_saber"),
    ]

    operations = [
        migrations.AddField(
            model_name="componentecurricularhierarquia",
            name="transferido_em",
            field=models.DateTimeField(default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="componentecurricularpap",
            name="transferido_em",
            field=models.DateTimeField(default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="componentecurricularplanejamentoregencia",
            name="transferido_em",
            field=models.DateTimeField(default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="turmaitinerarioensinomedio",
            name="transferido_em",
            field=models.DateTimeField(default=timezone.now),
            preserve_default=False,
        ),
    ]
