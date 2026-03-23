"""Comando Django para executar o ETL do dominio PROFESSORES_DB."""

from typing import Any

from django.core.management.base import BaseCommand

from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)
from apps.professores.services import EtlProfessoresService


class Command(BaseCommand):
    """Executa ETL completo do dominio PROFESSORES_DB."""

    help = "Popula professores_db a partir do EOL (SQL Server)"

    def handle(self, *args: Any, **options: Any) -> None:
        """Executa o ETL e registra auditoria."""
        repositorio = RepositorioAuditoriaPostgres()
        id_execucao = repositorio.iniciar_execucao("professores")

        try:
            servico = EtlProfessoresService()
            resultado = servico.executar()

            for tabela, linhas in resultado.items():
                repositorio.registrar_tabela_escrita(
                    id_execucao=id_execucao,
                    tabela_destino=tabela,
                    linhas_escritas=linhas,
                    modo_escrita=(
                        "upsert"
                        if tabela
                        in {
                            "cargo",
                            "professor",
                            "pessoa",
                            "funcao_funcionario_externo",
                            "cargo_base_servidor",
                            "contrato_externo",
                        }
                        else "full_refresh"
                    ),
                )

            repositorio.finalizar_execucao(id_execucao, situacao="concluido")
            self.stdout.write(
                self.style.SUCCESS(f"ETL PROFESSORES concluido: {resultado}")
            )

        except Exception as erro:
            repositorio.finalizar_execucao(
                id_execucao,
                situacao="erro",
                mensagem_erro=str(erro),
            )
            raise
