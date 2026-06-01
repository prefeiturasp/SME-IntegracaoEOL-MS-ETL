"""Adiciona OUTROS ao choices de CategoriaPrograma em todas as tabelas."""

from django.db import migrations, models


_CHOICES = [("PAP", "PAP"), ("PAEE", "PAEE"), ("OUTROS", "Outros")]


class Migration(migrations.Migration):

    dependencies = [
        ("programas", "0007_alter_data_matricula_to_datetime"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tipoprograma",
            name="categoria",
            field=models.CharField(
                choices=_CHOICES,
                help_text="'PAP', 'PAEE' ou 'OUTROS'.",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="componentecurricularprograma",
            name="categoria",
            field=models.CharField(
                choices=_CHOICES,
                help_text="'PAP', 'PAEE' ou 'OUTROS'.",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="turmaprograma",
            name="categoria",
            field=models.CharField(
                choices=_CHOICES,
                help_text=(
                    "'PAP', 'PAEE' ou 'OUTROS' — desnormalizado de "
                    "TipoPrograma para filtros diretos."
                ),
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="matriculaturmaprograma",
            name="categoria",
            field=models.CharField(
                choices=_CHOICES,
                help_text=(
                    "'PAP', 'PAEE' ou 'OUTROS' — desnormalizado da turma "
                    "para filtros diretos."
                ),
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="matriculaturmaprogramahistorico",
            name="categoria",
            field=models.CharField(
                choices=_CHOICES,
                help_text=(
                    "'PAP', 'PAEE' ou 'OUTROS' — desnormalizado da turma "
                    "para filtros diretos."
                ),
                max_length=10,
            ),
        ),
    ]
