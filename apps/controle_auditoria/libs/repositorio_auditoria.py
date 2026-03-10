"""Repositorio de auditoria ETL baseado em ORM Django."""

from uuid import UUID, uuid4

from django.db import transaction
from django.utils import timezone

from apps.controle_auditoria.models import (
    EtlCheckpointDominio,
    EtlExecucao,
    EtlExecucaoTabelaLida,
)


class RepositorioAuditoriaPostgres:
    """Persiste estado de execucao e checkpoint por dominio."""

    def iniciar_execucao(self, dominio: str) -> UUID:
        """Cria registro de execucao em andamento."""
        id_execucao = uuid4()
        EtlExecucao.objects.create(
            id_execucao=id_execucao,
            dominio=dominio,
            situacao="em_execucao",
            iniciado_em=timezone.now(),
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

    def obter_checkpoint_dominio(self, dominio: str) -> dict[str, object] | None:
        """Retorna checkpoint atual do dominio."""
        return EtlCheckpointDominio.objects.filter(dominio=dominio).values(
            "dominio",
            "ultimo_id_execucao",
            "ultima_pagina",
            "token_parada",
            "indice_sincronizacao",
            "ultima_situacao",
            "ultimo_sucesso_em",
            "atualizado_em",
        ).first()

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
        checkpoint, criado = EtlCheckpointDominio.objects.select_for_update().get_or_create(
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
