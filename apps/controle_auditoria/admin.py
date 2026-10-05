"""Configuracao do Django Admin para auditoria ETL."""

from django.contrib import admin

from apps.controle_auditoria.models import (
    EtlCheckpointDominio,
    EtlExecucao,
    EtlExecucaoTabelaEscrita,
    EtlExecucaoTabelaLida,
    EtlProgressoExecucao,
)

_SEARCH_ID = "=id_execucao"
_ID_EXECUCAO = "id_execucao"


@admin.register(EtlExecucaoTabelaLida)
class EtlExecucaoTabelaLidaAdmin(admin.ModelAdmin):
    """Admin de tabelas lidas por execucao."""

    list_display = (
        _ID_EXECUCAO,
        "tabela_origem",
        "numero_pagina",
        "linhas_lidas",
        "lido_em",
    )
    list_filter = ("tabela_origem", "lido_em")
    search_fields = (_SEARCH_ID, "tabela_origem")
    ordering = ("-lido_em",)


@admin.register(EtlExecucao)
class EtlExecucaoAdmin(admin.ModelAdmin):
    """Admin de execucoes ETL."""

    list_display = (
        _ID_EXECUCAO,
        "dominio",
        "situacao",
        "iniciado_em",
        "finalizado_em",
    )
    list_filter = ("situacao", "iniciado_em", "finalizado_em")
    search_fields = (_SEARCH_ID, "dominio")
    readonly_fields = ("parametros",)
    ordering = ("-iniciado_em",)


@admin.register(EtlCheckpointDominio)
class EtlCheckpointDominioAdmin(admin.ModelAdmin):
    """Admin de checkpoint por dominio."""

    list_display = (
        "dominio",
        "ultimo_id_execucao",
        "ultima_pagina",
        "token_parada",
    )
    list_filter = ("dominio",)
    search_fields = ("dominio", "=ultimo_id_execucao", "token_parada")
    ordering = ("dominio",)


@admin.register(EtlExecucaoTabelaEscrita)
class EtlExecucaoTabelaEscritaAdmin(admin.ModelAdmin):
    """Admin de tabelas escritas por execucao."""

    list_display = (
        "id_execucao",
        "linhas_escritas",
        "modo_escrita",
    )
    list_filter = ("tabela_destino", "modo_escrita", "escrito_em")
    search_fields = (_SEARCH_ID, "tabela_destino")
    ordering = ("-escrito_em",)


@admin.register(EtlProgressoExecucao)
class EtlProgressoExecucaoAdmin(admin.ModelAdmin):
    """Admin do progresso operacional por execução/fase."""

    list_display = (
        _ID_EXECUCAO,
        "dominio",
        "fase_numero",
        "fase_nome",
        "etapa",
        "chunk_atual",
        "linhas_lidas",
        "linhas_escritas",
        "linhas_ignoradas",
        "atualizado_em",
    )
    list_filter = ("dominio", "etapa", "atualizado_em")
    search_fields = (_SEARCH_ID, "dominio", "fase_nome", "tabela_destino")
    ordering = ("-atualizado_em",)
