"""DTOs de entrada para o domínio Institucional mapeados a partir do EOL."""

from typing import Any
from dataclasses import dataclass
from apps.core.libs.helpers import strip_str


@dataclass(slots=True)
class TipoEscolaIn:
    """Dados brutos da tabela `tipo_escola`."""

    codigo_tipo_escola: int
    sigla: str | None
    descricao: str

    def to_domain(self) -> dict:
        """Converte para dicionário de persistência no Model TipoEscola."""
        return {
            "codigo_tipo_escola": int(self.codigo_tipo_escola),
            "sigla": strip_str(self.sigla),
            "descricao": strip_str(self.descricao),
        }


@dataclass(slots=True)
class SubprefeituraIn:
    """Dados brutos da tabela `sub_prefeitura`."""

    codigo_sub_prefeitura: int
    sigla: str | None
    nome: str

    def to_domain(self) -> dict:
        """Converte para dicionário de persistência no Model SubPrefeitura."""
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
        """Converte para dicionário de persistência no Model DRE."""
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
    """Dados de Unidade Educacional."""

    codigo_ue: str
    nome: str
    nome_nao_oficial: str | None
    tipo_ue: str | None
    tipo_logradouro: str | None
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
    codigo_sub_prefeitura: int | None
    codigo_ue_integracao: str | None = None

    def to_domain(self) -> dict:
        """Converte para dicionário de persistência no Model UnidadeEducacional."""

        def _int(val: Any, default: int | None = None) -> int | None:
            return int(val) if val is not None else default

        return {
            "codigo_ue": str(self.codigo_ue),
            "nome": strip_str(self.nome),
            "nome_nao_oficial": strip_str(self.nome_nao_oficial),
            "tipo_ue": strip_str(self.tipo_ue),
            "tipo_logradouro": strip_str(self.tipo_logradouro),
            "logradouro": strip_str(self.logradouro),
            "numero": strip_str(self.numero),
            "bairro": strip_str(self.bairro),
            "cep": strip_str(self.cep),
            "municipio": strip_str(self.municipio),
            "distrito": strip_str(self.distrito),
            "email": strip_str(self.email),
            "telefone_1": strip_str(self.telefone_1),
            "telefone_2": strip_str(self.telefone_2),
            "ano_construcao": _int(self.ano_construcao),
            "propriedade": strip_str(self.propriedade),
            "organizacao_parceira": bool(self.organizacao_parceira),
            "vagas_matutino": _int(self.vagas_matutino, 0),
            "vagas_vespertino": _int(self.vagas_vespertino, 0),
            "vagas_noturno": _int(self.vagas_noturno, 0),
            "vagas_intermediario": _int(self.vagas_intermediario, 0),
            "vagas_integral": _int(self.vagas_integral, 0),
            "vagas_total": _int(self.vagas_total, 0),
            "quantidade_funcionarios": _int(
                self.quantidade_funcionarios, 0
            ),
            "codigo_inep": _int(self.codigo_inep),
            "status": strip_str(self.status),
            "dre_id": str(self.codigo_dre) if self.codigo_dre else None,
            "tipo_escola_id": _int(self.codigo_tipo_escola),
            "subprefeitura_id": _int(self.codigo_sub_prefeitura),
            "codigo_ue_integracao": self.codigo_ue_integracao,
        }
