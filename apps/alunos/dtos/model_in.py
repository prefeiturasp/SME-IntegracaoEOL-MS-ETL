"""DTOs de entrada para o domínio Alunos."""

from dataclasses import dataclass
from datetime import date

from apps.core.libs.helpers import parse_date, strip_str


@dataclass(slots=True)
class TipoNecessidadeEspecialIn:
    """Dados brutos da tabela `tipo_necessidade_especial`."""

    codigo_necessidade_especial: int
    descricao: str
    codigo_estado: int | None
    dt_cancelamento: date | None

    def to_domain(self) -> dict:
        return {
            "codigo_necessidade_especial": self.codigo_necessidade_especial,
            "descricao": strip_str(self.descricao),
            "codigo_estado": self.codigo_estado,
            "data_cancelamento": parse_date(self.dt_cancelamento),
            "ativo": self.dt_cancelamento is None,
        }


@dataclass(slots=True)
class AlunoIn:
    """Dados brutos da view `v_aluno_cotic`."""

    codigo_aluno: int
    nome: str
    nome_social: str | None
    data_nascimento: date | None
    sexo: int | None
    nacionalidade: str | None
    nis: str | None
    cpf: str | None
    raca_cor: str | None

    def to_domain(self) -> dict:
        return {
            "codigo_aluno": self.codigo_aluno,
            "nome": strip_str(self.nome) or "NÃO INFORMADO",
            "nome_social": strip_str(self.nome_social),
            "data_nascimento": parse_date(self.data_nascimento),
            "sexo": self.sexo or "U",
            "nacionalidade": strip_str(self.nacionalidade) or "0",
            "nis": strip_str(self.nis),
            "cpf": strip_str(self.cpf),
            "raca_cor": strip_str(self.raca_cor) or "NÃO INFORMADA",
        }


@dataclass(slots=True)
class ResponsavelAlunoIn:
    """Dados brutos da tabela `responsavel_aluno`."""

    codigo_responsavel: int
    codigo_aluno: int
    tipo_responsavel: int | None
    nome: str
    cpf: str | None
    email: str | None
    ddd_celular: str | None
    numero_celular: str | None
    autoriza_sms: int | None
    logradouro: str | None
    cep: int | None
    data_fim_vinculo_aluno: date | None

    def to_domain(self) -> dict:
        return {
            "codigo_responsavel": self.codigo_responsavel,
            "aluno_id": self.codigo_aluno,
            "tipo_responsavel": self.tipo_responsavel,
            "nome": strip_str(self.nome),
            "cpf": strip_str(self.cpf),
            "email": strip_str(self.email),
            "ddd_celular": strip_str(self.ddd_celular),
            "numero_celular": strip_str(self.numero_celular),
            "autoriza_sms": self.autoriza_sms,
            "logradouro": strip_str(self.logradouro),
            "cep": self.cep,
            "data_fim_vinculo": parse_date(self.data_fim_vinculo_aluno),
        }


@dataclass(slots=True)
class NecessidadeEspecialAlunoIn:
    """Dados brutos da tabela `necessidade_especial_aluno`."""

    codigo_necessidade_especial_aluno: int
    codigo_aluno: int
    codigo_necessidade_especial: int
    dt_inicio: date | None
    dt_fim: date | None

    def to_domain(self) -> dict:
        return {
            "codigo_necessidade_especial_aluno": (
                self.codigo_necessidade_especial_aluno
            ),
            "aluno_id": self.codigo_aluno,
            "necessidade_especial_id": self.codigo_necessidade_especial,
            "data_inicio": parse_date(self.dt_inicio),
            "data_fim": parse_date(self.dt_fim),
        }


@dataclass(slots=True)
class MatriculaIn:
    """Dados brutos da view `v_matricula_cotic`."""

    codigo_matricula: int
    codigo_aluno: int
    codigo_ue: str
    data_status: date | None
    ano_letivo: int
    codigo_situacao_matricula: int

    def to_domain(self) -> dict:
        from apps.alunos.enums import SituacaoMatricula

        return {
            "codigo_matricula": self.codigo_matricula,
            "aluno_id": self.codigo_aluno,
            "codigo_ue": strip_str(self.codigo_ue),
            "data_status": parse_date(self.data_status),
            "ano_letivo": self.ano_letivo,
            "codigo_situacao_matricula": self.codigo_situacao_matricula,
            "situacao_matricula": SituacaoMatricula.get_descricao(
                self.codigo_situacao_matricula
            ),
        }


@dataclass(slots=True)
class MatriculaTurmaIn:
    """Dados brutos da tabela `matricula_turma_escola`."""

    codigo_matricula: int | None
    codigo_turma: int
    numero_chamada: str | None
    data_situacao: date | None

    def to_domain(self) -> dict:
        return {
            "codigo_matricula": self.codigo_matricula,
            "codigo_turma": self.codigo_turma,
            "numero_chamada": strip_str(self.numero_chamada),
            "data_situacao_aluno": parse_date(self.data_situacao),
        }
