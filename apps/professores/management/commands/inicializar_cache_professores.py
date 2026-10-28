"""Inicializa o controle de geração após validação das fontes existentes."""

from typing import Any
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.controle_auditoria.models import EtlExecucao
from apps.professores.models import ControleCargaProfessores


class Command(BaseCommand):
    """Confirma a disponibilidade inicial das fontes de professores."""

    help = "Inicializa uma geração após conferir uma carga concluída."

    def add_arguments(self, parser: Any) -> None:
        """Declara a confirmação da integridade das fontes."""
        parser.add_argument(
            "--confirmar-fontes-completas",
            action="store_true",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Confirma fontes completas quando não há cargas ativas."""
        if not options["confirmar_fontes_completas"]:
            raise CommandError(
                "Confirme primeiro que as fontes estão completas."
            )
        execucoes = EtlExecucao.objects.filter(dominio="professores")
        if execucoes.filter(
            situacao__in=["em_execucao", "em_andamento"]
        ).exists():
            raise CommandError("Há execução de professores em andamento.")
        ultima = execucoes.order_by("-iniciado_em").first()
        if ultima is None or ultima.situacao != "concluido":
            raise CommandError("A última carga não foi concluída com sucesso.")

        with transaction.atomic(using="professores_db"):
            estados = ControleCargaProfessores.objects.using("professores_db")
            estados.get_or_create(pk=1)
            estado = estados.select_for_update().get(pk=1)
            if estado.cargas_ativas:
                raise CommandError(
                    "Há registro de carga ativa ou interrompida."
                )
            estado.geracao = uuid4()
            estado.falha = False
            estado.save(using="professores_db")
        self.stdout.write("Geração inicial registrada após carga concluída.")
