"""DTOs de entrada para o domínio Institucional mapeados a partir do EOL."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from apps.core.libs.helpers import strip_str

_SP = ZoneInfo("America/Sao_Paulo")


def _make_aware(dt: datetime | None) -> datetime | None:
    """Aplica America/Sao_Paulo em datetimes naive vindos do SQL Server."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=_SP)


@dataclass(slots=True)
class TipoEscolaIn:
    """Dados brutos da tabela `tipo_escola`."""

    codigo_tipo_escola: int
    sigla: str | None
    descricao: str
    data_atualizacao: datetime | None = None

    def to_domain(self) -> dict:
        return {
            "codigo_tipo_escola": int(self.codigo_tipo_escola),
            "sigla": strip_str(self.sigla),
            "descricao": strip_str(self.descricao),
            "data_atualizacao": _make_aware(self.data_atualizacao),
        }


@dataclass(slots=True)
class SubprefeituraIn:
    """Dados brutos da tabela `sub_prefeitura`."""

    codigo_sub_prefeitura: int
    sigla: str | None
    nome: str

    def to_domain(self) -> dict:
        return {
            "codigo_sub_prefeitura": int(self.codigo_sub_prefeitura),
            "sigla": strip_str(self.sigla),
            "nome": strip_str(self.nome),
        }


@dataclass(slots=True)
class DREIn:
    """Dados brutos da query de unidade_administrativa (DRE)."""

    codigo_dre: str
    nome: str
    sigla: str | None
    tipo_unidade_adm: int | None
    descricao_unidade_adm: str | None

    def to_domain(self) -> dict:
        return {
            "codigo_dre": str(self.codigo_dre),
            "nome": strip_str(self.nome),
            "sigla": strip_str(self.sigla),
            "tipo_unidade_adm": (
                int(self.tipo_unidade_adm)
                if self.tipo_unidade_adm is not None
                else None
            ),
            "descricao_unidade_adm": strip_str(self.descricao_unidade_adm),
        }


@dataclass(slots=True)
class UnidadeEducacionalIn:
    """Dados de Unidade Educacional.

    A ordem dos campos deve espelhar exatamente a ordem das colunas no
    SQL_UNIDADE_EDUCACIONAL em services.py, pois o ETL instancia via
    UnidadeEducacionalIn(*row) (posicional).
    """

    codigo_ue: str
    nome: str
    nome_nao_oficial: str | None
    tipo_ue: str | None
    codigo_tipo_unidade_educacao: int | None
    tipo_logradouro: str | None
    codigo_logradouro: int | None
    logradouro: str | None
    numero: str | None
    bairro: str | None
    cep: str | None
    municipio: str | None
    distrito: str | None
    email: str | None
    telefone_1: str | None
    telefone_2: str | None
    ano_construcao: int | None
    propriedade: str | None
    organizacao_parceira: bool | int
    eh_ceu: bool | int
    data_atualizacao: datetime | None
    vagas_matutino: int | None
    vagas_vespertino: int | None
    vagas_noturno: int | None
    vagas_intermediario: int | None
    vagas_integral: int | None
    vagas_total: int | None
    quantidade_funcionarios: int | None
    codigo_inep: int | None
    status: str | None
    codigo_dre: str | None
    codigo_tipo_escola: int | None
    codigo_tp_equipamento: int | None
    codigo_sub_prefeitura: int | None
    codigo_ue_integracao: str | None = None

    def to_domain(self) -> dict:
        def _int(val: Any, default: int | None = None) -> int | None:
            return int(val) if val is not None else default

        return {
            "codigo_ue": str(self.codigo_ue),
            "nome": strip_str(self.nome),
            "nome_nao_oficial": strip_str(self.nome_nao_oficial),
            "tipo_ue": strip_str(self.tipo_ue),
            "tipo_logradouro": strip_str(self.tipo_logradouro),
            "codigo_logradouro": _int(self.codigo_logradouro),
            "logradouro": strip_str(self.logradouro),
            "numero": strip_str(self.numero),
            "bairro": strip_str(self.bairro),
            "cep": strip_str(self.cep),
            "municipio": strip_str(self.municipio),
            "distrito": strip_str(self.distrito),
            "email": strip_str(self.email),
            "telefone_1": strip_str(self.telefone_1),
            "telefone_2": strip_str(self.telefone_2),
            "ano_construcao": _int(self.ano_construcao, 0),
            "propriedade": strip_str(self.propriedade),
            "organizacao_parceira": bool(self.organizacao_parceira),
            "eh_ceu": bool(self.eh_ceu),
            "data_atualizacao": _make_aware(self.data_atualizacao),
            "vagas_matutino": _int(self.vagas_matutino, 0),
            "vagas_vespertino": _int(self.vagas_vespertino, 0),
            "vagas_noturno": _int(self.vagas_noturno, 0),
            "vagas_intermediario": _int(self.vagas_intermediario, 0),
            "vagas_integral": _int(self.vagas_integral, 0),
            "vagas_total": _int(self.vagas_total, 0),
            "quantidade_funcionarios": _int(self.quantidade_funcionarios, 0),
            "codigo_inep": _int(self.codigo_inep),
            "status": strip_str(self.status),
            "dre_id": str(self.codigo_dre) if self.codigo_dre else None,
            "tipo_escola_id": _int(self.codigo_tipo_escola) or None,
            "codigo_tp_equipamento": _int(self.codigo_tp_equipamento),
            "codigo_tipo_unidade_educacao": _int(
                self.codigo_tipo_unidade_educacao
            ),
            "subprefeitura_id": _int(self.codigo_sub_prefeitura) or None,
            "codigo_ue_integracao": self.codigo_ue_integracao,
        }
