"""Proxy Models Django para transformação EOL - destino.

Domínio institucional: Centraliza a lógica de conversão e limpeza.
null handling) ao mapear os DTOs de entrada (In) para as instâncias de
persistência (Out).
"""

from typing import Any

from apps.institucional.dtos.model_in import (
    DREIn,
    SubprefeituraIn,
    TipoEscolaIn,
    UnidadeEducacionalIn,
)
from apps.institucional.models import (
    DRE,
    SubPrefeitura,
    TipoEscola,
    UnidadeEducacional,
)


def _strip(val: Any) -> str:
    """Remove espaços em branco de uma string ou retorna vazio."""
    return str(val).strip() if val else ""


def _int(val: Any, default: int | None = None) -> int | None:
    """Valor convertido para inteiro ou default."""
    return int(val) if val is not None else default


class ProxyMeta:
    """Metadados base para Proxy Models do domínio Institucional."""

    proxy = True
    app_label = "institucional"


class TipoEscolaOut(TipoEscola):
    """Proxy para conversão de TipoEscola."""

    class Meta(ProxyMeta):
        """Configurações do proxy."""

        pass

    @classmethod
    def from_in(cls, obj: TipoEscolaIn) -> "TipoEscolaOut":
        """Mapeia DTO de entrada para instância de saída."""
        return cls(
            codigo_tipo_escola=int(obj.codigo_tipo_escola),
            sigla=_strip(obj.sigla) or None,
            descricao=_strip(obj.descricao),
        )


class DREOut(DRE):
    """Proxy para conversão de DRE."""

    class Meta(ProxyMeta):
        """Configurações do proxy."""

        pass

    @classmethod
    def from_in(cls, obj: DREIn) -> "DREOut":
        """Mapeia DTO de entrada para instância de saída."""
        return cls(
            codigo_dre=str(obj.codigo_dre),
            nome=_strip(obj.nome),
            sigla=_strip(obj.sigla) or None,
            tipo_unidade_adm=_int(obj.tipo_unidade_adm),
            descricao_unidade_adm=_strip(obj.descricao_unidade_adm) or None,
        )


class SubprefeituraOut(SubPrefeitura):
    """Proxy para conversão de SubPrefeitura."""

    class Meta(ProxyMeta):
        """Configurações do proxy."""

        pass

    @classmethod
    def from_in(cls, obj: SubprefeituraIn) -> "SubprefeituraOut":
        """Mapeia DTO de entrada para instância de saída."""
        return cls(
            codigo_sub_prefeitura=int(obj.codigo_sub_prefeitura),
            sigla=_strip(obj.sigla) or None,
            nome=_strip(obj.nome),
        )


class UnidadeEducacionalOut(UnidadeEducacional):
    """Proxy para conversão de UnidadeEducacional."""

    class Meta(ProxyMeta):
        """Configurações do proxy."""

        pass

    @classmethod
    def from_in(
        cls,
        obj: UnidadeEducacionalIn,
        codigo_ue_integracao: str | None = None,
    ) -> "UnidadeEducacionalOut":
        """Mapeia DTO de entrada para instância de saída."""
        return cls(
            codigo_ue=str(obj.codigo_ue),
            nome=_strip(obj.nome),
            nome_nao_oficial=_strip(obj.nome_nao_oficial) or None,
            tipo_ue=_strip(obj.tipo_ue) or None,
            tipo_logradouro=_strip(obj.tipo_logradouro) or None,
            logradouro=_strip(obj.logradouro) or None,
            numero=_strip(obj.numero) or None,
            bairro=_strip(obj.bairro) or None,
            cep=_strip(obj.cep) or None,
            municipio=_strip(obj.municipio) or None,
            distrito=_strip(obj.distrito) or None,
            email=_strip(obj.email) or None,
            telefone_1=_strip(obj.telefone_1) or None,
            telefone_2=_strip(obj.telefone_2) or None,
            ano_construcao=_int(obj.ano_construcao),
            propriedade=_strip(obj.propriedade) or None,
            organizacao_parceira=bool(obj.organizacao_parceira),
            vagas_matutino=_int(obj.vagas_matutino, 0),
            vagas_vespertino=_int(obj.vagas_vespertino, 0),
            vagas_noturno=_int(obj.vagas_noturno, 0),
            vagas_intermediario=_int(obj.vagas_intermediario, 0),
            vagas_integral=_int(obj.vagas_integral, 0),
            vagas_total=_int(obj.vagas_total, 0),
            quantidade_funcionarios=_int(obj.quantidade_funcionarios, 0),
            status=_strip(obj.status) or None,
            dre_id=str(obj.codigo_dre) if obj.codigo_dre else None,
            tipo_escola_id=_int(obj.codigo_tipo_escola),
            subprefeitura_id=_int(obj.codigo_sub_prefeitura),
            codigo_ue_integracao=codigo_ue_integracao,
        )
