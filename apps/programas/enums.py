"""Enums e mapeamentos do domínio Programas."""

from enum import IntEnum, StrEnum

from django.db import models


class CategoriaPrograma(models.TextChoices):
    """Categoria de programa — PAP ou PAEE."""

    PAP = "PAP", "PAP"
    PAEE = "PAEE", "PAEE"


class TipoProgramaEOL(IntEnum):
    """Subset histórico de tipos de programas do EOL (uso retrocompatível)."""

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
        """
        textos = " ".join(t.upper() for t in (sigla, descricao) if t)
        if "PAEE" in textos or "SRM" in textos:
            return CategoriaPrograma.PAEE
        return CategoriaPrograma.PAP

    @classmethod
    def codigos(cls) -> tuple[int, ...]:
        """Retorna os códigos canônicos históricos."""
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
        """Retorna todos os códigos do enum como tupla."""
        return tuple(m.value for m in cls)

    @classmethod
    def codigos_pap_vigentes(cls) -> tuple[int, ...]:
        """Retorna os códigos vigentes da categoria PAP (sem PAEE, sem legado)."""
        return tuple(
            m.value
            for m in cls
            if m.value in _COMPONENTES_VIGENTES
            and m.value not in _COMPONENTES_PAEE
        )


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
    """Mapeamento da situação do aluno / situação da matrícula do EOL."""

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
