"""Proxy Models Django para transformação EOL → destino.

Domínio programas: Centraliza a lógica de conversão e limpeza ao mapear
os DTOs de entrada (In) para as instâncias de persistência (Out).
"""

from typing import Any

from apps.programas.dtos.model_in import (
    ComponenteCurricularProgramaIn,
    MatriculaTurmaProgramaIn,
    TipoProgramaIn,
    TurmaProgramaComponenteCurricularIn,
    TurmaProgramaIn,
)
from apps.programas.enums import (
    ComponenteCurricularEOL,
    SituacaoMatricula,
    TipoProgramaEOL,
)
from apps.programas.models import (
    ComponenteCurricularPrograma,
    MatriculaTurmaPrograma,
    TipoPrograma,
    TurmaPrograma,
    TurmaProgramaComponenteCurricular,
)


def _strip(val: Any) -> str:
    """Remove espaços em branco ou retorna vazio."""
    return str(val).strip() if val else ""


def _int(val: Any, default: int | None = None) -> int | None:
    """Converte para inteiro ou retorna default."""
    return int(val) if val is not None else default


class ProxyMeta:
    """Metadados base para Proxy Models do domínio Programas."""

    proxy = True
    app_label = "programas"


class TipoProgramaOut(TipoPrograma):
    """Proxy para conversão de TipoPrograma."""

    class Meta(ProxyMeta):
        pass

    @classmethod
    def from_in(cls, obj: TipoProgramaIn) -> "TipoProgramaOut":
        """Mapeia DTO de entrada para instância de saída."""
        codigo = int(obj.codigo_tipo_programa)
        return cls(
            codigo_tipo_programa=codigo,
            nome=_strip(obj.descricao) or _strip(obj.sigla),
            categoria=TipoProgramaEOL.categoria(codigo),
            ativo=True,
        )


class ComponenteCurricularProgramaOut(ComponenteCurricularPrograma):
    """Proxy para conversão de ComponenteCurricularPrograma."""

    class Meta(ProxyMeta):
        pass

    @classmethod
    def from_in(cls, obj: ComponenteCurricularProgramaIn) -> "ComponenteCurricularProgramaOut":
        """Mapeia DTO de entrada para instância de saída."""
        codigo = int(obj.codigo_componente_curricular)
        return cls(
            codigo_componente_curricular=codigo,
            nome_componente_curricular=_strip(obj.nome_componente_curricular),
            categoria=ComponenteCurricularEOL.categoria(codigo),
            vigente=ComponenteCurricularEOL.vigente(codigo),
        )


class TurmaProgramaOut(TurmaPrograma):
    """Proxy para conversão de TurmaPrograma."""

    class Meta(ProxyMeta):
        pass

    @classmethod
    def from_in(cls, obj: TurmaProgramaIn) -> "TurmaProgramaOut":
        """Mapeia DTO de entrada para instância de saída."""
        codigo_tipo = int(obj.codigo_tipo_programa)
        return cls(
            codigo_turma=int(obj.codigo_turma),
            nome_turma=_strip(obj.nome_turma),
            codigo_ue=str(obj.codigo_ue),
            codigo_dre=str(obj.codigo_dre),
            ano_letivo=int(obj.ano_letivo),
            tipo_turno=_int(obj.tipo_turno),
            descricao_turno=_strip(obj.descricao_turno),
            situacao=_strip(obj.situacao),
            codigo_tipo_programa=codigo_tipo,
            categoria=TipoProgramaEOL.categoria(codigo_tipo),
        )


class TurmaProgramaComponenteCurricularOut(TurmaProgramaComponenteCurricular):
    """Proxy para conversão de TurmaProgramaComponenteCurricular."""

    class Meta(ProxyMeta):
        pass

    @classmethod
    def from_in(
        cls, obj: TurmaProgramaComponenteCurricularIn
    ) -> "TurmaProgramaComponenteCurricularOut":
        """Mapeia DTO de entrada para instância de saída."""
        return cls(
            codigo_turma=int(obj.codigo_turma),
            codigo_componente_curricular=int(obj.codigo_componente_curricular),
            nome_componente_curricular=_strip(obj.nome_componente_curricular),
        )


class MatriculaTurmaProgramaOut(MatriculaTurmaPrograma):
    """Proxy para conversão de MatriculaTurmaPrograma."""

    class Meta(ProxyMeta):
        pass

    @classmethod
    def from_in(cls, obj: MatriculaTurmaProgramaIn) -> "MatriculaTurmaProgramaOut":
        """Mapeia DTO de entrada para instância de saída."""
        codigo_tipo = int(obj.codigo_tipo_programa)
        return cls(
            codigo_aluno=int(obj.codigo_aluno),
            codigo_turma=int(obj.codigo_turma),
            codigo_componente_curricular=int(obj.codigo_componente_curricular),
            nome_componente_curricular=_strip(obj.nome_componente_curricular),
            codigo_situacao_matricula=int(obj.codigo_situacao_matricula),
            descricao_situacao_matricula=SituacaoMatricula.get_descricao(
                obj.codigo_situacao_matricula
            ),
            data_matricula=obj.data_matricula,
            data_situacao=obj.data_situacao,
            ano_letivo=int(obj.ano_letivo),
            codigo_ue=str(obj.codigo_ue),
            codigo_dre=str(obj.codigo_dre),
            categoria=TipoProgramaEOL.categoria(codigo_tipo),
        )
