"""Indexa o responsável vigente e prioritário por aluno."""

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("alunos", "0026_indice_listagem_ue_ano"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="responsavelaluno",
            index=models.Index(
                fields=["aluno", "tipo_responsavel", "codigo_responsavel"],
                condition=models.Q(data_fim_vinculo__isnull=True),
                name="idx_resp_aluno_vigente_prioridade",
            ),
        ),
    ]
