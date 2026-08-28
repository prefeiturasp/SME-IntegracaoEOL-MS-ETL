"""Cria tabela de progresso operacional das execuções ETL."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Migration de criação do progresso operacional."""

    dependencies = [
        ("controle_auditoria", "0002_etlauditorialinha"),
    ]

    operations = [
        migrations.CreateModel(
            name="EtlProgressoExecucao",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("id_execucao", models.UUIDField(db_index=True)),
                ("dominio", models.CharField(db_index=True, max_length=120)),
                ("fase_numero", models.PositiveIntegerField(default=0)),
                ("total_fases", models.PositiveIntegerField(default=0)),
                ("fase_nome", models.CharField(max_length=200)),
                (
                    "tabela_origem",
                    models.CharField(blank=True, max_length=200, null=True),
                ),
                (
                    "tabela_destino",
                    models.CharField(blank=True, max_length=200, null=True),
                ),
                ("etapa", models.CharField(default="pendente", max_length=40)),
                ("chunk_atual", models.PositiveIntegerField(default=0)),
                ("linhas_lidas", models.BigIntegerField(default=0)),
                ("linhas_escritas", models.BigIntegerField(default=0)),
                ("linhas_ignoradas", models.BigIntegerField(default=0)),
                ("mensagem", models.TextField(blank=True, null=True)),
                ("iniciado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "etl_progresso_execucao",
                "indexes": [
                    models.Index(
                        fields=["dominio", "atualizado_em"],
                        name="idx_ep_dominio_atualizado",
                    ),
                    models.Index(fields=["etapa"], name="idx_ep_etapa"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["id_execucao", "fase_numero"],
                        name="uq_ep_execucao_fase",
                    )
                ],
            },
        ),
    ]
