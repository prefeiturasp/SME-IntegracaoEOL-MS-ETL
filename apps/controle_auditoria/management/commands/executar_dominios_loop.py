"""Comando para executar dominios em loop contínuo."""

import time
from typing import Any, cast

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)


class Command(BaseCommand):
    """Executa dominios em loop com intervalo configurável."""

    help = "Executa os dominios continuamente respeitando intervalo em segundos"

    def add_arguments(self, parser: Any) -> None:
        """Adiciona argumentos do comando."""
        parser.add_argument(
            "--intervalo",
            type=int,
            default=settings.INTERVALO_EXECUCAO_ETL_SEGUNDOS,
        )
        parser.add_argument("--volume", type=int, default=100)
        parser.add_argument("--continuar", action="store_true")
        parser.add_argument("--limite-linhas", type=int, default=None)

    def handle(self, *args: Any, **options: Any) -> None:
        """Executa os dominios continuamente respeitando intervalo em segundos."""
        intervalo: int = options["intervalo"]
        volume: int = options["volume"]
        continuar: bool = options["continuar"]
        limite_linhas: int | None = options["limite_linhas"]

        if limite_linhas is not None and limite_linhas <= 0:
            raise CommandError("--limite-linhas deve ser maior que zero")

        repositorio = RepositorioAuditoriaPostgres()
        total_linhas_processadas: int = 0

        while True:
            volume_execucao = self._calcular_volume(volume, limite_linhas, total_linhas_processadas)
            if volume_execucao <= 0:
                break

            argumentos: list[str] = ["--volume", str(volume_execucao)]
            if continuar:
                argumentos.append("--continuar")

            linhas = self._executar_e_contar(repositorio, argumentos)
            total_linhas_processadas += linhas

            if linhas == 0 or (limite_linhas and total_linhas_processadas >= limite_linhas):
                break

            time.sleep(intervalo)

        self.stdout.write(
            self.style.SUCCESS(
                f"Loop finalizado. linhas_processadas={total_linhas_processadas}"
            )
        )

    def _calcular_volume(self, volume: int, limite: int | None, total: int) -> int:
        """Calcula volume do próximo lote considerando limite total."""
        if limite is None:
            return volume
        restante = limite - total
        return min(volume, restante) if restante > 0 else 0

    def _executar_e_contar(self, repositorio: Any, argumentos: list[str]) -> int:
        """Executa comando e retorna delta de linhas processadas."""
        def _get_token() -> int:
            cp = repositorio.obter_checkpoint_dominio("escola")
            return int(cast(int | str, (cp or {}).get("token_parada", 0)))

        token_antes = _get_token()
        call_command("executar_dominios", *argumentos)
        token_depois = _get_token()
        return max(token_depois - token_antes, 0)
