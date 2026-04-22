"""Verifica compatibilidade entre EolConnection e professores_db.

Executa os verificadores definidos em apps/professores/compat/ e exibe um
relatório de compatibilidade por query do ProfessorController.

Fluxo:
    1. (Opcional) Executa o ETL com --rodar-etl para popular o professores_db
       com uma amostra de {limite} linhas por tabela.
    2. Para cada verificador, busca {limite} linhas na origem (EolConnection) e
       no destino (professores_db) e compara os campos-chave.
    3. Exibe relatório com taxa de compatibilidade por query.
    4. Retorna código de saída 1 se qualquer verificador reprovar.

Uso:
    # Apenas verificar (ETL já rodou):
    python manage.py compat_professores

    # Rodar ETL com 30 linhas antes de verificar:
    python manage.py compat_professores --rodar-etl

    # Alterar limite de amostragem:
    python manage.py compat_professores --limite 50

    # Exibir divergências detalhadas:
    python manage.py compat_professores --detalhes

    # Salvar resultado em JSON:
    python manage.py compat_professores --saida resultado.json
"""

import json
import os
import sys
from typing import Any

from django.core.management.base import BaseCommand

from apps.eol_connection.libs.servico_eol import EOLService
from apps.professores.compat.executor import ExecutorCompatibilidade


class Command(BaseCommand):
    """Verifica compatibilidade ETL professores entre origem e destino."""

    help = (
        "Compara {limite} linhas por query do ProfessorController entre "
        "EolConnection (origem) e professores_db (destino)."
    )

    def add_arguments(self, parser: Any) -> None:
        """Declara argumentos do comando."""
        parser.add_argument(
            "--limite",
            type=int,
            default=30,
            help=(
                "Número de linhas a amostrar por verificador (default: 30). "
                "Mínimo recomendado: 30 para cobertura adequada."
            ),
        )
        parser.add_argument(
            "--rodar-etl",
            action="store_true",
            help=(
                "Executa o ETL de professores antes da verificação, "
                "usando EOL_CHUNK_SIZE={limite} e EOL_LOTE_MAXIMO=1 "
                "para processar apenas uma amostra."
            ),
        )
        parser.add_argument(
            "--detalhes",
            action="store_true",
            help=(
                "Exibe exemplos de divergências para cada verificador "
                "reprovado."
            ),
        )
        parser.add_argument(
            "--saida",
            type=str,
            default=None,
            help=("Caminho de arquivo JSON para salvar o resultado completo."),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Executa verificação de compatibilidade."""
        limite: int = options["limite"]
        rodar_etl: bool = options["rodar_etl"]
        mostrar_detalhes: bool = options["detalhes"]
        arquivo_saida: str | None = options["saida"]

        self._executar_etl_se_necessario(limite, rodar_etl)

        self.stdout.write(
            self.style.HTTP_INFO(
                f"\n[compat] Iniciando verificação de compatibilidade "
                f"(limite={limite})...\n"
            )
        )

        eol = EOLService()
        executor = ExecutorCompatibilidade(eol, limite=limite)
        resultados = executor.executar_todos()
        sumario = executor.resumo(resultados)

        self._imprimir_relatorio(resultados, mostrar_detalhes)
        self._imprimir_sumario(sumario)
        self._exportar_json_se_necessario(arquivo_saida, sumario, resultados)

        if not sumario["compativel"]:
            sys.exit(1)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _executar_etl_se_necessario(
        self, limite: int, rodar_etl: bool
    ) -> None:
        """Executa ETL amostral se --rodar-etl foi passado."""
        if rodar_etl:
            self._executar_etl_amostral(limite)

    def _imprimir_resultado(
        self, resultado: Any, mostrar_detalhes: bool
    ) -> None:
        """Imprime linha do relatório para um único verificador."""
        if (
            resultado.aprovado
            and not resultado.ignorado
            and not resultado.erro
        ):
            linha = self.style.SUCCESS(str(resultado))
        elif resultado.ignorado:
            linha = self.style.WARNING(str(resultado))
        else:
            linha = self.style.ERROR(str(resultado))

        self.stdout.write(linha)

        if mostrar_detalhes and resultado.divergencias:
            self.stdout.write(
                self.style.WARNING("  Divergências (máx. 5 exemplos):")
            )
            for ex in resultado.divergencias:
                self.stdout.write(f"    {ex}")

    def _imprimir_relatorio(
        self, resultados: Any, mostrar_detalhes: bool
    ) -> None:
        """Imprime cabeçalho e todos os resultados por verificador."""
        self.stdout.write("=" * 72)
        self.stdout.write(
            self.style.HTTP_INFO(
                "RELATÓRIO DE COMPATIBILIDADE — PROFESSORES_DB"
            )
        )
        self.stdout.write("=" * 72)
        for resultado in resultados:
            self._imprimir_resultado(resultado, mostrar_detalhes)

    def _imprimir_sumario(self, sumario: dict) -> None:
        """Imprime totais e lista de falhas do sumário."""
        self.stdout.write("=" * 72)
        self.stdout.write(
            f"Total: {sumario['total']}  "
            f"OK: {sumario['aprovados']}  "
            f"FALHA: {sumario['reprovados']}  "
            f"IGNORADO: {sumario['ignorados']}  "
            f"ERRO: {sumario['erros']}"
        )

        if sumario["compativel"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✓ professores_db está COMPATÍVEL com EolConnection."
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "\n✗ professores_db NÃO está totalmente compatível."
                )
            )
            if sumario["falhas"]:
                self.stdout.write(self.style.ERROR("  Queries reprovadas:"))
                for falha in sumario["falhas"]:
                    self.stdout.write(f"    {falha}")

    def _exportar_json_se_necessario(
        self,
        arquivo_saida: str | None,
        sumario: dict,
        resultados: Any,
    ) -> None:
        """Salva resultado em JSON se --saida foi informado."""
        if arquivo_saida:
            self._salvar_json(arquivo_saida, sumario, resultados)
            self.stdout.write(
                self.style.SUCCESS(
                    f"[compat] Resultado salvo em: {arquivo_saida}"
                )
            )

    def _executar_etl_amostral(self, limite: int) -> None:
        """Executa o ETL com limite de amostragem via variáveis de ambiente."""
        self.stdout.write(
            self.style.WARNING(
                f"[compat] Executando ETL amostral "
                f"(EOL_CHUNK_SIZE={limite}, EOL_LOTE_MAXIMO=1)..."
            )
        )
        os.environ["EOL_CHUNK_SIZE"] = str(limite)
        os.environ["EOL_LOTE_MAXIMO"] = "1"

        from apps.professores.services import EtlProfessoresService

        try:
            srv = EtlProfessoresService()
            resultado_etl = srv.executar(fase_inicial=1)
            total = sum(resultado_etl.values())
            self.stdout.write(
                self.style.SUCCESS(
                    f"[compat] ETL amostral concluído. "
                    f"Registros alterados: {total}."
                )
            )
        finally:
            # Restaura env vars para não contaminar o processo
            os.environ.pop("EOL_CHUNK_SIZE", None)
            os.environ.pop("EOL_LOTE_MAXIMO", None)

    def _salvar_json(
        self,
        caminho: str,
        sumario: dict,
        resultados: Any,
    ) -> None:
        """Serializa o sumário e detalhes em JSON."""
        payload = {
            **sumario,
            "resultados": [
                {
                    "verificador": r.verificador,
                    "consulta": r.consulta,
                    "total_origem": r.total_origem,
                    "total_destino": r.total_destino,
                    "correspondencias": r.correspondencias,
                    "taxa_correspondencia": round(r.taxa_correspondencia, 4),
                    "aprovado": r.aprovado,
                    "ignorado": r.ignorado,
                    "motivo_ignorado": r.motivo_ignorado,
                    "erro": r.erro,
                    "divergencias": r.divergencias,
                }
                for r in resultados
            ],
        }
        with open(caminho, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, indent=2, ensure_ascii=False, default=str)
