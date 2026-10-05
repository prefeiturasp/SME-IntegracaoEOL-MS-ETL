from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("programas", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="turmaprograma",
            name="codigo_tipo_programa",
            field=models.IntegerField(
                blank=True,
                help_text=(
                    "EOL cd_tipo_programa — FK lógica para tipo_programa. "
                    "Pode ser NULL: a categoria PAP/PAEE é determinada pelo componente "
                    "curricular da turma, não pelo tipo de programa."
                ),
                null=True,
            ),
        ),
    ]
