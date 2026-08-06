"""DTOs para o domínio Professores."""

import datetime
from dataclasses import dataclass
from typing import Any
from uuid import UUID

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
        """Retorna dados do professor.

        Returns:
            Dados prontos para persistência.
        """
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
        """Retorna dados do cargo base.

        Returns:
            Dados prontos para persistência.
        """
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
class FuncionarioCargoOut:
    """Estrutura para o model ``FuncionarioCargo``."""

    nome: str
    codigo_rf: str
    data_inicio: Any
    data_fim: Any
    cargo: str
    codigo_cargo: int

    def __post_init__(self) -> None:
        """Normaliza campos do funcionário por cargo."""
        self.nome = _normalizar_texto(self.nome)
        self.codigo_rf = _normalizar_texto(self.codigo_rf)
        self.data_inicio = _normalizar_datetime(self.data_inicio)
        self.data_fim = _normalizar_datetime(self.data_fim)
        self.cargo = _normalizar_texto(self.cargo)
        self.codigo_cargo = _normalizar_int(self.codigo_cargo)

    def to_dict(self) -> dict[str, Any]:
        """Retorna dados do funcionário por cargo.

        Returns:
            Dados prontos para persistência.
        """
        return {
            "nome": self.nome,
            "codigo_rf": self.codigo_rf,
            "data_inicio": self.data_inicio,
            "data_fim": self.data_fim,
            "cargo": self.cargo,
            "codigo_cargo": self.codigo_cargo,
        }


@dataclass(slots=True)
class FuncionarioSistemaPerfilOut:
    """Estrutura para o model ``FuncionarioSistemaPerfil``."""

    login: str
    nome_servidor: str | None
    cpf: str | None
    email: str | None
    uad_codigo: str | None
    perfil: UUID
    sis_id: int

    def __post_init__(self) -> None:
        """Normaliza campos do perfil de sistema."""
        self.login = _normalizar_texto(self.login)
        self.nome_servidor = _normalizar_texto_opcional(self.nome_servidor)
        self.cpf = _normalizar_texto_opcional(self.cpf)
        self.email = _normalizar_texto_opcional(self.email)
        self.uad_codigo = _normalizar_texto_opcional(self.uad_codigo)
        self.perfil = _normalizar_uuid(self.perfil)
        self.sis_id = _normalizar_int(self.sis_id)

    def to_dict(self) -> dict[str, Any]:
        """Retorna dados do perfil de sistema.

        Returns:
            Dados prontos para persistência.
        """
        return {
            "login": self.login,
            "nome_servidor": self.nome_servidor,
            "cpf": self.cpf,
            "email": self.email,
            "uad_codigo": self.uad_codigo,
            "perfil": self.perfil,
            "sis_id": self.sis_id,
        }


@dataclass(slots=True)
class LotacaoServidorOut:
    """Estrutura para o model ``LotacaoServidor``."""

    cargo_base_id: int
    codigo_unidade_educacao: str
    codigo_dre: str | None
    dt_inicio: Any
    dt_fim: Any

    def to_dict(self) -> dict[str, Any]:
        """Retorna dados da lotação.

        Returns:
            Dados prontos para persistência.
        """
        return {
            "cargo_base_id": self.cargo_base_id,
            "codigo_unidade_educacao": self.codigo_unidade_educacao,
            "codigo_dre": self.codigo_dre,
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
        """Retorna dados do cargo sobreposto.

        Returns:
            Dados prontos para persistência.
        """
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
        """Retorna dados da função atividade.

        Returns:
            Dados prontos para persistência.
        """
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
        """Retorna dados do laudo médico.

        Returns:
            Dados prontos para persistência.
        """
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
    nome_pai: str | None
    nome_mae: str | None
    data_nascimento: Any
    rg: str | None
    titulo_eleitoral: str | None
    pis_pasep: str | None

    def __post_init__(self) -> None:
        """Normaliza dados opcionais da pessoa."""
        self.cpf = _normalizar_texto(self.cpf)
        self.nome = _normalizar_texto(self.nome)
        self.nome_social = _normalizar_texto_opcional(self.nome_social)
        self.nome_pai = _normalizar_texto_opcional(self.nome_pai)
        self.nome_mae = _normalizar_texto_opcional(self.nome_mae)
        self.data_nascimento = _normalizar_datetime(self.data_nascimento)
        self.rg = _normalizar_texto_opcional(self.rg)
        self.titulo_eleitoral = _normalizar_texto_opcional(
            self.titulo_eleitoral
        )
        self.pis_pasep = _normalizar_texto_opcional(self.pis_pasep)

    def to_dict(self) -> dict[str, Any]:
        """Retorna dados da pessoa.

        Returns:
            Dados prontos para persistência.
        """
        return {
            "codigo_pessoa": self.codigo_pessoa,
            "cpf": self.cpf,
            "nome": self.nome,
            "nome_social": self.nome_social,
            "nome_pai": self.nome_pai,
            "nome_mae": self.nome_mae,
            "data_nascimento": self.data_nascimento,
            "rg": self.rg,
            "titulo_eleitoral": self.titulo_eleitoral,
            "pis_pasep": self.pis_pasep,
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
        """Retorna dados do contrato externo.

        Returns:
            Dados prontos para persistência.
        """
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
    descricao_turma_escola: str | None
    codigo_turma_escola_grade_programa: int | None
    codigo_grade: int | None
    codigo_componente_curricular: int | None
    descricao_componente_curricular: str | None
    codigo_serie_grade: int | None
    ano_escolar: str | None
    ano_atribuicao: int | None
    codigo_etapa_ensino: int | None
    dt_atribuicao_aula: Any
    dt_inicio_turma: Any
    dt_fim_turma: Any
    dt_disponibilizacao_aulas: Any
    codigo_motivo_disponibilizacao: int | None
    dt_cancelamento: Any
    codigo_dre: str | None
    nome_dre: str | None
    abreviacao_dre: str | None
    nome_unidade_educacional: str | None
    codigo_tipo_escola: int | None
    codigo_tipo_turma: int | None
    modalidade: str | None
    codigo_modalidade: int | None
    semestre: int | None
    duracao_turno: int | None
    tipo_turno: int | None

    def to_dict(self) -> dict[str, Any]:
        """Retorna dados da atribuição de aula.

        Returns:
            Dados prontos para persistência.
        """
        return {
            "id": self.id,
            "cargo_base_id": self.cargo_base_id,
            "codigo_unidade_educacao": self.codigo_unidade_educacao,
            "codigo_turma_escola": self.codigo_turma_escola,
            "descricao_turma_escola": self.descricao_turma_escola,
            "codigo_turma_escola_grade_programa": (
                self.codigo_turma_escola_grade_programa
            ),
            "codigo_grade": self.codigo_grade,
            "codigo_componente_curricular": self.codigo_componente_curricular,
            "descricao_componente_curricular": (
                self.descricao_componente_curricular
            ),
            "codigo_serie_grade": self.codigo_serie_grade,
            "ano_escolar": self.ano_escolar,
            "ano_atribuicao": self.ano_atribuicao,
            "codigo_etapa_ensino": self.codigo_etapa_ensino,
            "dt_atribuicao_aula": self.dt_atribuicao_aula,
            "dt_inicio_turma": self.dt_inicio_turma,
            "dt_fim_turma": self.dt_fim_turma,
            "dt_disponibilizacao_aulas": self.dt_disponibilizacao_aulas,
            "codigo_motivo_disponibilizacao": (
                self.codigo_motivo_disponibilizacao
            ),
            "dt_cancelamento": self.dt_cancelamento,
            "codigo_dre": (
                str(self.codigo_dre).strip() if self.codigo_dre else None
            ),
            "nome_dre": (
                str(self.nome_dre).strip() if self.nome_dre else None
            ),
            "abreviacao_dre": (
                str(self.abreviacao_dre).strip()
                if self.abreviacao_dre
                else None
            ),
            "nome_unidade_educacional": (
                str(self.nome_unidade_educacional).strip()
                if self.nome_unidade_educacional
                else None
            ),
            "codigo_tipo_escola": self.codigo_tipo_escola,
            "codigo_tipo_turma": self.codigo_tipo_turma,
            "modalidade": (
                str(self.modalidade).strip() if self.modalidade else None
            ),
            "codigo_modalidade": self.codigo_modalidade,
            "semestre": self.semestre,
            "duracao_turno": self.duracao_turno,
            "tipo_turno": self.tipo_turno,
        }


@dataclass(slots=True)
class AtribuicaoExternoOut:
    """Estrutura para o model ``AtribuicaoExterno``."""

    id: int
    contrato_externo_id: int
    codigo_unidade_educacao: str
    codigo_turma_escola: int | None
    descricao_turma_escola: str | None
    codigo_grade: int | None
    codigo_componente_curricular: int | None
    descricao_componente_curricular: str | None
    codigo_serie_grade: int | None
    codigo_turma_escola_grade_programa: int | None
    ano_escolar: str | None
    ano_atribuicao: int | None
    codigo_etapa_ensino: int | None
    dt_atribuicao: Any
    dt_inicio_turma: Any
    dt_fim_turma: Any
    dt_disponibilizacao: Any
    codigo_motivo_disponibilizacao_externo: int | None
    dt_cancelamento: Any

    def to_dict(self) -> dict[str, Any]:
        """Retorna dados da atribuição externa.

        Returns:
            Dados prontos para persistência.
        """
        return {
            "id": self.id,
            "contrato_externo_id": self.contrato_externo_id,
            "codigo_unidade_educacao": self.codigo_unidade_educacao,
            "codigo_turma_escola": self.codigo_turma_escola,
            "descricao_turma_escola": self.descricao_turma_escola,
            "codigo_grade": self.codigo_grade,
            "codigo_componente_curricular": self.codigo_componente_curricular,
            "descricao_componente_curricular": (
                self.descricao_componente_curricular
            ),
            "codigo_serie_grade": self.codigo_serie_grade,
            "codigo_turma_escola_grade_programa": (
                self.codigo_turma_escola_grade_programa
            ),
            "ano_escolar": self.ano_escolar,
            "ano_atribuicao": self.ano_atribuicao,
            "codigo_etapa_ensino": self.codigo_etapa_ensino,
            "dt_atribuicao": self.dt_atribuicao,
            "dt_inicio_turma": self.dt_inicio_turma,
            "dt_fim_turma": self.dt_fim_turma,
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
    """Normaliza nulo e vazio para zero.

    Args:
        valor: Valor recebido da origem.

    Returns:
        Valor inteiro normalizado.
    """
    if valor in (None, ""):
        return 0
    return int(valor)


def _normalizar_int_opcional(valor: Any) -> int | None:
    """Normaliza nulo e vazio para None.

    Args:
        valor: Valor recebido da origem.

    Returns:
        Valor inteiro normalizado ou `None`.
    """
    if valor in (None, ""):
        return None
    return int(valor)


def _normalizar_uuid(valor: Any) -> UUID:
    """Normaliza valor recebido para UUID.

    Args:
        valor: Valor recebido da origem.

    Returns:
        UUID normalizado.
    """
    if isinstance(valor, UUID):
        return valor
    return UUID(str(valor).strip())


def _normalizar_bool(valor: Any) -> bool:
    """Retorna booleano a partir de indicadores de origem.

    Args:
        valor: Valor recebido da origem.

    Returns:
        Indicador convertido para booleano.
    """
    if isinstance(valor, str):
        return valor.strip().lower() in {"1", "true", "t", "s", "sim"}
    return bool(valor)


def _normalizar_datetime(valor: Any) -> Any:
    """Garante datetime com timezone (aware).

    Args:
        valor: Valor de data/hora recebido da origem.

    Returns:
        Data/hora pronta para persistencia no Django.
    """
    if valor is None or not hasattr(valor, "tzinfo"):
        return valor
    return make_aware(valor)


def _normalizar_data_chave_funcionario(valor: Any) -> Any:
    """Normaliza data usada na chave do funcionário.

    Args:
        valor: Data recebida para normalização.

    Returns:
        Data normalizada para persistência.
    """
    return _normalizar_datetime(valor or _DATA_CHAVE_PADRAO)


@dataclass(slots=True)
class FuncionarioUnidadeEducacionalOut:
    """Estrutura para o model ``FuncionarioUnidadeEducacional``."""

    nome: str
    nome_social: str | None
    cpf: str | None
    codigo_rf: str
    codigo_ue: str
    codigo_dre: str | None
    data_inicio: Any
    data_fim: Any
    dt_fim_nomeacao: Any
    dt_fim_funcao_atividade: Any
    origem_vinculo: str | None
    codigo_cargo: int | None
    cargo: str | None
    codigo_tipo_funcao_atividade: int | None
    pessoa_id: int | None
    nome_ue: str | None
    tipo_funcionario_externo: str | None
    dc_funcao_externo: str | None
    supervisor_dre: Any
    eh_professor: Any
    esta_afastado: Any
    funcao_externo: int | None
    tipo_funcao_externo: int | None

    def __post_init__(self) -> None:
        """Normaliza campos do funcionário por unidade."""
        self.nome = _normalizar_texto(self.nome)
        self.nome_social = _normalizar_texto_opcional(self.nome_social)
        self.cpf = _normalizar_texto_opcional(self.cpf)
        self.codigo_rf = _normalizar_texto(self.codigo_rf)
        self.codigo_ue = _normalizar_texto(self.codigo_ue)
        self.codigo_dre = _normalizar_texto_opcional(self.codigo_dre)
        self.data_inicio = _normalizar_data_chave_funcionario(self.data_inicio)
        self.data_fim = _normalizar_datetime(self.data_fim)
        self.dt_fim_nomeacao = _normalizar_datetime(self.dt_fim_nomeacao)
        self.dt_fim_funcao_atividade = _normalizar_datetime(
            self.dt_fim_funcao_atividade
        )
        self.origem_vinculo = _normalizar_texto_opcional(self.origem_vinculo)
        self.codigo_cargo = _normalizar_int_opcional(self.codigo_cargo)
        self.cargo = _normalizar_texto_opcional(self.cargo)
        self.codigo_tipo_funcao_atividade = _normalizar_int_opcional(
            self.codigo_tipo_funcao_atividade
        )
        self.pessoa_id = _normalizar_int_opcional(self.pessoa_id)
        self.nome_ue = _normalizar_texto_opcional(self.nome_ue)
        self.tipo_funcionario_externo = _normalizar_texto_opcional(
            self.tipo_funcionario_externo
        )
        self.dc_funcao_externo = _normalizar_texto_opcional(
            self.dc_funcao_externo
        )
        self.supervisor_dre = _normalizar_bool(self.supervisor_dre)
        self.eh_professor = _normalizar_bool(self.eh_professor)
        self.esta_afastado = _normalizar_bool(self.esta_afastado)
        self.funcao_externo = _normalizar_int_opcional(self.funcao_externo)
        self.tipo_funcao_externo = _normalizar_int_opcional(
            self.tipo_funcao_externo
        )

    def to_dict(self) -> dict[str, Any]:
        """Retorna dados do funcionário por unidade.

        Returns:
            Dados prontos para persistência.
        """
        return {
            "nome": self.nome,
            "nome_social": self.nome_social,
            "cpf": self.cpf,
            "codigo_rf": self.codigo_rf,
            "codigo_ue": self.codigo_ue,
            "codigo_dre": self.codigo_dre,
            "data_inicio": self.data_inicio,
            "data_fim": self.data_fim,
            "dt_fim_nomeacao": self.dt_fim_nomeacao,
            "dt_fim_funcao_atividade": self.dt_fim_funcao_atividade,
            "origem_vinculo": self.origem_vinculo,
            "codigo_cargo": self.codigo_cargo,
            "cargo": self.cargo,
            "codigo_tipo_funcao_atividade": (
                _normalizar_int(self.codigo_tipo_funcao_atividade)
            ),
            "pessoa_id": self.pessoa_id,
            "nome_ue": self.nome_ue,
            "tipo_funcionario_externo": self.tipo_funcionario_externo,
            "dc_funcao_externo": self.dc_funcao_externo,
            "supervisor_dre": self.supervisor_dre,
            "eh_professor": self.eh_professor,
            "esta_afastado": self.esta_afastado,
            "funcao_externo": _normalizar_int(self.funcao_externo),
            "tipo_funcao_externo": _normalizar_int(self.tipo_funcao_externo),
        }


@dataclass(slots=True)
class TurmaAtribuidaUeOut:
    """Estrutura para o model ``TurmaAtribuidaUe``."""

    codigo_escola: str
    codigo_turma: int
    ano_letivo: int
    modalidade: str | None
    semestre: int | None
    codigo_modalidade: int | None
    codigo_dre: str | None
    dre: str | None
    dre_abreviacao: str | None
    ue: str | None
    ue_abreviacao: str | None
    nome_turma: str | None
    ano: str | None
    tipo_ue: str | None
    codigo_tipo_ue: int | None
    codigo_tipo_escola: int | None
    tipo_escola: str | None
    duracao_turno: int | None
    tipo_turno: int | None
    usuario_rf: str
    cargo: int | None
    cargo_sobreposto: int | None

    def to_dict(self) -> dict[str, Any]:
        """Retorna dados da turma atribuída por UE.

        Returns:
            Dados prontos para persistência.
        """
        return {
            "codigo_escola": self.codigo_escola,
            "codigo_turma": self.codigo_turma,
            "ano_letivo": self.ano_letivo,
            "modalidade": _normalizar_texto_opcional(self.modalidade),
            "semestre": _normalizar_int_opcional(self.semestre),
            "codigo_modalidade": _normalizar_int_opcional(
                self.codigo_modalidade
            ),
            "codigo_dre": _normalizar_texto_opcional(self.codigo_dre),
            "dre": _normalizar_texto_opcional(self.dre),
            "dre_abreviacao": _normalizar_texto_opcional(self.dre_abreviacao),
            "ue": _normalizar_texto_opcional(self.ue),
            "ue_abreviacao": _normalizar_texto_opcional(self.ue_abreviacao),
            "nome_turma": _normalizar_texto_opcional(self.nome_turma),
            "ano": _normalizar_texto_opcional(self.ano),
            "tipo_ue": _normalizar_texto_opcional(self.tipo_ue),
            "codigo_tipo_ue": _normalizar_int_opcional(self.codigo_tipo_ue),
            "codigo_tipo_escola": _normalizar_int_opcional(
                self.codigo_tipo_escola
            ),
            "tipo_escola": _normalizar_texto_opcional(self.tipo_escola),
            "duracao_turno": _normalizar_int_opcional(self.duracao_turno),
            "tipo_turno": _normalizar_int_opcional(self.tipo_turno),
            "usuario_rf": self.usuario_rf,
            "cargo": _normalizar_int_opcional(self.cargo),
            "cargo_sobreposto": _normalizar_int_opcional(
                self.cargo_sobreposto
            ),
        }


@dataclass(slots=True)
class DisciplinaTurmaAtribuidaUeOut:
    """Estrutura para o model ``DisciplinaTurmaAtribuidaUe``."""

    codigo_escola: str
    codigo_turma: int
    ano_letivo: int
    usuario_rf: str
    codigo_componente_curricular: int
    descricao_componente_curricular: str
    codigo_componente_curricular_pai: int | None
    regencia: bool
    codigo_componente_territorio_saber: int | None
    territorio_saber: bool
    codigo_dre: str | None
    codigo_tipo_escola: int | None
    tipo_escola: str | None
    cargo: int | None
    cargo_sobreposto: int | None

    def to_dict(self) -> dict[str, Any]:
        """Retorna dados da disciplina atribuída por UE.

        Returns:
            Dados prontos para persistência.
        """
        return {
            "codigo_escola": self.codigo_escola,
            "codigo_turma": _normalizar_int(self.codigo_turma),
            "ano_letivo": _normalizar_int(self.ano_letivo),
            "usuario_rf": self.usuario_rf,
            "codigo_componente_curricular": _normalizar_int(
                self.codigo_componente_curricular
            ),
            "descricao_componente_curricular": _normalizar_texto(
                self.descricao_componente_curricular
            ),
            "codigo_componente_curricular_pai": _normalizar_int_opcional(
                self.codigo_componente_curricular_pai
            ),
            "regencia": _normalizar_bool(self.regencia),
            "codigo_componente_territorio_saber": _normalizar_int_opcional(
                self.codigo_componente_territorio_saber
            ),
            "territorio_saber": _normalizar_bool(self.territorio_saber),
            "codigo_dre": _normalizar_texto_opcional(self.codigo_dre),
            "codigo_tipo_escola": _normalizar_int_opcional(
                self.codigo_tipo_escola
            ),
            "tipo_escola": _normalizar_texto_opcional(self.tipo_escola),
            "cargo": _normalizar_int_opcional(self.cargo),
            "cargo_sobreposto": _normalizar_int_opcional(
                self.cargo_sobreposto
            ),
        }
