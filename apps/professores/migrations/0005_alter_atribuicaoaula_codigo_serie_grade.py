from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("professores", "0004_alter_atribuicaoaula_codigo_grade_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="atribuicaoaula",
            name="codigo_serie_grade",
            field=models.IntegerField(
                null=True,
                blank=True,
                help_text="ID da SerieTurmaGrade neste DB.",
            ),
        ),
    ]
