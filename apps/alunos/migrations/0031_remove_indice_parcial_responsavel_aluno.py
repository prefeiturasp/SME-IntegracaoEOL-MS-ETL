"""Remove o índice parcial `idx_resp_aluno_prioritario` de responsavel_aluno.

`idx_resp_aluno_tipo_cod` (0030) tem as mesmas colunas, sem o predicado
`data_fim_vinculo IS NULL`, e atende também as consultas que só buscam
vínculos vigentes: o filtro é aplicado sobre as poucas linhas de cada aluno.
Manter os dois dobra o custo de escrita e de espaço em ~6 milhões de linhas.
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
