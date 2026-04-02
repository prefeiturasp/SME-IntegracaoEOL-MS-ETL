"""Dataclasses representando a estrutura bruta retornada pelo banco legado EOL.

Cada campo mapeia diretamente a posição das tuplas retornadas pelo cursor pyodbc
via unpacking: `ModelIn(*row)`.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class TipoEscolaIn:
    """Linha bruta da query de tipo_escola."""

    codigo_tipo_escola: Any
    sigla: Any
    descricao: Any


@dataclass
class SubprefeituraIn:
    """Linha bruta da query de sub_prefeitura."""

    codigo_sub_prefeitura: Any
    sigla: Any
    nome: Any


@dataclass
class DREIn:
    """Linha bruta da query de unidade_administrativa (DRE)."""

    codigo_dre: Any
    nome: Any
    sigla: Any
    tipo_unidade_adm: Any
    descricao_unidade_adm: Any


@dataclass
class UnidadeEducacionalIn:
    """Linha bruta da query de v_unidade_educacao_dados_gerais."""

    codigo_ue: Any
    nome: Any
    nome_nao_oficial: Any
    tipo_ue: Any
    tipo_logradouro: Any
    logradouro: Any
    numero: Any
    bairro: Any
    cep: Any
    municipio: Any
    distrito: Any
    email: Any
    telefone_1: Any
    telefone_2: Any
    ano_construcao: Any
    propriedade: Any
    organizacao_parceira: Any
    vagas_matutino: Any
    vagas_vespertino: Any
    vagas_noturno: Any
    vagas_intermediario: Any
    vagas_integral: Any
    vagas_total: Any
    quantidade_funcionarios: Any
    status: Any
    codigo_dre: Any
    codigo_tipo_escola: Any
    codigo_sub_prefeitura: Any
