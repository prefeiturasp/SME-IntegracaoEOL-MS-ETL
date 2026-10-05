from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("professores", "0016_disciplina_turma_atribuida_ue"),
    ]

    operations = [
        migrations.AddField(
            model_name="funcionariounidadeeducacional",
            name="dt_fim_nomeacao",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="funcionariounidadeeducacional",
            name="dt_fim_funcao_atividade",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
