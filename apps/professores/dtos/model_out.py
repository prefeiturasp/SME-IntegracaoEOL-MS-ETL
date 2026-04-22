"""DTOs de saída para o domínio Professores.

Cada dataclass representa a estrutura já transformada, validada e
nomeada exatamente como os campos do Django model correspondente.

Responsabilidades:
    - Tipagem explícita dos campos de saída (mais rigorosa que model_in).
    - Encapsulamento da lógica de serialização para persistência via
      ``to_dict()``, que retorna o dict esperado por ``_upsert_incremental``
      e ``bulk_create``.

Notas de tipagem:
    - Campos de data usam ``Any`` pois o driver pyodbc pode retornar
      ``datetime.date``, ``datetime.datetime`` ou ``None`` dependendo do
      tipo da coluna no SQL Server. O Django ORM aceita todos esses tipos
      nos campos DateField/DateTimeField.
    - Campos de texto e inteiros têm tipagem explícita (str, int, None).
"""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class UnidadeEducacionalOut:
    """Estrutura de saída para o model ``UnidadeEducacional``."""

    codigo_ue: str
    codigo_dre: str | None
    codigo_tipo_escola: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "codigo_ue": self.codigo_ue,
            "codigo_dre": self.codigo_dre,
            "codigo_tipo_escola": self.codigo_tipo_escola,
        }


@dataclass(slots=True)
class TurmaEscolaOut:
    """Estrutura de saída para o model ``TurmaEscola``."""

    codigo_turma: int
    codigo_escola: str
    ano_letivo: int | None
    status: str
    tipo_turma: int | None
    dt_inicio_turma: Any
    dt_fim_turma: Any
    dt_fim: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "codigo_turma": self.codigo_turma,
            "codigo_escola": self.codigo_escola,
            "ano_letivo": self.ano_letivo,
            "status": self.status,
            "tipo_turma": self.tipo_turma,
            "dt_inicio_turma": self.dt_inicio_turma,
            "dt_fim_turma": self.dt_fim_turma,
            "dt_fim": self.dt_fim,
        }


@dataclass(slots=True)
class SerieTurmaGradeOut:
    """Estrutura de saída para o model ``SerieTurmaGrade``."""

    codigo_serie_grade: int
    codigo_turma: int
    codigo_escola: str
    codigo_escola_grade: int | None
    dt_fim: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "codigo_serie_grade": self.codigo_serie_grade,
            "codigo_turma": self.codigo_turma,
            "codigo_escola": self.codigo_escola,
            "codigo_escola_grade": self.codigo_escola_grade,
            "dt_fim": self.dt_fim,
        }


@dataclass(slots=True)
class TurmaEscolaGradeProgramaOut:
    """Estrutura de saída para o model ``TurmaEscolaGradePrograma``."""

    codigo: int
    codigo_turma: int
    codigo_escola_grade: int | None
    dt_fim: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "codigo_turma": self.codigo_turma,
            "codigo_escola_grade": self.codigo_escola_grade,
            "dt_fim": self.dt_fim,
        }


@dataclass(slots=True)
class TurmaGradeTerritorioExperienciaOut:
    """Estrutura de saída para o model ``TurmaGradeTerritorioExperiencia``."""

    codigo_serie_grade: int
    codigo_componente_curricular: int | None
    codigo_territorio_saber: int | None
    codigo_experiencia_pedagogica: int | None
    dt_inicio: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "codigo_serie_grade": self.codigo_serie_grade,
            "codigo_componente_curricular": self.codigo_componente_curricular,
            "codigo_territorio_saber": self.codigo_territorio_saber,
            "codigo_experiencia_pedagogica": (
                self.codigo_experiencia_pedagogica
            ),
            "dt_inicio": self.dt_inicio,
        }


@dataclass(slots=True)
class ProfessorOut:
    """Estrutura de saída para o model ``Professor``."""

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
    """Estrutura de saída para o model ``CargoBaseServidor``."""

    id: int
    professor_id: str
    codigo_cargo: int
    situacao_funcional: int | None
    dt_posse: Any
    dt_fim_nomeacao: Any
    dt_cancelamento: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "professor_id": self.professor_id,
            "codigo_cargo": self.codigo_cargo,
            "situacao_funcional": self.situacao_funcional,
            "dt_posse": self.dt_posse,
            "dt_fim_nomeacao": self.dt_fim_nomeacao,
            "dt_cancelamento": self.dt_cancelamento,
        }


@dataclass(slots=True)
class LotacaoServidorOut:
    """Estrutura de saída para o model ``LotacaoServidor``."""

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
    """Estrutura de saída para o model ``CargoSobrepostoServidor``."""

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
    """Estrutura de saída para o model ``FuncaoAtividadeCargoServidor``."""

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
    """Estrutura de saída para o model ``LaudoMedico``."""

    cargo_base_id: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "cargo_base_id": self.cargo_base_id,
        }


@dataclass(slots=True)
class PessoaOut:
    """Estrutura de saída para o model ``Pessoa``."""

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
    """Estrutura de saída para o model ``ContratoExterno``."""

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
    """Estrutura de saída para o model ``AtribuicaoAula``.

    ``codigo_turma_escola`` é sempre ``None`` no SQL atual (fixado como
    ``NULL AS cd_turma_escola``), mas é mantido para fidelidade ao schema.
    """

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
    """Estrutura de saída para o model ``AtribuicaoExterno``."""

    id: int
    contrato_externo_id: int
    codigo_unidade_educacao: str
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
