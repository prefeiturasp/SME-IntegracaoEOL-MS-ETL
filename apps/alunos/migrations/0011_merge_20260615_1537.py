# ruff: noqa: D100,D101

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("alunos", "0010_aluno_data_atualizacao_contato_datetime"),
        ("alunos", "0010_matriculaturma_codigo_etapa_ensino_and_more"),
    ]

    operations = []
