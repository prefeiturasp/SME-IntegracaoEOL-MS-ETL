"""Command para listar escolas por offset/limit."""

import json

from django.core.management.base import BaseCommand, CommandError

from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)
from apps.escolas.libs.servico_offset import ServicoEscolasOffset


class Command(BaseCommand):
    """Lista escolas em blocos de offset para validacao de carga."""

    help = (
        "Lista escolas por offset/limit e salva checkpoint de continuidade "
        "no SINC_REC_DB"
    )

    def add_arguments(self, parser):
        parser.add_argument("--volume", type=int, default=100)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--continuar", action="store_true")

    def handle(self, *args, **options):
        volume = options["volume"]
        offset = options["offset"]
        continuar = options["continuar"]

        if volume <= 0:
            raise CommandError("--volume deve ser maior que zero")
        if offset < 0:
            raise CommandError("--offset nao pode ser negativo")

        repositorio = RepositorioAuditoriaPostgres()
        checkpoint = repositorio.obter_checkpoint_dominio("escola")

        offset_inicial = offset
        pagina_inicial = 0
        if continuar and checkpoint:
            offset_inicial = int(checkpoint.get("token_parada") or 0)
            pagina_inicial = int(checkpoint.get("ultima_pagina") or 0)

        id_execucao = repositorio.iniciar_execucao("escola")
        servico = ServicoEscolasOffset()

        try:
            registros = servico.listar_volume(
                volume=volume,
                offset_inicial=offset_inicial,
            )
            paginas_lidas = (len(registros) + 99) // 100 if registros else 0
            pagina_final = pagina_inicial + paginas_lidas
            token_parada = str(offset_inicial + len(registros))

            repositorio.registrar_tabela_lida(
                id_execucao=id_execucao,
                tabela_origem="dbo.v_cadastro_unidade_educacao",
                numero_pagina=pagina_final,
                linhas_lidas=len(registros),
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
            repositorio.finalizar_execucao(id_execucao=id_execucao, situacao="sucesso")

            print("=== DOMINIO ESCOLA ===")
            print(f"id_execucao: {id_execucao}")
            print(f"pagina_lida: {pagina_final}")
            print(f"token_parada: {token_parada}")
            print(f"total_registros: {len(registros)}")
            print("registros:")
            print(json.dumps(registros, default=str, ensure_ascii=True, indent=2))
        except Exception as erro:
            repositorio.atualizar_checkpoint_dominio(
                dominio="escola",
                ultimo_id_execucao=id_execucao,
                ultima_pagina=pagina_inicial,
                token_parada=str(offset_inicial),
                indice_sincronizacao=f"escola:offset:{offset_inicial}",
                ultima_situacao="falha",
                sucesso=False,
            )
            repositorio.finalizar_execucao(
                id_execucao=id_execucao,
                situacao="falha",
                mensagem_erro=str(erro),
            )
            raise
