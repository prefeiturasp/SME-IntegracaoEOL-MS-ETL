from dataclasses import dataclass
from typing import Optional
from datetime import date

@dataclass(slots=True)
class TipoNecessidadeEspecialIn:
    codigo_necessidade_especial: int
    descricao: str
    codigo_estado: Optional[int]
    dt_cancelamento: Optional[date]

@dataclass(slots=True)
class AlunoIn:
    codigo_aluno: int
    nome: str
    nome_social: Optional[str]
    data_nascimento: Optional[date]
    sexo: Optional[int]
    nacionalidade: Optional[str]
    nis: Optional[str]
    cpf: Optional[str]
    raca_cor: Optional[str]

@dataclass(slots=True)
class ResponsavelAlunoIn:
    codigo_responsavel: int
    codigo_aluno: int
    tipo_responsavel: Optional[int]
    nome: str
    cpf: Optional[str]
    email: Optional[str]
    ddd_celular: Optional[str]
    numero_celular: Optional[str]
    autoriza_sms: Optional[int]
    logradouro: Optional[str]
    cep: Optional[int]
    data_fim_vinculo_aluno: Optional[date]

@dataclass(slots=True)
class NecessidadeEspecialAlunoIn:
    codigo_necessidade_especial_aluno: int
    codigo_aluno: int
    codigo_necessidade_especial: int
    dt_inicio: Optional[date]
    dt_fim: Optional[date]

@dataclass(slots=True)
class MatriculaIn:
    codigo_matricula: int
    codigo_aluno: int
    codigo_ue: str
    data_status: Optional[date]
    ano_letivo: int
    codigo_situacao_matricula: int
    situacao_matricula: str

@dataclass(slots=True)
class MatriculaTurmaIn:
    codigo_matricula: int
    codigo_turma: int
    numero_chamada: Optional[str]
    data_situacao: Optional[date]
