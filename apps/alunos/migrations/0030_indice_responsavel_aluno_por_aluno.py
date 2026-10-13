"""Índice não parcial em responsavel_aluno por aluno.

O índice parcial (data_fim_vinculo IS NULL) não atende consultas que
filtram apenas por aluno, pois estas incluem vínculos encerrados.
"""

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("alunos", "0029_remove_indice_nome_invalido_responsavel_aluno"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="responsavelaluno",
            index=models.Index(
                fields=["aluno", "tipo_responsavel", "codigo_responsavel"],
                name="idx_resp_aluno_tipo_cod",
            ),
        ),
    ]
