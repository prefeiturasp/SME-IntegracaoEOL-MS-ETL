"""Adiciona parâmetros usados na execução ETL."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Migration para armazenar o escopo de disparo da execução."""

    dependencies = [
        ("controle_auditoria", "0003_etlprogressoexecucao"),
    ]

    operations = [
        migrations.AddField(
            model_name="etlexecucao",
            name="parametros",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
