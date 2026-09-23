"""Recria o índice do responsável vigente/prioritário por aluno.

A 0027 criou esse índice com o nome `idx_resp_aluno_vigente_prioridade`
(33 caracteres), mas o Meta.indexes do model não tinha sido atualizado
para declará-lo -- o pipeline de deploy roda `makemigrations` antes do
`migrate`, detectou a divergência entre o estado das migrations e o
model, e gerou/aplicou uma migration removendo o índice no mesmo deploy
(nunca commitada neste repositório). O nome também estourava o limite
de 30 caracteres do Django (E034), que só é checado quando o índice
está declarado no Meta -- por isso a 0027 "passou" sem erro. Esta
migration recria o índice com um nome válido (`idx_resp_aluno_prioritario`,
26 caracteres), já refletido no Meta.indexes do model.
"""

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("alunos", "0027_indice_responsavel_aluno_vigente_por_aluno"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="responsavelaluno",
            index=models.Index(
                fields=["aluno", "tipo_responsavel", "codigo_responsavel"],
                condition=models.Q(data_fim_vinculo__isnull=True),
                name="idx_resp_aluno_prioritario",
            ),
        ),
    ]
