"""Base para verificadores de compatibilidade ETL professores.

Cada verificador valida que uma consulta do ProfessorController.txt retorna
resultados compatíveis entre origem (EolConnection/SQL Server) e destino
(professores_db/PostgreSQL), garantindo que o ETL replica corretamente os
dados necessários para eliminar os INNER JOINs externos no microserviço.

Fluxo de um verificador:
    1. buscar_origem  → consulta na origem com TOP {limite} (sem filtros de
                        parâmetros específicos como @CodigoRF, @AnoLetivo).
    2. buscar_destino → consulta equivalente no professores_db via Django ORM.
    3. comparar       → verifica que as chaves naturais batem entre origem
                        e destino.
    4. ResultadoCompatibilidade → expõe taxa_correspondencia e exemplos de
                                  divergências.

Critério de aprovação: taxa_correspondencia >= 0.8 (80 % das linhas da origem
encontradas no destino com os mesmos campos de chave).
"""

import datetime as _dt
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_LIMIAR_APROVACAO = 0.8
_MAX_EXEMPLOS_DIVERGENCIA = 5


@dataclass
class ResultadoCompatibilidade:
    """Resultado de uma verificação de compatibilidade."""

    verificador: str
    consulta: str
    total_origem: int = 0
    total_destino: int = 0
    correspondencias: int = 0
    divergencias: list[dict] = field(default_factory=list)
    ignorado: bool = False
    motivo_ignorado: str = ""
    erro: str = ""

    @property
    def taxa_correspondencia(self) -> float:
        """Taxa de correspondência (0.0–1.0)."""
        if self.total_origem == 0:
            return 0.0
        return self.correspondencias / self.total_origem

    @property
    def aprovado(self) -> bool:
        """True se aprovado ou não aplicável (ignorado / erro)."""
        if self.ignorado or self.erro:
            return True
        return self.taxa_correspondencia >= _LIMIAR_APROVACAO

    def rotulo(self) -> str:
        """Rótulo de status para exibição."""
        if self.erro:
            return "ERRO"
        if self.ignorado:
            return "IGNORADO"
        return "OK  " if self.aprovado else "FALHA"

    def __str__(self) -> str:
        """Representação resumida do resultado."""
        lbl = self.rotulo()
        if self.erro:
            return f"[{lbl}] {self.verificador}.{self.consulta}: {self.erro}"
        if self.ignorado:
            return (
                f"[{lbl}] {self.verificador}.{self.consulta}:"
                f" {self.motivo_ignorado}"
            )
        return (
            f"[{lbl}] {self.verificador}.{self.consulta}: "
            f"{self.correspondencias}/{self.total_origem} "
            f"({self.taxa_correspondencia:.0%}) "
            f"| destino={self.total_destino}"
        )


def _formatar_data(valor: Any) -> str | None:
    """Normaliza datas para o formato de comparação.

    Args:
        valor: Data recebida para comparação.

    Returns:
        Data normalizada quando houver valor.
    """
    if valor is None:
        return None
    if isinstance(valor, _dt.datetime):
        return valor.date().isoformat()
    if hasattr(valor, "isoformat"):
        return str(valor.isoformat())
    return str(valor)[:10]


class VerificadorBase:
    """Verificador de compatibilidade base.

    Subclasses implementam os três métodos abstratos.

    Atributos de classe:
        nome          Identificador do grupo (ex.: "AtribuicaoAula").
        nome_consulta Nome da consulta (ex.: "BuscaProfessoresAsync").
        limite        Número de linhas a amostrar na origem.
    """

    nome: str = "base"
    nome_consulta: str = "sem_nome"
    limite: int = 30  # linhas amostradas por execução

    # ------------------------------------------------------------------
    # Métodos a implementar
    # ------------------------------------------------------------------

    def buscar_origem(
        self,
        eol: Any,
        limite: int,
    ) -> list[dict[str, Any]]:
        """Executa a consulta na origem e retorna lista de dicts."""
        raise NotImplementedError

    def buscar_destino(
        self,
        linhas_origem: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Executa a consulta equivalente no professores_db."""
        raise NotImplementedError

    def chave_comparacao(self, linha: dict[str, Any]) -> tuple:
        """Extrai a chave de comparação de uma linha (origem ou destino)."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Orquestração
    # ------------------------------------------------------------------

    def executar(
        self, eol: Any, limite: int | None = None
    ) -> ResultadoCompatibilidade:
        """Executa o verificador e retorna ResultadoCompatibilidade."""
        limite_efetivo = limite or self.limite
        resultado = ResultadoCompatibilidade(
            verificador=self.nome, consulta=self.nome_consulta
        )

        try:
            linhas_origem = self.buscar_origem(eol, limite_efetivo)
        except Exception as exc:  # noqa: BLE001
            resultado.erro = f"origem: {exc}"
            logger.exception(
                "[compat] erro ao ler origem em %s.%s",
                self.nome,
                self.nome_consulta,
            )
            return resultado

        if not linhas_origem:
            resultado.ignorado = True
            resultado.motivo_ignorado = "sem dados na origem"
            return resultado

        resultado.total_origem = len(linhas_origem)

        try:
            linhas_destino = self.buscar_destino(linhas_origem)
        except Exception as exc:  # noqa: BLE001
            resultado.erro = f"destino: {exc}"
            logger.exception(
                "[compat] erro ao ler destino em %s.%s",
                self.nome,
                self.nome_consulta,
            )
            return resultado

        resultado.total_destino = len(linhas_destino)
        chaves_destino = {self.chave_comparacao(r) for r in linhas_destino}

        for linha in linhas_origem:
            chave = self.chave_comparacao(linha)
            if chave in chaves_destino:
                resultado.correspondencias += 1
            elif len(resultado.divergencias) < _MAX_EXEMPLOS_DIVERGENCIA:
                resultado.divergencias.append({"chave": chave, "linha": linha})

        return resultado
