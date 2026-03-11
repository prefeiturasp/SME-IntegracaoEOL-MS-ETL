"""Command para listar escolas por offset/limit."""

import json
from typing import Any, cast
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)
from apps.escolas.libs.servico_offset import ServicoEscolasOffset


class Command(BaseCommand):
    """Lista escolas em blocos de offset para validação de carga."""

    help = (
        "Lista escolas por offset/limit e salva checkpoint de continuidade "
        "no SINC_REC_DB"
    )

    def add_arguments(self, parser: Any) -> None:
        """Adiciona argumentos ao comando."""
        parser.add_argument("--volume", type=int, default=100)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--continuar", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        """Executa o ETL do domínio especificado."""
        volume: int = options["volume"]
        offset: int = options["offset"]
        continuar: bool = options["continuar"]

        if volume <= 0:
            raise CommandError("--volume deve ser maior que zero")
        if offset < 0:
            raise CommandError("--offset nao pode ser negativo")

        repositorio = RepositorioAuditoriaPostgres()
        checkpoint = repositorio.obter_checkpoint_dominio("escola")

        offset_inicial: int = offset
        pagina_inicial: int = 0

        if continuar and checkpoint:
            token_parada_valor = checkpoint.get("token_parada", 0)
            ultima_pagina_valor = checkpoint.get("ultima_pagina", 0)

            offset_inicial = int(cast(int | str, token_parada_valor))
            pagina_inicial = int(cast(int | str, ultima_pagina_valor))

        id_execucao: UUID = repositorio.iniciar_execucao("escola")
        servico = ServicoEscolasOffset()

        registros: list[dict[str, object]] = []

        offset_atual: int = offset_inicial
        pagina_atual: int = pagina_inicial
        restante: int = volume

        try:
            while restante > 0:
                limite_pagina = min(servico.TAMANHO_PAGINA_PADRAO, restante)

                lote = servico.listar_pagina(
                    limite=limite_pagina,
                    offset=offset_atual,
                )

                if not lote:
                    break

                pagina_atual += 1
                linhas_lote = len(lote)

                registros.extend(lote)

                offset_atual += linhas_lote
                restante -= linhas_lote

                repositorio.registrar_tabela_lida(
                    id_execucao=id_execucao,
                    tabela_origem="dbo.v_cadastro_unidade_educacao",
                    numero_pagina=pagina_atual,
                    linhas_lidas=linhas_lote,
                )

                repositorio.atualizar_checkpoint_dominio(
                    dominio="escola",
                    ultimo_id_execucao=id_execucao,
                    ultima_pagina=pagina_atual,
                    token_parada=str(offset_atual),
                    indice_sincronizacao=f"escola:offset:{offset_atual}",
                    ultima_situacao="em_execucao",
                    sucesso=False,
                )

                if linhas_lote < limite_pagina:
                    break

            pagina_final: int = pagina_atual
            token_parada: str = str(offset_atual)

            repositorio.registrar_tabela_escrita(
                id_execucao=id_execucao,
                tabela_destino="console.saida_validacao_escolas",
                linhas_escritas=len(registros),
                modo_escrita="validacao",
            )

            repositorio.atualizar_checkpoint_dominio(
                dominio="escola",
                ultimo_id_execucao=id_execucao,
                ultima_pagina=pagina_final,
                token_parada=token_parada,
                indice_sincronizacao=f"escola:offset:{token_parada}",
                ultima_situacao="sucesso",
                sucesso=True,
            )

            repositorio.finalizar_execucao(
                id_execucao=id_execucao,
                situacao="sucesso",
            )

            print("=== DOMINIO ESCOLA ===")
            print(f"id_execucao: {id_execucao}")
            print(f"pagina_lida: {pagina_final}")
            print(f"token_parada: {token_parada}")
            print(f"total_registros: {len(registros)}")
            print("registros:")

            print(
                json.dumps(
                    registros,
                    default=str,
                    ensure_ascii=True,
                    indent=2,
                )
            )

        except Exception as erro:
            repositorio.atualizar_checkpoint_dominio(
                dominio="escola",
                ultimo_id_execucao=id_execucao,
                ultima_pagina=pagina_atual,
                token_parada=str(offset_atual),
                indice_sincronizacao=f"escola:offset:{offset_atual}",
                ultima_situacao="falha",
                sucesso=False,
            )

            repositorio.finalizar_execucao(
                id_execucao=id_execucao,
                situacao="falha",
                mensagem_erro=str(erro),
            )

            raise
