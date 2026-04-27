"""Enums e mapeamentos do domínio Programas.

Centraliza os valores do EOL usados pelo domínio:
    - CategoriaPrograma           PAP / PAEE
    - TipoProgramaEOL             cd_tipo_programa → categoria
    - ComponenteCurricularEOL     cd_componente_curricular → categoria + vigência
    - SituacaoTurma               st_turma_escola (O/A/C/E)
    - SituacaoMatricula           st_matricula / cd_situacao_aluno (1-17)

Os enums substituem:
    - O CASE WHEN embutido no SQL_MATRICULA_TURMA_PROGRAMA (services.py)
    - Os dicts _CATEGORIA_POR_TIPO_PROGRAMA, _CATEGORIA_POR_COMPONENTE
      e frozensets _COMPONENTES_*_VIGENTES do model_out.py
    - As constantes PAP/PAEE duplicadas nos models
"""

from enum import IntEnum, StrEnum

from django.db import models


class CategoriaPrograma(models.TextChoices):
    """Categoria de programa — PAP ou PAEE.

    Herda de TextChoices (e não StrEnum) para expor `.choices` consumível
    diretamente pelo `choices=` do CharField nos models. O comportamento
    como string é preservado — `CategoriaPrograma.PAP == "PAP"`.
    """

    PAP = "PAP", "PAP"
    PAEE = "PAEE", "PAEE"


class TipoProgramaEOL(IntEnum):
    """Subset histórico de cd_tipo_programa do EOL.

    Mantido por retrocompatibilidade — não é mais usado como filtro de extração.
    A descoberta no EOL (2026-04) revelou ~20 códigos distintos de cd_tipo_programa
    associados a turmas PAP/PAEE (ex: 94/95/96/97 SRM Complementar, 426 PAP,
    603 PAP Colaborativo, etc.). Filtrar por uma lista hardcoded é frágil.

    A nova estratégia: identificar PAP/PAEE pelo componente curricular (estável)
    e derivar a categoria pela sigla/descrição vinda da própria tabela tipo_programa
    do EOL via :meth:`categoria_por_sigla`.
    """

    PAP_RECUPERACAO = 649
    PAP_COLABORATIVO = 650
    PAEE_SRM = 656
    PAEE_COLABORATIVO = 657
    PAEE_ITINERANTE = 658

    @classmethod
    def categoria_por_sigla(
        cls, sigla: str | None, descricao: str | None = None
    ) -> CategoriaPrograma:
        """Deriva PAP/PAEE pela sigla/descrição do tipo_programa do EOL.

        PAEE quando a sigla ou descrição contém "PAEE" ou "SRM"; PAP caso contrário.
        Substitui a tabela hardcoded de códigos como fonte de verdade.
        """
        textos = " ".join(
            t.upper() for t in (sigla, descricao) if t
        )
        if "PAEE" in textos or "SRM" in textos:
            return CategoriaPrograma.PAEE
        return CategoriaPrograma.PAP

    @classmethod
    def codigos(cls) -> tuple[int, ...]:
        """Retorna os códigos canônicos históricos (uso restrito a testes)."""
        return tuple(m.value for m in cls)


class ComponenteCurricularEOL(IntEnum):
    """cd_componente_curricular do EOL para os componentes de PAP/PAEE."""

    PAP_RECUPERACAO_APRENDIZAGENS = 1322
    PAP_PROJETO_COLABORATIVO = 1770
    PAP_2ANO_ALFABETIZACAO = 1804
    PAP_2ANO_COLABORATIVO_ALFABETIZACAO = 1805

    PAP_LEGADO_MATEMATICA = 1033
    PAP_LEGADO_CIENCIAS = 1051
    PAP_LEGADO_GEOGRAFIA = 1052
    PAP_LEGADO_HISTORIA = 1053
    PAP_LEGADO_PORTUGUES = 1054

    PAEE_SALA_RECURSOS_MULTIFUNCIONAIS = 1030

    @classmethod
    def categoria(cls, codigo: int | str | None) -> CategoriaPrograma:
        """Retorna a categoria (PAP/PAEE) a partir do cd_componente_curricular."""
        try:
            cod = int(codigo) if codigo is not None else None
        except (ValueError, TypeError):
            return CategoriaPrograma.PAP

        if cod in _COMPONENTES_PAEE:
            return CategoriaPrograma.PAEE
        return CategoriaPrograma.PAP

    @classmethod
    def vigente(cls, codigo: int | str | None) -> bool:
        """Retorna True se o componente está vigente (não é legado)."""
        try:
            cod = int(codigo) if codigo is not None else None
        except (ValueError, TypeError):
            return False
        return cod in _COMPONENTES_VIGENTES

    @classmethod
    def codigos(cls) -> tuple[int, ...]:
        """Retorna todos os códigos como tupla — útil para filtros SQL IN (...)."""
        return tuple(m.value for m in cls)


_COMPONENTES_PAEE: frozenset[int] = frozenset(
    {ComponenteCurricularEOL.PAEE_SALA_RECURSOS_MULTIFUNCIONAIS}
)

_COMPONENTES_VIGENTES: frozenset[int] = frozenset(
    {
        ComponenteCurricularEOL.PAP_RECUPERACAO_APRENDIZAGENS,
        ComponenteCurricularEOL.PAP_PROJETO_COLABORATIVO,
        ComponenteCurricularEOL.PAP_2ANO_ALFABETIZACAO,
        ComponenteCurricularEOL.PAP_2ANO_COLABORATIVO_ALFABETIZACAO,
        ComponenteCurricularEOL.PAEE_SALA_RECURSOS_MULTIFUNCIONAIS,
    }
)


class SituacaoTurma(StrEnum):
    """st_turma_escola do EOL."""

    ORGANIZADA = "O"
    NAO_ORGANIZADA = "A"
    CONCLUIDA = "C"
    EXTINTA = "E"

    @classmethod
    def get_descricao(cls, codigo: str | None) -> str:
        """Retorna a descrição amigável para o código."""
        if codigo is None:
            return "Não Informada"

        mapeamento = {
            cls.ORGANIZADA: "Organizada",
            cls.NAO_ORGANIZADA: "Não Organizada",
            cls.CONCLUIDA: "Concluída",
            cls.EXTINTA: "Extinta",
        }
        try:
            return mapeamento[cls(codigo)]
        except ValueError:
            return "Desconhecido"


class SituacaoMatricula(IntEnum):
    """Mapeamento de cd_situacao_aluno / st_matricula do EOL.

    Espelha apps.alunos.enums.SituacaoMatricula — replicado aqui para manter
    independência entre domínios (sem cross-app imports).
    """

    ATIVO = 1
    DESISTENTE = 2
    TRANSFERIDO = 3
    VINCULO_INDEVIDO = 4
    CONCLUIDO = 5
    PENDENTE_REMATRICULA = 6
    FALECIDO = 7
    NAO_COMPARECEU = 8
    REMATRICULADO = 10
    DESLOCAMENTO = 11
    CESSADO = 12
    SEM_CONTINUIDADE = 13
    REMANEJADO_SAIDA = 14
    RECLASSIFICADO_SAIDA = 15
    TRANSFERIDO_SED = 16
    DISPENSADO_ED_FISICA = 17

    @classmethod
    def get_descricao(cls, codigo: int | str | None) -> str:
        """Retorna a descrição amigável para o código."""
        if codigo is None:
            return "Não Informada"

        try:
            cod_int = int(codigo)
        except (ValueError, TypeError):
            return "Desconhecido"

        mapeamento = {
            cls.ATIVO: "Ativo",
            cls.DESISTENTE: "Desistente",
            cls.TRANSFERIDO: "Transferido",
            cls.VINCULO_INDEVIDO: "Vínculo Indevido",
            cls.CONCLUIDO: "Concluído",
            cls.PENDENTE_REMATRICULA: "Pendente de Rematrícula",
            cls.FALECIDO: "Falecido",
            cls.NAO_COMPARECEU: "Não Compareceu",
            cls.REMATRICULADO: "Rematriculado",
            cls.DESLOCAMENTO: "Deslocamento",
            cls.CESSADO: "Cessado",
            cls.SEM_CONTINUIDADE: "Sem continuidade",
            cls.REMANEJADO_SAIDA: "Remanejado Saída",
            cls.RECLASSIFICADO_SAIDA: "Reclassificado Saída",
            cls.TRANSFERIDO_SED: "Transferido SED",
            cls.DISPENSADO_ED_FISICA: "Dispensado Ed. Física",
        }
        try:
            return mapeamento[cls(cod_int)]
        except ValueError:
            return "Desconhecido"
