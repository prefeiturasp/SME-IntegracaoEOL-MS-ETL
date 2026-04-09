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
    mensagem_erro = models.TextField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:

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

        db_table = "etl_execucao_tabela_escrita"


class EtlCheckpointDominio(models.Model):
    """Checkpoint de retomada por dominio."""

    id = models.BigAutoField(primary_key=True)
    dominio = models.CharField(max_length=120, unique=True)
    ultimo_id_execucao = models.UUIDField(null=True)
    ultima_pagina = models.IntegerField(default=0)
    token_parada = models.CharField(max_length=255, blank=True, null=True)
    indice_sincronizacao = models.CharField(
        max_length=120, blank=True, null=True
    )
    ultima_situacao = models.CharField(max_length=30, default="pendente")
    ultimo_sucesso_em = models.DateTimeField(null=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:

        db_table = "etl_checkpoint_dominio"


class EtlAuditoriaLinha(models.Model):
    """Controle de hash por linha para atualização incremental no destino.

    Permite que o ETL processe apenas registros que sofreram alteração
    na origem, evitando reescritas desnecessárias no destino.

    Fluxo de processamento:
        1. ETL lê batch da origem e calcula SHA-256 dos campos
           relevantes de cada linha.
        2. Consulta esta tabela pelo id_destino.
        3. Se hash_controle diverge (ou id_destino não existe):
           linha vai para o batch de atualização.
        4. Destino é atualizado em batch (bulk_create/bulk_update).
        5. hash_controle é atualizado aqui para refletir o estado
           atual da origem.

    id_destino:
        Chave composta no formato "{tabela_destino}:{id_origem}", ex:
            "professor:0012345"
            "turma_escola:9988776"
            "atribuicao_aula:123456"

    hash_controle:
        SHA-256 (hex, 64 chars) calculado sobre os campos relevantes
        da linha de origem.
        Apenas campos que impactam o dado destino devem compor o hash.
    """

    id_destino = models.CharField(
        max_length=255,
        primary_key=True,
        help_text="Chave composta '{tabela_destino}:{id_origem}'",
    )
    hash_controle = models.CharField(
        max_length=64,
        help_text="SHA-256 hex dos dados relevantes da linha de origem.",
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:

        db_table = "etl_auditoria_linha"
        indexes = [
            models.Index(fields=["atualizado_em"], name="idx_eal_atualizado"),
        ]
