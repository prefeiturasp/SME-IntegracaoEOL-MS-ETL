"""Comando para validar continuidade do domínio escolas."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Executa duas chamadas sequenciais do domínio escolas."""

    help = "Executa escolas e em seguida continua do checkpoint"

    def add_arguments(self, parser):
        parser.add_argument("--volume", type=int, default=100)

    def handle(self, *args, **options):
        volume = options["volume"]
        call_command("listar_escolas_offset", "--volume", str(volume))
        call_command(
            "listar_escolas_offset",
            "--volume",
            str(volume),
            "--continuar",
        )
