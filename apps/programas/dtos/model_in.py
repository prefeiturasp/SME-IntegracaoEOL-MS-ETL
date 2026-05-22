"""DTOs de entrada do domínio Programas."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from apps.programas.enums import (
    CategoriaPrograma,
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
        return {
            "codigo_tipo_programa": int(self.codigo_tipo_programa),
            "nome": _strip(self.descricao) or _strip(self.sigla),
            "categoria": TipoProgramaEOL.categoria_por_sigla(
                _strip(self.sigla), _strip(self.descricao)
            ),
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
    """Linha bruta da query de turma de programa do EOL."""

    codigo_turma: Any
    nome_turma: Any
    codigo_ue: Any
    codigo_dre: Any
    ano_letivo: Any
    tipo_turno: Any
    descricao_turno: Any
    situacao: Any
    codigo_tipo_programa: Any
    categoria: Any
    descricao_grade: Any = None

    def to_domain(self) -> dict:
        descricao_grade = _strip(self.descricao_grade)
        return {
            "codigo_turma": int(self.codigo_turma),
            "nome_turma": _strip(self.nome_turma),
            "codigo_ue": str(self.codigo_ue),
            "codigo_dre": str(self.codigo_dre),
            "ano_letivo": int(self.ano_letivo),
            "tipo_turno": _int_opt(self.tipo_turno),
            "descricao_turno": _strip(self.descricao_turno),
            "situacao": _strip(self.situacao),
            "codigo_tipo_programa": _int_opt(self.codigo_tipo_programa),
            "categoria": CategoriaPrograma(_strip(self.categoria)),
            "descricao_grade": descricao_grade or None,
        }


@dataclass(slots=True)
class TurmaProgramaComponenteCurricularIn:
    """Linha bruta da query de componentes curriculares por turma."""

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
class AlunoPapAnoLetivoIn:
    """Linha bruta da query pré-agregada de alunos PAP por ano letivo."""

    codigo_aluno: Any
    codigo_turma: Any
    codigo_componente_curricular: Any
    ano_letivo: Any
    codigo_ue: Any
    codigo_dre: Any

    def to_domain(self) -> dict:
        return {
            "codigo_aluno": int(self.codigo_aluno),
            "codigo_turma": int(self.codigo_turma),
            "codigo_componente_curricular": int(
                self.codigo_componente_curricular
            ),
            "ano_letivo": int(self.ano_letivo),
            "codigo_ue": str(self.codigo_ue),
            "codigo_dre": str(self.codigo_dre),
        }


@dataclass(slots=True)
class MatriculaTurmaProgramaIn:
    """Linha bruta da query de matrículas em turmas de programa do EOL."""

    codigo_aluno: Any
    codigo_turma: Any
    codigo_componente_curricular: Any
    nome_componente_curricular: Any
    codigo_situacao_matricula: Any
    data_matricula: datetime | None
    data_situacao: date | None
    ano_letivo: Any
    codigo_ue: Any
    codigo_dre: Any

    def to_domain(self) -> dict:
        codigo_componente = int(self.codigo_componente_curricular)
        return {
            "codigo_aluno": int(self.codigo_aluno),
            "codigo_turma": int(self.codigo_turma),
            "codigo_componente_curricular": codigo_componente,
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
            "categoria": ComponenteCurricularEOL.categoria(codigo_componente),
        }
