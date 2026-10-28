"""Registra gerações e execuções de carga do domínio."""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("professores", "0030_reaplica_indices_atribuicao_aula"),
    ]

    operations = [
        migrations.CreateModel(
            name="ControleCargaProfessores",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1, primary_key=True, serialize=False
                    ),
                ),
                ("geracao", models.UUIDField(default=uuid.uuid4)),
                ("cargas_ativas", models.JSONField(default=list)),
                ("falha", models.BooleanField(default=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "controle_carga_professores"},
        ),
    ]
