"""Comando Django para executar dominios ativos."""

from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Executa todos os dominios ativos no momento."""

    help = "Executa dominios ativos: sinc_rec_db e institucional"

    def add_arguments(self, parser: Any) -> None:
        """Adiciona argumentos ao comando."""
        parser.add_argument("--volume", type=int, default=100)
        parser.add_argument("--continuar", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        """Executa todos os dominios ativos no momento."""
        volume = options["volume"]
        continuar = options["continuar"]

        call_command("executar_dominio", "--dominio", "sinc_rec_db")

        argumentos = [
            "--dominio",
            "institucional",
            "--volume",
            str(volume),
        ]
        if continuar:
            argumentos.append("--continuar")
        call_command("executar_dominio", *argumentos)
