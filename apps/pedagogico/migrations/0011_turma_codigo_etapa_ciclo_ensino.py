"""Materializa codigo_etapa_ensino e codigo_ciclo_ensino na tabela turma."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedagogico", "0010_grade_unique_por_serie"),
    ]

    operations = [
        migrations.AddField(
            model_name="turma",
            name="codigo_etapa_ensino",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="turma",
            name="codigo_ciclo_ensino",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
