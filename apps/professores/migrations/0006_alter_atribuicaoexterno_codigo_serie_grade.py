from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("professores", "0005_alter_atribuicaoaula_codigo_serie_grade"),
    ]

    operations = [
        migrations.AlterField(
            model_name="atribuicaoexterno",
            name="codigo_serie_grade",
            field=models.IntegerField(
                null=True,
                blank=True,
                help_text="ID da SerieTurmaGrade neste DB.",
            ),
        ),
    ]
