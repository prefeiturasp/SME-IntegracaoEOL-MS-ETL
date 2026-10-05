from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("programas", "0002_turmaprograma_codigo_tipo_programa_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="turmaprograma",
            name="descricao_grade",
            field=models.CharField(
                blank=True,
                help_text=(
                    "EOL grade.dc_grade da grade vinculada à turma "
                    "(turma_escola_grade_programa → escola_grade → grade). "
                    "Usado para compor o turmaNome legado no formato "
                    "'<dc_turma_escola> - <dc_grade>' "
                    "(ex: 'PAP COLABORATIVO 3 / 4 E 5 ANO'). "
                    "Quando a turma tem mais de uma grade ativa, é trazida "
                    "uma (TOP 1 / OUTER APPLY) — fiel ao comportamento "
                    "legado."
                ),
                max_length=200,
                null=True,
            ),
        ),
    ]
