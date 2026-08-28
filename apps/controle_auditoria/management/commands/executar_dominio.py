"""Comando Django para executar dominio ETL por app."""

from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.controle_auditoria.libs.dominios import (
    COMANDOS_POR_DOMINIO,
    DOMINIOS_VALIDOS,
    validar_parametros_dominio,
)


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
            "--fases",
            nargs="+",
            default=None,
            metavar="FASE",
            help="Executa apenas as fases informadas (pelo nome).",
        )
        parser.add_argument(
            "--anos-letivos",
            type=int,
            nargs="+",
            default=None,
            metavar="ANO",
            help=(
                "(alunos/pedagogico/professores/programas) Processa apenas "
                "os anos letivos informados."
            ),
        )
        parser.add_argument("--parametros-disparo", type=str, default=None)

    def handle(self, *args: Any, **options: Any) -> None:
        """Executa o ETL do dominio especificado."""
        dominio = options["dominio"]
        volume = options["volume"]
        offset = options["offset"]
        continuar = options["continuar"]
        fases = options.get("fases")
        anos_letivos = options.get("anos_letivos")

        erro_parametros = validar_parametros_dominio(
            dominio,
            fases=fases,
            anos_letivos=anos_letivos,
        )
        if erro_parametros:
            raise CommandError(erro_parametros)

        comando_etl = COMANDOS_POR_DOMINIO.get(dominio)

        argumentos = ["--volume", str(volume), "--offset", str(offset)]
        if continuar:
            argumentos.append("--continuar")
        if fases:
            argumentos += ["--fases", *fases]
        if anos_letivos:
            argumentos += ["--anos-letivos", *[str(a) for a in anos_letivos]]
        if options.get("parametros_disparo"):
            argumentos += [
                "--parametros-disparo",
                str(options["parametros_disparo"]),
            ]
        call_command(str(comando_etl), *argumentos)
