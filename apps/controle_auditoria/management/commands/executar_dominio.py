"""Comando Django para executar dominio ETL por app."""

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.controle_auditoria.libs.servico_sinc_rec_db import (
    exibir_validacao_sinc_rec_db,
)


class Command(BaseCommand):
    """Executa um dominio ETL independente."""

    help = "Executa dominio ETL: sinc_rec_db, escola"

    def add_arguments(self, parser):
        parser.add_argument("--dominio", required=True, type=str)
        parser.add_argument("--volume", type=int, default=100)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--continuar", action="store_true")

    def handle(self, *args, **options):
        dominio = options["dominio"]
        volume = options["volume"]
        offset = options["offset"]
        continuar = options["continuar"]

        if dominio == "sinc_rec_db":
            exibir_validacao_sinc_rec_db()
            return

        if dominio in {"escola", "escolas"}:
            argumentos = ["--volume", str(volume), "--offset", str(offset)]
            if continuar:
                argumentos.append("--continuar")
            call_command("listar_escolas_offset", *argumentos)
            return

        raise CommandError("Dominio invalido. Use: sinc_rec_db, escola")
