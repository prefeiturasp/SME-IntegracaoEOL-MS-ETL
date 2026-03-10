"""Comando para executar dominios em loop contínuo."""

import time

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)


class Command(BaseCommand):
    """Executa dominios em loop com intervalo configurável."""

    help = "Executa os dominios continuamente respeitando intervalo em segundos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--intervalo",
            type=int,
            default=settings.INTERVALO_EXECUCAO_ETL_SEGUNDOS,
        )
        parser.add_argument("--volume", type=int, default=100)
        parser.add_argument("--continuar", action="store_true")
        parser.add_argument("--limite-linhas", type=int, default=None)

    def handle(self, *args, **options):
        intervalo = options["intervalo"]
        volume = options["volume"]
        continuar = options["continuar"]
        limite_linhas = options["limite_linhas"]

        if limite_linhas is not None and limite_linhas <= 0:
            raise CommandError("--limite-linhas deve ser maior que zero")

        repositorio = RepositorioAuditoriaPostgres()
        total_linhas_processadas = 0
        while True:
            volume_execucao = volume
            if limite_linhas is not None:
                restante = limite_linhas - total_linhas_processadas
                if restante <= 0:
                    break
                volume_execucao = min(volume, restante)

            argumentos = ["--volume", str(volume_execucao)]
            if continuar:
                argumentos.append("--continuar")

            checkpoint_antes = repositorio.obter_checkpoint_dominio("escola")
            token_antes = int((checkpoint_antes or {}).get("token_parada") or 0)

            call_command("executar_dominios", *argumentos)

            checkpoint_depois = repositorio.obter_checkpoint_dominio("escola")
            token_depois = int((checkpoint_depois or {}).get("token_parada") or 0)
            linhas = max(token_depois - token_antes, 0)
            total_linhas_processadas += linhas

            if linhas == 0:
                break

            if limite_linhas is not None and total_linhas_processadas >= limite_linhas:
                break
            time.sleep(intervalo)

        self.stdout.write(
            self.style.SUCCESS(
                "Loop finalizado. linhas_processadas="
                f"{total_linhas_processadas}"
            )
        )
