"""Comando Django para executar dominios ativos."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Executa todos os dominios ativos no momento."""

    help = "Executa dominios ativos: sinc_rec_db e escola"

    def add_arguments(self, parser):
        parser.add_argument("--volume", type=int, default=100)
        parser.add_argument("--continuar", action="store_true")

    def handle(self, *args, **options):
        volume = options["volume"]
        continuar = options["continuar"]

        call_command("executar_dominio", "--dominio", "sinc_rec_db")

        argumentos = [
            "--dominio",
            "escola",
            "--volume",
            str(volume),
        ]
        if continuar:
            argumentos.append("--continuar")
        call_command("executar_dominio", *argumentos)
