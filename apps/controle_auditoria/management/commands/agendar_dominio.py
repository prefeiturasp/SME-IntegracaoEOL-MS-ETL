"""Comando para registrar execução de domínio na fila Celery."""

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.controle_auditoria.libs.tasks import executar_dominio_task


class Command(BaseCommand):
    """Agenda ou enfileira execução de domínio ETL."""

    help = "Registra execução na fila Celery (imediata ou com data/hora futura)"

    def add_arguments(self, parser: Any) -> None:
        """Adiciona argumentos ao comando."""
        parser.add_argument("--dominio", required=True, type=str)
        parser.add_argument("--volume", type=int, default=100)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--continuar", action="store_true")
        parser.add_argument("--executar-em", type=str, default=None)

    def handle(self, *args: Any, **options: Any) -> None:
        """Executa o agendador ETL para todos o dominios."""
        dominio = options["dominio"]
        volume = options["volume"]
        offset = options["offset"]
        continuar = options["continuar"]
        executar_em = options["executar_em"]

        kwargs_tarefa = {
            "dominio": dominio,
            "volume": volume,
            "offset": offset,
            "continuar": continuar,
        }

        if executar_em:
            data_hora = parse_datetime(executar_em)
            if data_hora is None:
                raise CommandError("--executar-em deve estar em ISO-8601")
            if timezone.is_naive(data_hora):
                data_hora = timezone.make_aware(
                    data_hora,
                    timezone.get_current_timezone(),
                )
            resultado = executar_dominio_task.apply_async(
                kwargs=kwargs_tarefa,
                eta=data_hora,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Task agendada: {resultado.id} para {data_hora.isoformat()}"
                )
            )
            return

        resultado = executar_dominio_task.delay(**kwargs_tarefa)
        self.stdout.write(self.style.SUCCESS(f"Task enfileirada: {resultado.id}"))
