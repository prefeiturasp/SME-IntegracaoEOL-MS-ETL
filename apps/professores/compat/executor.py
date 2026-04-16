"""Executor de compatibilidade.

Executa todos os verificadores e agrega resultados.

Uso programático:
    from apps.professores.compat.executor import ExecutorCompatibilidade
    from apps.eol_connection.libs.servico_eol import EOLService

    executor = ExecutorCompatibilidade(EOLService(), limite=30)
    resultados = executor.executar_todos()
    for r in resultados:
        print(r)

Consultas cobertas (ProfessorController.txt):
    FuncionarioRepository
        BuscaFuncionarioPorRfAsync ......... VerificadorCargoBaseAtivo

    PerfilSGPRepository
        BuscarInformacoesPerfilProfAsync ... VerificadorPerfilProfServidor
        BuscarInformacoesPerfilProf (ext)  . VerificadorPerfilProfExterno

    ProfessorRepository
        BuscaProfessoresAsync .............. VerificadorAtribuicaoAula
        BuscaProfessoresAsync (ext) ........ VerificadorAtribuicaoExterno
        BuscarProfessorTitular ............. VerificadorTitularServidor
        BuscarProfessorTitular (ext) ....... VerificadorTitularExterno
        VerificarValidadeProfessorAsync .... VerificadorValidadeProf
        VerificaSeEhTurmaDeProgramaAsync ... VerificadorTurmaEscola
        VerificaSeTemAtribuicaoNaTurma .... VerificadorTurmaEscolaGradePrograma

    ComponenteCurricularRepository
        ObterComponentesCurricularesTerr ... VerificadorTerritorioReplicado
        ObterComponentesCurriculares(join)  . VerificadorTerritorioAtribuicao

    AgrupamentoAtribuicaoTerritorioSaber
        VerificadorAgrupamentoTS ........ popular_agrupamentos_territorio_saber
"""

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
from apps.professores.compat.checkers.territorio import (
    VerificadorAgrupamentoTS,
    VerificadorTerritorioAtribuicao,
    VerificadorTerritorioReplicado,
)
from apps.professores.compat.checkers.turma_escola import (
    VerificadorTurmaEscola,
    VerificadorTurmaEscolaGradePrograma,
)

logger = logging.getLogger(__name__)

_TODOS_VERIFICADORES = [
    # Funcionário / Cargo Base
    VerificadorCargoBaseAtivo,
    VerificadorValidadeProf,
    # Perfil professor — servidor
    VerificadorPerfilProfServidor,
    # Perfil professor — externo
    VerificadorPerfilProfExterno,
    # AtribuicaoAula (servidor)
    VerificadorAtribuicaoAula,
    VerificadorTitularServidor,
    # AtribuicaoExterno
    VerificadorAtribuicaoExterno,
    VerificadorTitularExterno,
    # TurmaEscola / TurmaEscolaGradePrograma
    VerificadorTurmaEscola,
    VerificadorTurmaEscolaGradePrograma,
    # Território do Saber (ComponenteCurricular)
    VerificadorTerritorioReplicado,
    VerificadorTerritorioAtribuicao,
    # AgrupamentoAtribuicaoTerritorioSaber
    VerificadorAgrupamentoTS,
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
