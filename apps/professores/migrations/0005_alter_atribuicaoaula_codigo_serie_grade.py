from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("professores", "0004_cargobaseservidor_situacao_funcional_and_more"),
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
