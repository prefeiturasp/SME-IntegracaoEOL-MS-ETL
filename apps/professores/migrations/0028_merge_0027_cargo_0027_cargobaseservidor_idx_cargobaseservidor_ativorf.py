# ruff: noqa: D100,D101

from django.db import migrations
from django.db.migrations.operations.base import Operation


class Migration(migrations.Migration):
    dependencies = [
        ("professores", "0027_cargo"),
        (
            "professores",
            "0027_cargobaseservidor_idx_cargobaseservidor_ativorf",
        ),
    ]

    operations: list[Operation] = []
