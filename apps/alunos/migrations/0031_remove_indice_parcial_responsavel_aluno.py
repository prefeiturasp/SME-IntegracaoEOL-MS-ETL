"""Remove o índice parcial de responsavel_aluno por aluno.

O índice não parcial de mesmas colunas já atende também as consultas de
vínculos vigentes, tornando o parcial redundante.
"""

from django.contrib.postgres.operations import RemoveIndexConcurrently
from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("alunos", "0030_indice_responsavel_aluno_por_aluno"),
    ]

    operations = [
        RemoveIndexConcurrently(
            model_name="responsavelaluno",
            name="idx_resp_aluno_prioritario",
        ),
    ]
