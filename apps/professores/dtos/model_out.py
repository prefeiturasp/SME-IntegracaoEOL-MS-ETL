"""DTOs para o domínio Professores."""

import datetime
from dataclasses import dataclass
from typing import Any

from apps.core.libs.helpers import make_aware

_DATA_CHAVE_PADRAO = datetime.datetime(1900, 1, 1)


@dataclass(slots=True)
class ProfessorOut:
    """Estrutura para o model ``Professor``."""

    codigo_rf: str
    nome: str
    nome_social: str | None
    cpf: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "codigo_rf": self.codigo_rf,
            "nome": self.nome,
            "nome_social": self.nome_social,
            "cpf": self.cpf,
        }


@dataclass(slots=True)
class CargoBaseServidorOut:
    """Estrutura para o model ``CargoBaseServidor``."""

    id: int
    professor_id: str
    codigo_cargo: int
    descricao_cargo: str | None
    situacao_funcional: int | None
    dt_posse: Any
    dt_fim_nomeacao: Any
    dt_cancelamento: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "professor_id": self.professor_id,
            "codigo_cargo": self.codigo_cargo,
            "descricao_cargo": self.descricao_cargo,
            "situacao_funcional": self.situacao_funcional,
            "dt_posse": self.dt_posse,
            "dt_fim_nomeacao": self.dt_fim_nomeacao,
            "dt_cancelamento": self.dt_cancelamento,
        }


@dataclass(slots=True)
class LotacaoServidorOut:
    """Estrutura para o model ``LotacaoServidor``."""

    cargo_base_id: int
    codigo_unidade_educacao: str
    dt_inicio: Any
    dt_fim: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "cargo_base_id": self.cargo_base_id,
            "codigo_unidade_educacao": self.codigo_unidade_educacao,
            "dt_inicio": self.dt_inicio,
            "dt_fim": self.dt_fim,
        }


@dataclass(slots=True)
class CargoSobrepostoServidorOut:
    """Estrutura para o model ``CargoSobrepostoServidor``."""

    cargo_base_id: int
    codigo_cargo: int
    codigo_unidade_local_servico: str
    dt_fim_cargo_sobreposto: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "cargo_base_id": self.cargo_base_id,
            "codigo_cargo": self.codigo_cargo,
            "codigo_unidade_local_servico": self.codigo_unidade_local_servico,
            "dt_fim_cargo_sobreposto": self.dt_fim_cargo_sobreposto,
        }


@dataclass(slots=True)
class FuncaoAtividadeCargoServidorOut:
    """Estrutura para o model ``FuncaoAtividadeCargoServidor``."""

    cargo_base_id: int
    codigo_unidade_local_servico: str
    dt_fim_funcao_atividade: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "cargo_base_id": self.cargo_base_id,
            "codigo_unidade_local_servico": self.codigo_unidade_local_servico,
            "dt_fim_funcao_atividade": self.dt_fim_funcao_atividade,
        }


@dataclass(slots=True)
class LaudoMedicoOut:
    """Estrutura para o model ``LaudoMedico``."""

    cargo_base_id: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "cargo_base_id": self.cargo_base_id,
        }


@dataclass(slots=True)
class PessoaOut:
    """Estrutura para o model ``Pessoa``."""

    codigo_pessoa: int
    cpf: str
    nome: str
    nome_social: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "codigo_pessoa": self.codigo_pessoa,
            "cpf": self.cpf,
            "nome": self.nome,
            "nome_social": self.nome_social,
        }


@dataclass(slots=True)
class ContratoExternoOut:
    """Estrutura para o model ``ContratoExterno``."""

    codigo_contrato: int
    pessoa_id: int
    codigo_tipo_funcao: int | None
    codigo_unidade_educacao: str
    dt_cancelamento: Any
    codigo_motivo_desligamento: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "codigo_contrato": self.codigo_contrato,
            "pessoa_id": self.pessoa_id,
            "codigo_tipo_funcao": self.codigo_tipo_funcao,
            "codigo_unidade_educacao": self.codigo_unidade_educacao,
            "dt_cancelamento": self.dt_cancelamento,
            "codigo_motivo_desligamento": self.codigo_motivo_desligamento,
        }


@dataclass(slots=True)
class AtribuicaoAulaOut:
    """Estrutura para o model ``AtribuicaoAula``."""

    id: int
    cargo_base_id: int
    codigo_unidade_educacao: str
    codigo_turma_escola: int | None
    codigo_turma_escola_grade_programa: int | None
    codigo_grade: int | None
    codigo_componente_curricular: int | None
    codigo_serie_grade: int | None
    ano_atribuicao: int | None
    dt_atribuicao_aula: Any
    dt_disponibilizacao_aulas: Any
    codigo_motivo_disponibilizacao: int | None
    dt_cancelamento: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "cargo_base_id": self.cargo_base_id,
            "codigo_unidade_educacao": self.codigo_unidade_educacao,
            "codigo_turma_escola": self.codigo_turma_escola,
            "codigo_turma_escola_grade_programa": (
                self.codigo_turma_escola_grade_programa
            ),
            "codigo_grade": self.codigo_grade,
            "codigo_componente_curricular": self.codigo_componente_curricular,
            "codigo_serie_grade": self.codigo_serie_grade,
            "ano_atribuicao": self.ano_atribuicao,
            "dt_atribuicao_aula": self.dt_atribuicao_aula,
            "dt_disponibilizacao_aulas": self.dt_disponibilizacao_aulas,
            "codigo_motivo_disponibilizacao": (
                self.codigo_motivo_disponibilizacao
            ),
            "dt_cancelamento": self.dt_cancelamento,
        }


@dataclass(slots=True)
class AtribuicaoExternoOut:
    """Estrutura para o model ``AtribuicaoExterno``."""

    id: int
    contrato_externo_id: int
    codigo_unidade_educacao: str
    codigo_turma_escola: int | None
    codigo_grade: int | None
    codigo_componente_curricular: int | None
    codigo_serie_grade: int | None
    codigo_turma_escola_grade_programa: int | None
    ano_atribuicao: int | None
    dt_atribuicao: Any
    dt_disponibilizacao: Any
    codigo_motivo_disponibilizacao_externo: int | None
    dt_cancelamento: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "contrato_externo_id": self.contrato_externo_id,
            "codigo_unidade_educacao": self.codigo_unidade_educacao,
            "codigo_turma_escola": self.codigo_turma_escola,
            "codigo_grade": self.codigo_grade,
            "codigo_componente_curricular": self.codigo_componente_curricular,
            "codigo_serie_grade": self.codigo_serie_grade,
            "codigo_turma_escola_grade_programa": (
                self.codigo_turma_escola_grade_programa
            ),
            "ano_atribuicao": self.ano_atribuicao,
            "dt_atribuicao": self.dt_atribuicao,
            "dt_disponibilizacao": self.dt_disponibilizacao,
            "codigo_motivo_disponibilizacao_externo": (
                self.codigo_motivo_disponibilizacao_externo
            ),
            "dt_cancelamento": self.dt_cancelamento,
        }


def _normalizar_texto(valor: Any, default: str = "") -> str:
    """Normaliza texto de entrada para DTO de saida.

    Args:
        valor: Valor recebido da origem.
        default: Valor usado quando a origem vier nula.
    Returns:
        Texto normalizado.
    """
    if valor is None:
        return default
    return str(valor).strip()


def _normalizar_texto_opcional(valor: Any) -> str | None:
    """Normaliza texto opcional para DTO de saida.

    Args:
        valor: Valor recebido da origem.
    Returns:
        Texto normalizado ou `None`.
    """
    texto = _normalizar_texto(valor)
    return texto or None


def _normalizar_int(valor: Any) -> int:
    """Converta nulo e vazio para zero.

    Args:
        valor: Valor recebido da origem.
    Returns:
        Valor inteiro normalizado.
    """
    if valor in (None, ""):
        return 0
    return int(valor)


def _normalizar_int_opcional(valor: Any) -> int | None:
    """Converta nulo e vazio para None.

    Args:
        valor: Valor recebido da origem.
    Returns:
        Valor inteiro normalizado ou `None`.
    """
    if valor in (None, ""):
        return None
    return int(valor)


def _normalizar_bool(valor: Any) -> bool:
    """Converta indicadores SQL para booleano.

    Args:
        valor: Valor recebido da origem.
    Returns:
        Indicador convertido para booleano.
    """
    if isinstance(valor, str):
        return valor.strip().lower() in {"1", "true", "t", "s", "sim"}
    return bool(valor)


def _normalizar_datetime(valor: Any) -> Any:
    """Converta datetime naive para aware.

    Args:
        valor: Valor de data/hora recebido da origem.
    Returns:
        Data/hora pronta para persistencia no Django.
    """
    if valor is None or not hasattr(valor, "tzinfo"):
        return valor
    return make_aware(valor)


def _normalizar_data_chave_funcionario(valor: Any) -> Any:
    """Normaliza data usada na chave natural."""
    return _normalizar_datetime(valor or _DATA_CHAVE_PADRAO)


@dataclass(slots=True)
class FuncionarioUnidadeEducacionalOut:
    """Estrutura para o model ``FuncionarioUnidadeEducacional``."""

    nome: str
    nome_social: str | None
    cpf: str | None
    codigo_rf: str
    codigo_ue: str
    data_inicio: Any
    data_fim: Any
    codigo_cargo: int | None
    cargo: str | None
    codigo_tipo_funcao_atividade: int | None
    eh_professor: Any
    esta_afastado: Any
    funcao_externo: int | None
    tipo_funcao_externo: int | None

    def __post_init__(self) -> None:
        """Normaliza campos do contrato de funcionario."""
        self.nome = _normalizar_texto(self.nome)
        self.nome_social = _normalizar_texto_opcional(self.nome_social)
        self.cpf = _normalizar_texto_opcional(self.cpf)
        self.codigo_rf = _normalizar_texto(self.codigo_rf)
        self.codigo_ue = _normalizar_texto(self.codigo_ue)
        self.data_inicio = _normalizar_data_chave_funcionario(
            self.data_inicio
        )
        self.data_fim = _normalizar_datetime(self.data_fim)
        self.codigo_cargo = _normalizar_int_opcional(self.codigo_cargo)
        self.cargo = _normalizar_texto_opcional(self.cargo)
        self.codigo_tipo_funcao_atividade = _normalizar_int_opcional(
            self.codigo_tipo_funcao_atividade
        )
        self.eh_professor = _normalizar_bool(self.eh_professor)
        self.esta_afastado = _normalizar_bool(self.esta_afastado)
        self.funcao_externo = _normalizar_int_opcional(self.funcao_externo)
        self.tipo_funcao_externo = _normalizar_int_opcional(
            self.tipo_funcao_externo
        )

    def to_dict(self) -> dict[str, Any]:
        """Converta para dicionario de persistencia.

        Returns:
            Campos compatíveis com o model `FuncionarioUnidadeEducacional`.
        """
        return {
            "nome": self.nome,
            "nome_social": self.nome_social,
            "cpf": self.cpf,
            "codigo_rf": self.codigo_rf,
            "codigo_ue": self.codigo_ue,
            "data_inicio": self.data_inicio,
            "data_fim": self.data_fim,
            "codigo_cargo": self.codigo_cargo,
            "cargo": self.cargo,
            "codigo_tipo_funcao_atividade": (
                _normalizar_int(self.codigo_tipo_funcao_atividade)
            ),
            "eh_professor": self.eh_professor,
            "esta_afastado": self.esta_afastado,
            "funcao_externo": _normalizar_int(self.funcao_externo),
            "tipo_funcao_externo": _normalizar_int(
                self.tipo_funcao_externo
            ),
        }
