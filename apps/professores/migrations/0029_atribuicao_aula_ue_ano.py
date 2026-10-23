"""Indexa atribuições por unidade educacional e ano."""

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        (
            "professores",
            "0028_merge_0027_cargo_0027_cargobaseservidor_idx_cargobaseservidor_ativorf",
        ),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="atribuicaoaula",
            index=models.Index(
                fields=["codigo_unidade_educacao", "ano_atribuicao"],
                name="idx_aa_ue_ano",
            ),
        ),
    ]
