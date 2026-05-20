from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("programas", "0006_alunopapanoletivo_alunopapanoletivohistorico"),
    ]

    operations = [
        migrations.AlterField(
            model_name="matriculaturmaprograma",
            name="data_matricula",
            field=models.DateTimeField(help_text="EOL dt_status_matricula."),
        ),
        migrations.AlterField(
            model_name="matriculaturmaprogramahistorico",
            name="data_matricula",
            field=models.DateTimeField(
                blank=True,
                help_text="EOL dt_status_matricula — nullable no histórico.",
                null=True,
            ),
        ),
    ]
