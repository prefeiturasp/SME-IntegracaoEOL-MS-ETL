"""DTOs de entrada para o domínio Programas.

Cada dataclass mapeia diretamente a posição das tuplas retornadas pelo
cursor pyodbc via unpacking: ``ModelIn(*row)``. O método ``to_domain()``
converte a linha bruta no dicionário de campos do model Django destino,
absorvendo a lógica antes espalhada em ``model_out.py``.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from apps.programas.enums import (
    ComponenteCurricularEOL,
    SituacaoMatricula,
    TipoProgramaEOL,
)


def _strip(val: Any) -> str:
    """Remove espaços em branco ou retorna vazio."""
    return str(val).strip() if val else ""


def _int_opt(val: Any) -> int | None:
    """Converte para inteiro ou None."""
    return int(val) if val is not None else None


@dataclass(slots=True)
class TipoProgramaIn:
    """Linha bruta da query de tipo_programa."""

    codigo_tipo_programa: Any
    sigla: Any
    descricao: Any

    def to_domain(self) -> dict:
        codigo = int(self.codigo_tipo_programa)
        return {
            "codigo_tipo_programa": codigo,
            "nome": _strip(self.descricao) or _strip(self.sigla),
            "categoria": TipoProgramaEOL.categoria(codigo),
            "ativo": True,
        }


@dataclass(slots=True)
class ComponenteCurricularProgramaIn:
    """Linha bruta da query de componente_curricular filtrada por IDs conhecidos."""

    codigo_componente_curricular: Any
    nome_componente_curricular: Any

    def to_domain(self) -> dict:
        codigo = int(self.codigo_componente_curricular)
        return {
            "codigo_componente_curricular": codigo,
            "nome_componente_curricular": _strip(
                self.nome_componente_curricular
            ),
            "categoria": ComponenteCurricularEOL.categoria(codigo),
            "vigente": ComponenteCurricularEOL.vigente(codigo),
        }


@dataclass(slots=True)
class TurmaProgramaIn:
    """Linha bruta da query de turma_escola onde cd_tipo_turma = 3."""

    codigo_turma: Any
    nome_turma: Any
    codigo_ue: Any
    codigo_dre: Any
    ano_letivo: Any
    tipo_turno: Any
    descricao_turno: Any
    situacao: Any
    codigo_tipo_programa: Any

    def to_domain(self) -> dict:
        codigo_tipo = int(self.codigo_tipo_programa)
        return {
            "codigo_turma": int(self.codigo_turma),
            "nome_turma": _strip(self.nome_turma),
            "codigo_ue": str(self.codigo_ue),
            "codigo_dre": str(self.codigo_dre),
            "ano_letivo": int(self.ano_letivo),
            "tipo_turno": _int_opt(self.tipo_turno),
            "descricao_turno": _strip(self.descricao_turno),
            "situacao": _strip(self.situacao),
            "codigo_tipo_programa": codigo_tipo,
            "categoria": TipoProgramaEOL.categoria(codigo_tipo),
        }


@dataclass(slots=True)
class TurmaProgramaComponenteCurricularIn:
    """Linha bruta da query de componentes curriculares por turma de programa."""

    codigo_turma: Any
    codigo_componente_curricular: Any
    nome_componente_curricular: Any

    def to_domain(self) -> dict:
        return {
            "codigo_turma": int(self.codigo_turma),
            "codigo_componente_curricular": int(
                self.codigo_componente_curricular
            ),
            "nome_componente_curricular": _strip(
                self.nome_componente_curricular
            ),
        }


@dataclass(slots=True)
class MatriculaTurmaProgramaIn:
    """Linha bruta da query de matrículas em turmas de programa."""

    codigo_aluno: Any
    codigo_turma: Any
    codigo_componente_curricular: Any
    nome_componente_curricular: Any
    codigo_situacao_matricula: Any
    data_matricula: date | None
    data_situacao: date | None
    ano_letivo: Any
    codigo_ue: Any
    codigo_dre: Any
    codigo_tipo_programa: Any

    def to_domain(self) -> dict:
        codigo_tipo = int(self.codigo_tipo_programa)
        return {
            "codigo_aluno": int(self.codigo_aluno),
            "codigo_turma": int(self.codigo_turma),
            "codigo_componente_curricular": int(
                self.codigo_componente_curricular
            ),
            "nome_componente_curricular": _strip(
                self.nome_componente_curricular
            ),
            "codigo_situacao_matricula": int(self.codigo_situacao_matricula),
            "descricao_situacao_matricula": SituacaoMatricula.get_descricao(
                self.codigo_situacao_matricula
            ),
            "data_matricula": self.data_matricula,
            "data_situacao": self.data_situacao,
            "ano_letivo": int(self.ano_letivo),
            "codigo_ue": str(self.codigo_ue),
            "codigo_dre": str(self.codigo_dre),
            "categoria": TipoProgramaEOL.categoria(codigo_tipo),
        }
