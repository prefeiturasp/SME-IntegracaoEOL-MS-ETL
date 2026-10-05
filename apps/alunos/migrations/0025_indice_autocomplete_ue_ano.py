"""Indexa os vínculos regulares consultados por UE e ano."""

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("alunos", "0024_aluno_tipo_sigilo_responsavel_campos_contrato"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="matriculaturma",
            index=models.Index(
                fields=[
                    "codigo_ue_turma",
                    "ano_letivo_turma",
                    "origem_atual",
                ],
                condition=models.Q(codigo_tipo_turma=1),
                name="idx_mt_regular_ue_ano_origem",
            ),
        ),
    ]
