"""Dataclasses representando a estrutura bruta retornada pelo banco legado EOL.

Cada campo mapeia diretamente a posição das tuplas retornadas pelo cursor pyodbc
via unpacking: `ModelIn(*row)`.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class TipoProgramaIn:
    """Linha bruta da query de tipo_programa."""

    codigo_tipo_programa: Any
    sigla: Any
    descricao: Any


@dataclass
class ComponenteCurricularProgramaIn:
    """Linha bruta da query de componente_curricular filtrada por IDs conhecidos."""

    codigo_componente_curricular: Any
    nome_componente_curricular: Any


@dataclass
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


@dataclass
class TurmaProgramaComponenteCurricularIn:
    """Linha bruta da query de componentes curriculares por turma de programa."""

    codigo_turma: Any
    codigo_componente_curricular: Any
    nome_componente_curricular: Any


@dataclass
class MatriculaTurmaProgramaIn:
    """Linha bruta da query de matrículas em turmas de programa."""

    codigo_aluno: Any
    codigo_turma: Any
    codigo_componente_curricular: Any
    nome_componente_curricular: Any
    codigo_situacao_matricula: Any
    descricao_situacao_matricula: Any
    data_matricula: Any
    data_situacao: Any
    ano_letivo: Any
    codigo_ue: Any
    codigo_dre: Any
    codigo_tipo_programa: Any
