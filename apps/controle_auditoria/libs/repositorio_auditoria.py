"""Repositorio de auditoria ETL baseado em ORM Django."""

from typing import cast
from uuid import UUID, uuid4

from django.db import transaction
from django.utils import timezone

from apps.controle_auditoria.models import (
    EtlCheckpointDominio,
    EtlExecucao,
    EtlExecucaoTabelaEscrita,
    EtlExecucaoTabelaLida,
    EtlProgressoExecucao,
)


class RepositorioAuditoriaPostgres:
    """Persiste estado de execucao e checkpoint por dominio."""

    def iniciar_execucao(
        self, dominio: str, parametros: dict[str, object] | None = None
    ) -> UUID:
        """Cria registro de execucao em andamento."""
        id_execucao = uuid4()
        EtlExecucao.objects.create(
            id_execucao=id_execucao,
            dominio=dominio,
            situacao="em_execucao",
            iniciado_em=timezone.now(),
            parametros=parametros or {},
        )
        return id_execucao

    def finalizar_execucao(
        self,
        id_execucao: UUID,
        situacao: str,
        mensagem_erro: str | None = None,
    ) -> None:
        """Finaliza execucao com status final."""
        EtlExecucao.objects.filter(id_execucao=id_execucao).update(
            situacao=situacao,
            finalizado_em=timezone.now(),
            mensagem_erro=mensagem_erro,
        )

    def registrar_tabela_lida(
        self,
        id_execucao: UUID,
        tabela_origem: str,
        numero_pagina: int,
        linhas_lidas: int,
    ) -> None:
        """Registra metadados de leitura no log de execucao."""
        EtlExecucaoTabelaLida.objects.create(
            id_execucao=id_execucao,
            tabela_origem=tabela_origem,
            numero_pagina=numero_pagina,
            linhas_lidas=linhas_lidas,
        )

    def registrar_tabela_escrita(
        self,
        id_execucao: UUID,
        tabela_destino: str,
        linhas_escritas: int,
        modo_escrita: str = "upsert",
    ) -> None:
        """Registra metadados de escrita no log de execucao."""
        registros = EtlExecucaoTabelaEscrita.objects.filter(
            id_execucao=id_execucao,
            tabela_destino=tabela_destino,
        )
        registro = registros.order_by("-escrito_em").first()
        if registro:
            registro.linhas_escritas = linhas_escritas
            registro.modo_escrita = modo_escrita
            registro.save(update_fields=["linhas_escritas", "modo_escrita"])
            registros.exclude(pk=registro.pk).delete()
            return

        EtlExecucaoTabelaEscrita.objects.create(
            id_execucao=id_execucao,
            tabela_destino=tabela_destino,
            linhas_escritas=linhas_escritas,
            modo_escrita=modo_escrita,
        )

    def obter_checkpoint_dominio(
        self, dominio: str
    ) -> dict[str, object] | None:
        """Retorna checkpoint atual do dominio."""
        resultado = (
            EtlCheckpointDominio.objects.filter(dominio=dominio)
            .values(
                "dominio",
                "ultimo_id_execucao",
                "ultima_pagina",
                "token_parada",
                "indice_sincronizacao",
                "ultima_situacao",
                "ultimo_sucesso_em",
                "atualizado_em",
            )
            .first()
        )

        return cast(dict[str, object] | None, resultado)

    def obter_progresso_execucoes(
        self, ids_execucao: list[UUID]
    ) -> dict[str, list[dict[str, object]]]:
        """Retorna progresso operacional agrupado por id_execucao."""
        progresso: dict[str, list[dict[str, object]]] = {}
        qs = (
            EtlProgressoExecucao.objects.filter(id_execucao__in=ids_execucao)
            .values(
                "id_execucao",
                "dominio",
                "fase_numero",
                "total_fases",
                "fase_nome",
                "tabela_origem",
                "tabela_destino",
                "etapa",
                "chunk_atual",
                "linhas_lidas",
                "linhas_escritas",
                "linhas_ignoradas",
                "mensagem",
                "atualizado_em",
            )
            .order_by("id_execucao", "fase_numero")
        )
        for item in qs:
            progresso.setdefault(str(item["id_execucao"]), []).append(item)
        return progresso

    def atualizar_progresso_execucao(
        self,
        *,
        id_execucao: UUID,
        dominio: str,
        fase_numero: int,
        total_fases: int,
        fase_nome: str,
        tabela_origem: str | None,
        tabela_destino: str | None,
        etapa: str,
        chunk_atual: int,
        linhas_lidas: int,
        linhas_escritas: int,
        linhas_ignoradas: int,
        mensagem: str | None = None,
    ) -> None:
        """Atualiza uma linha leve de progresso operacional."""
        EtlProgressoExecucao.objects.update_or_create(
            id_execucao=id_execucao,
            fase_numero=fase_numero,
            defaults={
                "dominio": dominio,
                "total_fases": total_fases,
                "fase_nome": fase_nome,
                "tabela_origem": tabela_origem,
                "tabela_destino": tabela_destino,
                "etapa": etapa,
                "chunk_atual": chunk_atual,
                "linhas_lidas": linhas_lidas,
                "linhas_escritas": linhas_escritas,
                "linhas_ignoradas": linhas_ignoradas,
                "mensagem": mensagem,
            },
        )

    @transaction.atomic
    def atualizar_checkpoint_dominio(
        self,
        dominio: str,
        ultimo_id_execucao: UUID,
        ultima_pagina: int,
        token_parada: str | None,
        indice_sincronizacao: str | None,
        ultima_situacao: str,
        sucesso: bool,
    ) -> None:
        """Atualiza checkpoint do dominio com upsert transacional."""
        (
            checkpoint,
            criado,
        ) = EtlCheckpointDominio.objects.select_for_update().get_or_create(
            dominio=dominio,
            defaults={
                "ultimo_id_execucao": ultimo_id_execucao,
                "ultima_pagina": ultima_pagina,
                "token_parada": token_parada,
                "indice_sincronizacao": indice_sincronizacao,
                "ultima_situacao": ultima_situacao,
                "ultimo_sucesso_em": timezone.now() if sucesso else None,
            },
        )
        if criado:
            return

        checkpoint.ultimo_id_execucao = ultimo_id_execucao
        checkpoint.ultima_pagina = ultima_pagina
        checkpoint.token_parada = token_parada
        checkpoint.indice_sincronizacao = indice_sincronizacao
        checkpoint.ultima_situacao = ultima_situacao
        if sucesso:
            checkpoint.ultimo_sucesso_em = timezone.now()
        checkpoint.save()

    def upsert_bulk_hashes(
        self,
        rows: list[tuple[str, str]],
        batch_id: str = "batch",
    ) -> int:
        """Executa upsert de hashes de auditoria via COPY + Temp Table.

        Delega para ``PostgresUpsertEngine``, eliminando duplicação da
        lógica de COPY/staging entre este repositório e o motor de ETL.
        """
        from apps.core.libs.base_etl_service import PostgresUpsertEngine

        engine = PostgresUpsertEngine()
        result: int = engine.upsert_bulk("etl_auditoria_linha", rows, batch_id)
        return result
