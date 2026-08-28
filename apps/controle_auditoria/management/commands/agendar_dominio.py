"""Comando para registrar execução de domínio na fila Celery."""

import logging
from typing import Any
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from kombu.exceptions import OperationalError

from apps.controle_auditoria.libs.dominios import validar_parametros_dominio
from apps.controle_auditoria.libs.tasks import executar_dominio_task

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Agenda ou enfileira execução de domínio ETL."""

    help = (
        "Registra execução na fila Celery "
        "(imediata ou com data/hora futura)"
    )

    def add_arguments(self, parser: Any) -> None:
        """Adiciona argumentos ao comando."""
        parser.add_argument("--dominio", required=True, type=str)
        parser.add_argument("--volume", type=int, default=100)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--continuar", action="store_true")
        parser.add_argument("--executar-em", type=str, default=None)
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

    def handle(self, *args: Any, **options: Any) -> None:
        """Executa o agendador ETL para todos o dominios."""
        dominio = options["dominio"]
        volume = options["volume"]
        offset = options["offset"]
        continuar = options["continuar"]
        executar_em = options["executar_em"]
        fases = options.get("fases")
        anos_letivos = options.get("anos_letivos")

        erro_parametros = validar_parametros_dominio(
            dominio,
            fases=fases,
            anos_letivos=anos_letivos,
        )
        if erro_parametros:
            raise CommandError(erro_parametros)

        kwargs_tarefa = {
            "dominio": dominio,
            "volume": volume,
            "offset": offset,
            "continuar": continuar,
        }
        if fases:
            kwargs_tarefa["fases"] = fases
        if anos_letivos:
            kwargs_tarefa["anos_letivos"] = anos_letivos
        task_id = str(uuid4())
        kwargs_tarefa["parametros_disparo"] = {
            "origem": "management_command",
            "executar_em": executar_em,
            "celery_task_id": task_id,
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
            try:
                resultado = executar_dominio_task.apply_async(
                    kwargs=kwargs_tarefa,
                    eta=data_hora,
                    task_id=task_id,
                )
            except OperationalError as erro:
                logger.error(
                    "Broker indisponível ao agendar domínio '%s': %s",
                    dominio,
                    erro,
                )
                raise CommandError(f"Broker indisponível: {erro}") from erro
            self.stdout.write(
                self.style.SUCCESS(
                    "Task agendada: "
                    f"{resultado.id} para {data_hora.isoformat()}"
                )
            )
            return

        try:
            resultado = executar_dominio_task.apply_async(
                kwargs=kwargs_tarefa,
                task_id=task_id,
            )
        except OperationalError as erro:
            logger.error(
                "Broker indisponível ao enfileirar domínio '%s': %s",
                dominio,
                erro,
            )
            raise CommandError(f"Broker indisponível: {erro}") from erro
        self.stdout.write(
            self.style.SUCCESS(f"Task enfileirada: {resultado.id}")
        )
