"""Comando Django para cancelar execuções ETL em andamento."""

from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.controle_auditoria.models import EtlExecucao


class Command(BaseCommand):
    """Cancela execuções ETL que ficaram presas em 'em_execucao'."""

    help = "Cancela todas (ou de um domínio) as execuções em andamento"

    def add_arguments(self, parser: Any) -> None:
        """Adiciona argumentos opcionais."""
        parser.add_argument(
            "--dominio",
            type=str,
            default="",
            help="Filtra por domínio (omitir = todos os domínios)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Marca execuções em_execucao como cancelado."""
        dominio = options["dominio"].strip()

        qs = EtlExecucao.objects.filter(situacao="em_execucao")
        if dominio:
            qs = qs.filter(dominio=dominio)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("Nenhuma execução em andamento."))
            return

        self.stdout.write(f"Execuções encontradas: {total}")
        for exec_obj in qs.values("id_execucao", "dominio", "iniciado_em"):
            self.stdout.write(
                f"  [{exec_obj['dominio']}] {exec_obj['id_execucao']}"
                f" — iniciada em {exec_obj['iniciado_em']}"
            )

        canceladas = qs.update(
            situacao="cancelado",
            finalizado_em=timezone.now(),
            mensagem_erro="Cancelado manualmente via comando cancelar_execucoes",
        )

        self.stdout.write(
            self.style.SUCCESS(f"{canceladas} execução(ões) cancelada(s).")
        )
