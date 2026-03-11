# Generated manually for project bootstrap.

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="EtlExecucao",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("id_execucao", models.UUIDField(unique=True)),
                ("dominio", models.CharField(max_length=120)),
                ("situacao", models.CharField(max_length=30)),
                ("iniciado_em", models.DateTimeField()),
                ("finalizado_em", models.DateTimeField(null=True)),
                ("mensagem_erro", models.TextField(null=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "etl_execucao"},
        ),
        migrations.CreateModel(
            name="EtlExecucaoTabelaLida",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("id_execucao", models.UUIDField()),
                ("tabela_origem", models.CharField(max_length=200)),
                ("numero_pagina", models.IntegerField(default=0)),
                ("linhas_lidas", models.IntegerField(default=0)),
                ("lido_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "etl_execucao_tabela_lida"},
        ),
        migrations.CreateModel(
            name="EtlExecucaoTabelaEscrita",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("id_execucao", models.UUIDField()),
                ("tabela_destino", models.CharField(max_length=200)),
                ("linhas_escritas", models.IntegerField(default=0)),
                (
                    "modo_escrita",
                    models.CharField(default="upsert", max_length=30),
                ),
                ("escrito_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "etl_execucao_tabela_escrita"},
        ),
        migrations.CreateModel(
            name="EtlCheckpointDominio",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("dominio", models.CharField(max_length=120, unique=True)),
                ("ultimo_id_execucao", models.UUIDField(null=True)),
                ("ultima_pagina", models.IntegerField(default=0)),
                ("token_parada", models.CharField(max_length=255, null=True)),
                (
                    "indice_sincronizacao",
                    models.CharField(max_length=120, null=True),
                ),
                (
                    "ultima_situacao",
                    models.CharField(default="pendente", max_length=30),
                ),
                ("ultimo_sucesso_em", models.DateTimeField(null=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "etl_checkpoint_dominio"},
        ),
    ]
