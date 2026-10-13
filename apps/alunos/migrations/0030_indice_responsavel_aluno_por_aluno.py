"""Índice não parcial em responsavel_aluno com `codigo_aluno` na frente.

O índice parcial `idx_resp_aluno_prioritario` (WHERE data_fim_vinculo IS
NULL) não é usado por consultas que filtram só por aluno, como a listagem
de responsáveis do Alunos-MS: o planner cai em varredura por
`idx_resp_cpf_fim_aluno` (~240 ms por chamada em tabela de ~6 milhões de
linhas). Este índice atende a consulta com busca direta por aluno.
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
