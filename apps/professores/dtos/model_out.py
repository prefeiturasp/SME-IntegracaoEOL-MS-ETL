"""DTOs para o domínio Professores."""

from dataclasses import dataclass
from typing import Any


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
