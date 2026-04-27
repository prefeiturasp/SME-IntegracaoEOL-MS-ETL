"""Comando Django para executar dominio ETL por app."""

from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.controle_auditoria.libs.servico_sinc_rec_db import (
    exibir_validacao_sinc_rec_db,
)

COMANDOS_POR_DOMINIO: dict[str, str] = {
    "institucional": "etl_institucional",
    "professores": "etl_professores",
    "alunos": "etl_alunos",
    "pedagogico": "etl_pedagogico",
    "programas": "etl_programas",
}

DOMINIOS_VALIDOS = ["sinc_rec_db", *COMANDOS_POR_DOMINIO.keys()]


class Command(BaseCommand):
    """Executa um dominio ETL independente."""

    help = f"Executa dominio ETL: {', '.join(DOMINIOS_VALIDOS)}"

    def add_arguments(self, parser: Any) -> None:
        """Adiciona argumentos ao comando."""
        parser.add_argument("--dominio", required=True, type=str)
        parser.add_argument("--volume", type=int, default=100)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--continuar", action="store_true")
        parser.add_argument(
            "--ano-letivo",
            type=int,
            default=None,
            help=(
                "(pedagogico) Processa apenas anos letivos "
                "a partir deste valor."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Executa o ETL do dominio especificado."""
        dominio = options["dominio"]
        volume = options["volume"]
        offset = options["offset"]
        continuar = options["continuar"]
        ano_letivo = options.get("ano_letivo")

        if dominio == "sinc_rec_db":
            exibir_validacao_sinc_rec_db()
            return

        comando_etl = COMANDOS_POR_DOMINIO.get(dominio)
        if comando_etl is None:
            raise CommandError(
                f"Dominio invalido. Use: {', '.join(DOMINIOS_VALIDOS)}"
            )

        argumentos = ["--volume", str(volume), "--offset", str(offset)]
        if continuar:
            argumentos.append("--continuar")
        if ano_letivo is not None and dominio == "pedagogico":
            argumentos += ["--ano-letivo", str(ano_letivo)]
        call_command(comando_etl, *argumentos)
