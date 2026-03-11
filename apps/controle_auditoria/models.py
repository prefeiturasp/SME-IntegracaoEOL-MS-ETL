"""Modelos Django do dominio SINC_REC_DB."""

from django.db import models


class EtlExecucao(models.Model):
    """Representa uma execucao ETL auditavel."""

    id = models.BigAutoField(primary_key=True)
    id_execucao = models.UUIDField(unique=True)
    dominio = models.CharField(max_length=120)
    situacao = models.CharField(max_length=30)
    iniciado_em = models.DateTimeField()
    finalizado_em = models.DateTimeField(null=True)
    mensagem_erro = models.TextField(null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Configuração de metadados do modelo."""

        db_table = "etl_execucao"


class EtlExecucaoTabelaLida(models.Model):
    """Tabela de rastreio de leitura por execucao."""

    id = models.BigAutoField(primary_key=True)
    id_execucao = models.UUIDField()
    tabela_origem = models.CharField(max_length=200)
    numero_pagina = models.IntegerField(default=0)
    linhas_lidas = models.IntegerField(default=0)
    lido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Configuração de metadados do modelo."""

        db_table = "etl_execucao_tabela_lida"


class EtlExecucaoTabelaEscrita(models.Model):
    """Tabela de rastreio de escrita por execucao."""

    id = models.BigAutoField(primary_key=True)
    id_execucao = models.UUIDField()
    tabela_destino = models.CharField(max_length=200)
    linhas_escritas = models.IntegerField(default=0)
    modo_escrita = models.CharField(max_length=30, default="upsert")
    escrito_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Configuração de metadados do modelo."""

        db_table = "etl_execucao_tabela_escrita"


class EtlCheckpointDominio(models.Model):
    """Checkpoint de retomada por dominio."""

    id = models.BigAutoField(primary_key=True)
    dominio = models.CharField(max_length=120, unique=True)
    ultimo_id_execucao = models.UUIDField(null=True)
    ultima_pagina = models.IntegerField(default=0)
    token_parada = models.CharField(max_length=255, null=True)
    indice_sincronizacao = models.CharField(max_length=120, null=True)
    ultima_situacao = models.CharField(max_length=30, default="pendente")
    ultimo_sucesso_em = models.DateTimeField(null=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        """Configuração de metadados do modelo."""

        db_table = "etl_checkpoint_dominio"
