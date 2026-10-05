"""Indexa vínculos atuais por unidade educacional e ano letivo."""

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("alunos", "0025_indice_autocomplete_ue_ano"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="matriculaturma",
            index=models.Index(
                fields=["codigo_ue_turma", "ano_letivo_turma"],
                condition=models.Q(origem_atual=True),
                name="idx_mt_atual_ue_ano",
            ),
        ),
    ]
