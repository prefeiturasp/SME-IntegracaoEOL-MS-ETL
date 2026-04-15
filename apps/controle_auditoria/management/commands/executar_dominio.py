"""Comando Django para executar dominio ETL por app."""

from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.controle_auditoria.libs.servico_sinc_rec_db import (
    exibir_validacao_sinc_rec_db,
)


class Command(BaseCommand):
    """Executa um dominio ETL independente."""

    help = (
        "Executa dominio ETL: sinc_rec_db, institucional, professores, "
        "alunos, pedagogico, programas"
    )

    def add_arguments(self, parser: Any) -> None:
        """Adiciona argumentos ao comando."""
        parser.add_argument("--dominio", required=True, type=str)
        parser.add_argument("--volume", type=int, default=100)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--continuar", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        """Executa o ETL do dominio especificado."""
        dominio = options["dominio"]
        volume = options["volume"]
        offset = options["offset"]
        continuar = options["continuar"]

        if dominio == "sinc_rec_db":
            exibir_validacao_sinc_rec_db()
            return

        if dominio == "institucional":
            argumentos = ["--volume", str(volume), "--offset", str(offset)]
            if continuar:
                argumentos.append("--continuar")
            call_command("etl_institucional", *argumentos)
            return

        if dominio == "professores":
            argumentos = ["--volume", str(volume), "--offset", str(offset)]
            if continuar:
                argumentos.append("--continuar")
            call_command("etl_professores", *argumentos)
            return

        if dominio == "alunos":
            argumentos = ["--volume", str(volume), "--offset", str(offset)]
            if continuar:
                argumentos.append("--continuar")
            call_command("etl_alunos", *argumentos)
            return

        if dominio == "pedagogico":
            argumentos = ["--volume", str(volume), "--offset", str(offset)]
            if continuar:
                argumentos.append("--continuar")
            call_command("etl_pedagogico", *argumentos)
            return

        if dominio == "programas":
            argumentos = ["--volume", str(volume), "--offset", str(offset)]
            if continuar:
                argumentos.append("--continuar")
            call_command("etl_programas", *argumentos)
            return

        raise CommandError(
            "Dominio invalido. Use: sinc_rec_db, institucional, professores, alunos, pedagogico, programas"
        )
