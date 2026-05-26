"""Enums e mapeamentos do domínio Alunos."""

from enum import IntEnum


class SituacaoMatricula(IntEnum):
    """Mapeamento de st_matricula do EOL."""

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
            return "Fora do domínio liberado pela PRODAM"

        mapeamento: dict[int, str] = {
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
        return mapeamento.get(cod_int, "Fora do domínio liberado pela PRODAM")
