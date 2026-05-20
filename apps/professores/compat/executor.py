"""Executor de compatibilidade e agrega de resultados."""

import logging
from typing import Any

from apps.professores.compat.base import ResultadoCompatibilidade
from apps.professores.compat.checkers.atribuicao_aula import (
    VerificadorAtribuicaoAula,
    VerificadorPerfilProfServidor,
    VerificadorTitularServidor,
)
from apps.professores.compat.checkers.atribuicao_externo import (
    VerificadorAtribuicaoExterno,
    VerificadorPerfilProfExterno,
    VerificadorTitularExterno,
)
from apps.professores.compat.checkers.cargo_base import (
    VerificadorCargoBaseAtivo,
    VerificadorValidadeProf,
)

logger = logging.getLogger(__name__)

_TODOS_VERIFICADORES = [
    VerificadorCargoBaseAtivo,
    VerificadorValidadeProf,
    VerificadorPerfilProfServidor,
    VerificadorPerfilProfExterno,
    VerificadorAtribuicaoAula,
    VerificadorTitularServidor,
    VerificadorAtribuicaoExterno,
    VerificadorTitularExterno,
]


class ExecutorCompatibilidade:
    """Executa todos os verificadores e retorna lista de resultados."""

    def __init__(self, eol: Any, limite: int = 30) -> None:
        """Inicializa com EOLService e limite de linhas por verificador."""
        self.eol = eol
        self.limite = limite

    def executar_todos(self) -> list[ResultadoCompatibilidade]:
        """Executa todos os verificadores registrados."""
        resultados: list[ResultadoCompatibilidade] = []
        for cls in _TODOS_VERIFICADORES:
            verificador = cls()
            logger.info(
                "[compat] executando %s.%s",
                verificador.nome,
                verificador.nome_consulta,
            )
            resultado = verificador.executar(self.eol, limite=self.limite)
            resultados.append(resultado)
            logger.info("[compat] %s", resultado)
        return resultados

    def resumo(
        self, resultados: list[ResultadoCompatibilidade]
    ) -> dict[str, Any]:
        """Agrega resultados em sumário executivo."""
        aprovados = [r for r in resultados if r.aprovado and not r.ignorado]
        reprovados = [
            r for r in resultados if not r.aprovado and not r.ignorado
        ]
        ignorados = [r for r in resultados if r.ignorado]
        erros = [r for r in resultados if r.erro]

        return {
            "total": len(resultados),
            "aprovados": len(aprovados),
            "reprovados": len(reprovados),
            "ignorados": len(ignorados),
            "erros": len(erros),
            "compativel": (len(reprovados) == 0 and len(erros) == 0),
            "detalhes": [str(r) for r in resultados],
            "falhas": [str(r) for r in reprovados],
        }
