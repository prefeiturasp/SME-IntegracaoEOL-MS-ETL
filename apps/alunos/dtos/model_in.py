"""DTOs de entrada para o domínio Alunos."""

from dataclasses import dataclass
from datetime import date, datetime

from apps.core.libs.helpers import aware_or_none, parse_date, strip_str


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
    nome_mae: str | None
    raca_cor: str | None
    cns: str | None
    data_atualizacao_contato: date | None
    possui_deficiencia: bool

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
            "nome_mae": strip_str(self.nome_mae),
            "raca_cor": strip_str(self.raca_cor) or "NÃO INFORMADA",
            "cns": strip_str(self.cns),
            "data_atualizacao_contato": parse_date(
                self.data_atualizacao_contato
            ),
            "possui_deficiencia": bool(self.possui_deficiencia),
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
    data_nascimento: date | None
    nome_mae: str | None
    ddd_celular: str | None
    numero_celular: str | None
    autoriza_sms: int | None
    endereco_id: int | None
    numero_endereco: str | None
    complemento: str | None
    bairro: str | None
    logradouro: str | None
    cep: int | None
    nome_municipio: str | None
    sigla_uf: str | None
    tipo_logradouro: str | None
    data_atualizacao_tabela: datetime | None
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
            "data_nascimento": parse_date(self.data_nascimento),
            "nome_mae": strip_str(self.nome_mae),
            "endereco_id": self.endereco_id,
            "numero_endereco": strip_str(self.numero_endereco),
            "complemento": strip_str(self.complemento),
            "bairro": strip_str(self.bairro),
            "logradouro": strip_str(self.logradouro),
            "cep": self.cep,
            "nome_municipio": strip_str(self.nome_municipio),
            "sigla_uf": strip_str(self.sigla_uf),
            "tipo_logradouro": strip_str(self.tipo_logradouro),
            "data_atualizacao_tabela": aware_or_none(
                self.data_atualizacao_tabela
            ),
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
    codigo_tipo_recurso: int | None
    descricao_tipo_recurso: str | None

    def to_domain(self) -> dict:
        return {
            "codigo_necessidade_especial_aluno": (
                self.codigo_necessidade_especial_aluno
            ),
            "aluno_id": self.codigo_aluno,
            "necessidade_especial_id": self.codigo_necessidade_especial,
            "data_inicio": parse_date(self.dt_inicio),
            "data_fim": parse_date(self.dt_fim),
            "codigo_tipo_recurso": self.codigo_tipo_recurso,
            "descricao_tipo_recurso": strip_str(self.descricao_tipo_recurso),
        }


@dataclass(slots=True)
class MatriculaIn:
    """Dados brutos da view `v_matricula_cotic`."""

    codigo_matricula: int
    codigo_aluno: int
    codigo_ue: str
    data_situacao_matricula: date | None
    data_situacao_matricula_data_hora: datetime | None
    ano_letivo: int
    codigo_situacao_matricula: int
    origem_atual: bool

    def to_domain(self) -> dict:
        from apps.alunos.enums import SituacaoMatricula

        return {
            "codigo_matricula": self.codigo_matricula,
            "aluno_id": self.codigo_aluno,
            "codigo_ue": strip_str(self.codigo_ue),
            "data_situacao_matricula": parse_date(
                self.data_situacao_matricula
            ),
            "data_situacao_matricula_data_hora": aware_or_none(
                self.data_situacao_matricula_data_hora
            ),
            "ano_letivo": self.ano_letivo,
            "codigo_situacao_matricula": self.codigo_situacao_matricula,
            "situacao_matricula": SituacaoMatricula.get_descricao(
                self.codigo_situacao_matricula
            ),
            "origem_atual": self.origem_atual,
        }


@dataclass(slots=True)
class MatriculaTurmaIn:
    """Dados brutos da tabela `matricula_turma_escola`."""

    codigo_matricula: int | None
    codigo_turma: int
    numero_chamada: str | None
    data_situacao: date | None
    data_situacao_data_hora: datetime | None
    codigo_situacao_aluno: int | None
    codigo_tipo_turma: int | None
    data_atualizacao_tabela: datetime | None

    def to_domain(self) -> dict:
        return {
            "codigo_matricula": self.codigo_matricula,
            "codigo_turma": self.codigo_turma,
            "numero_chamada": strip_str(self.numero_chamada),
            "data_situacao_aluno": parse_date(self.data_situacao),
            "data_situacao_aluno_data_hora": aware_or_none(
                self.data_situacao_data_hora
            ),
            "codigo_situacao_aluno": self.codigo_situacao_aluno,
            "codigo_tipo_turma": self.codigo_tipo_turma,
            "data_atualizacao_tabela": aware_or_none(
                self.data_atualizacao_tabela
            ),
        }


@dataclass(slots=True)
class MatriculaAnoLetivoIn:
    """Dados agregados de matrículas por turma e ano letivo."""

    codigo_dre: str
    codigo_ue: str
    tipo_escola: int
    ano_letivo: int
    codigo_modalidade: int | None
    modalidade: str | None
    ordem: int | None
    ano: str | None
    turma: str | None
    quantidade: int

    def to_domain(self) -> dict:
        return {
            "codigo_dre": strip_str(self.codigo_dre),
            "codigo_ue": strip_str(self.codigo_ue),
            "tipo_escola": self.tipo_escola,
            "ano_letivo": self.ano_letivo,
            "codigo_modalidade": self.codigo_modalidade,
            "modalidade": self.modalidade,
            "ordem": self.ordem,
            "ano": strip_str(self.ano),
            "turma": strip_str(self.turma),
            "quantidade": self.quantidade,
        }


@dataclass(slots=True)
class MatriculaComponenteCurricularAnoLetivoIn:
    """Dados agregados de matrículas por componente e ano letivo."""

    codigo_ue: str
    codigo_dre: str
    ano_letivo: int
    modalidade: str | None
    ordem: int | None
    componente_curricular_id: int
    ano: str | None
    turma: str | None
    quantidade: int

    def to_domain(self) -> dict:
        return {
            "codigo_ue": strip_str(self.codigo_ue),
            "codigo_dre": strip_str(self.codigo_dre),
            "ano_letivo": self.ano_letivo,
            "modalidade": self.modalidade,
            "ordem": self.ordem,
            "componente_curricular_id": self.componente_curricular_id,
            "ano": strip_str(self.ano),
            "turma": strip_str(self.turma),
            "quantidade": self.quantidade,
        }


@dataclass(slots=True)
class DadosAlunoAcompanhamentoEscolarIn:
    """Dados brutos de aluno para acompanhamento escolar."""

    codigo_aluno: int
    nome: str
    nome_social: str | None
    nome_responsavel: str | None
    cpf_responsavel: str | None
    data_nascimento: date | None
    descricao_tipo_escola: str
    tipo_responsavel: int | None
    codigo_dre: str
    sigla_dre: str | None
    codigo_ue: str
    unidade_educacional: str
    codigo_turma: int
    turma: str
    codigo_tipo_escola: int
    situacao_matricula: str
    data_situacao_matricula: date | None
    codigo_etapa_ensino: int | None
    codigo_ciclo_ensino: int | None
    serie_resumida: str | None
    codigo_modalidade_turma: int | None

    def to_domain(self) -> dict:
        _texto_nao_informado = "NÃO INFORMADO"

        return {
            "codigo_aluno": self.codigo_aluno,
            "nome": strip_str(self.nome) or _texto_nao_informado,
            "nome_social": strip_str(self.nome_social),
            "nome_responsavel": strip_str(self.nome_responsavel),
            "cpf_responsavel": strip_str(self.cpf_responsavel),
            "data_nascimento": parse_date(self.data_nascimento),
            "descricao_tipo_escola": (
                strip_str(self.descricao_tipo_escola)
                or _texto_nao_informado
            ),
            "tipo_responsavel": self.tipo_responsavel,
            "codigo_dre": strip_str(self.codigo_dre),
            "sigla_dre": strip_str(self.sigla_dre),
            "codigo_ue": strip_str(self.codigo_ue),
            "unidade_educacional": (
                strip_str(self.unidade_educacional) or _texto_nao_informado
            ),
            "codigo_turma": self.codigo_turma,
            "turma": strip_str(self.turma) or _texto_nao_informado,
            "codigo_tipo_escola": self.codigo_tipo_escola,
            "situacao_matricula": (
                strip_str(self.situacao_matricula) or _texto_nao_informado
            ),
            "data_situacao_matricula": parse_date(
                self.data_situacao_matricula
            ),
            "codigo_etapa_ensino": self.codigo_etapa_ensino,
            "codigo_ciclo_ensino": self.codigo_ciclo_ensino,
            "serie_resumida": strip_str(self.serie_resumida),
            "codigo_modalidade_turma": self.codigo_modalidade_turma,
        }
