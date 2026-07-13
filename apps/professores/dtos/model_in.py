"""DTOs de entrada para o domínio Professores."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.professores.dtos.model_out import (
        AtribuicaoAulaOut,
        AtribuicaoExternoOut,
        CargoBaseServidorOut,
        CargoSobrepostoServidorOut,
        ContratoExternoOut,
        DisciplinaTurmaAtribuidaUeOut,
        FuncaoAtividadeCargoServidorOut,
        FuncionarioUnidadeEducacionalOut,
        LaudoMedicoOut,
        LotacaoServidorOut,
        PessoaOut,
        ProfessorOut,
        TurmaAtribuidaUeOut,
    )


@dataclass(slots=True)
class ProfessorIn:
    """Dados da view `v_servidor_cotic`."""

    cd_registro_funcional: Any
    nm_pessoa: Any
    nm_social: Any
    cd_cpf_pessoa: Any

    def to_domain(self) -> "ProfessorOut":
        from apps.professores.dtos.model_out import ProfessorOut

        return ProfessorOut(
            codigo_rf=str(self.cd_registro_funcional).strip(),
            nome=self.nm_pessoa or "",
            nome_social=self.nm_social or None,
            cpf=(
                str(self.cd_cpf_pessoa).strip() if self.cd_cpf_pessoa else None
            ),
        )


@dataclass(slots=True)
class CargoBaseServidorIn:
    """Dados da view `v_cargo_base_cotic` + tabela `cargo`."""

    cd_cargo_base_servidor: Any
    cd_registro_funcional: Any
    cd_cargo: Any
    dc_cargo: Any
    cd_situacao_funcional: Any
    dt_posse: Any
    dt_fim_nomeacao: Any
    dt_cancelamento: Any

    def to_domain(self) -> "CargoBaseServidorOut":
        from apps.professores.dtos.model_out import CargoBaseServidorOut

        dc = str(self.dc_cargo).strip() if self.dc_cargo else None
        return CargoBaseServidorOut(
            id=self.cd_cargo_base_servidor,
            professor_id=str(self.cd_registro_funcional).strip(),
            codigo_cargo=self.cd_cargo,
            descricao_cargo=dc or None,
            situacao_funcional=self.cd_situacao_funcional,
            dt_posse=self.dt_posse,
            dt_fim_nomeacao=self.dt_fim_nomeacao,
            dt_cancelamento=self.dt_cancelamento,
        )


@dataclass(slots=True)
class LotacaoServidorIn:
    """Dados da tabela `lotacao_servidor`."""

    cd_cargo_base_servidor: Any
    cd_unidade_educacao: Any
    dt_inicio: Any
    dt_fim: Any

    def to_domain(self) -> "LotacaoServidorOut":
        from apps.professores.dtos.model_out import LotacaoServidorOut

        return LotacaoServidorOut(
            cargo_base_id=self.cd_cargo_base_servidor,
            codigo_unidade_educacao=str(self.cd_unidade_educacao).strip(),
            dt_inicio=self.dt_inicio,
            dt_fim=self.dt_fim,
        )


@dataclass(slots=True)
class CargoSobrepostoServidorIn:
    """Dados da tabela `cargo_sobreposto_servidor`."""

    cd_cargo_base_servidor: Any
    cd_cargo: Any
    cd_unidade_local_servico: Any
    dt_fim_cargo_sobreposto: Any

    def to_domain(self) -> "CargoSobrepostoServidorOut":
        from apps.professores.dtos.model_out import CargoSobrepostoServidorOut

        return CargoSobrepostoServidorOut(
            cargo_base_id=self.cd_cargo_base_servidor,
            codigo_cargo=self.cd_cargo,
            codigo_unidade_local_servico=str(
                self.cd_unidade_local_servico
            ).strip(),
            dt_fim_cargo_sobreposto=self.dt_fim_cargo_sobreposto,
        )


@dataclass(slots=True)
class FuncaoAtividadeCargoServidorIn:
    """Dados da tabela `funcao_atividade_cargo_servidor`."""

    cd_cargo_base_servidor: Any
    cd_unidade_local_servico: Any
    dt_fim_funcao_atividade: Any

    def to_domain(self) -> "FuncaoAtividadeCargoServidorOut":
        from apps.professores.dtos.model_out import (
            FuncaoAtividadeCargoServidorOut,
        )

        return FuncaoAtividadeCargoServidorOut(
            cargo_base_id=self.cd_cargo_base_servidor,
            codigo_unidade_local_servico=str(
                self.cd_unidade_local_servico
            ).strip(),
            dt_fim_funcao_atividade=self.dt_fim_funcao_atividade,
        )


@dataclass(slots=True)
class LaudoMedicoIn:
    """Dados da tabela `laudo_medico`."""

    cd_cargo_base_servidor: Any

    def to_domain(self) -> "LaudoMedicoOut":
        from apps.professores.dtos.model_out import LaudoMedicoOut

        return LaudoMedicoOut(
            cargo_base_id=self.cd_cargo_base_servidor,
        )


@dataclass(slots=True)
class PessoaIn:
    """Dados da tabela `pessoa`."""

    cd_pessoa: Any
    cd_cpf_pessoa: Any
    nm_pessoa: Any
    nm_social: Any

    def to_domain(self) -> "PessoaOut":
        from apps.professores.dtos.model_out import PessoaOut

        return PessoaOut(
            codigo_pessoa=self.cd_pessoa,
            cpf=str(self.cd_cpf_pessoa).strip(),
            nome=self.nm_pessoa or "",
            nome_social=self.nm_social or None,
        )


@dataclass(slots=True)
class ContratoExternoIn:
    """Dados da tabela `contrato_externo`."""

    cd_contrato_externo: Any
    cd_pessoa: Any
    cd_tipo_funcao_funcionario_externo: Any
    cd_unidade_educacao: Any
    dt_cancelamento: Any
    cd_motivo_desligamento_externo: Any

    def to_domain(self) -> "ContratoExternoOut":
        from apps.professores.dtos.model_out import ContratoExternoOut

        return ContratoExternoOut(
            codigo_contrato=self.cd_contrato_externo,
            pessoa_id=self.cd_pessoa,
            codigo_tipo_funcao=self.cd_tipo_funcao_funcionario_externo,
            codigo_unidade_educacao=str(self.cd_unidade_educacao).strip(),
            dt_cancelamento=self.dt_cancelamento,
            codigo_motivo_desligamento=self.cd_motivo_desligamento_externo,
        )


@dataclass(slots=True)
class AtribuicaoAulaIn:
    """Dados da tabela `atribuicao_aula`."""

    cd_atribuicao_aula: Any
    cd_cargo_base_servidor: Any
    cd_unidade_educacao: Any
    cd_turma_escola: Any
    dc_turma_escola: Any
    cd_turma_escola_grade_programa: Any
    cd_grade: Any
    cd_componente_curricular: Any
    dc_componente_curricular: Any
    cd_serie_grade: Any
    ano_escolar: Any
    an_atribuicao: Any
    cd_etapa_ensino: Any
    dt_atribuicao_aula: Any
    dt_inicio_turma: Any
    dt_fim_turma: Any
    dt_disponibilizacao_aulas: Any
    cd_motivo_disponibilizacao: Any
    dt_cancelamento: Any
    codigo_dre: Any
    nome_dre: Any
    abreviacao_dre: Any
    nome_unidade_educacional: Any
    codigo_tipo_escola: Any
    codigo_tipo_turma: Any
    modalidade: Any
    codigo_modalidade: Any
    semestre: Any
    duracao_turno: Any
    tipo_turno: Any

    def to_domain(self) -> "AtribuicaoAulaOut":
        from apps.professores.dtos.model_out import AtribuicaoAulaOut

        return AtribuicaoAulaOut(
            id=self.cd_atribuicao_aula,
            cargo_base_id=self.cd_cargo_base_servidor,
            codigo_unidade_educacao=str(self.cd_unidade_educacao).strip(),
            codigo_turma_escola=self.cd_turma_escola,
            descricao_turma_escola=self.dc_turma_escola,
            codigo_turma_escola_grade_programa=(
                self.cd_turma_escola_grade_programa
            ),
            codigo_grade=self.cd_grade,
            codigo_componente_curricular=self.cd_componente_curricular,
            descricao_componente_curricular=self.dc_componente_curricular,
            codigo_serie_grade=self.cd_serie_grade,
            ano_escolar=self.ano_escolar,
            ano_atribuicao=self.an_atribuicao,
            codigo_etapa_ensino=self.cd_etapa_ensino,
            dt_atribuicao_aula=self.dt_atribuicao_aula,
            dt_inicio_turma=self.dt_inicio_turma,
            dt_fim_turma=self.dt_fim_turma,
            dt_disponibilizacao_aulas=self.dt_disponibilizacao_aulas,
            codigo_motivo_disponibilizacao=self.cd_motivo_disponibilizacao,
            dt_cancelamento=self.dt_cancelamento,
            codigo_dre=self.codigo_dre,
            nome_dre=self.nome_dre,
            abreviacao_dre=self.abreviacao_dre,
            nome_unidade_educacional=self.nome_unidade_educacional,
            codigo_tipo_escola=self.codigo_tipo_escola,
            codigo_tipo_turma=self.codigo_tipo_turma,
            modalidade=self.modalidade,
            codigo_modalidade=self.codigo_modalidade,
            semestre=self.semestre,
            duracao_turno=self.duracao_turno,
            tipo_turno=self.tipo_turno,
        )


@dataclass(slots=True)
class AtribuicaoExternoIn:
    """Dados da tabela `atribuicao_externo`."""

    cd_atribuicao_externo: Any
    cd_contrato_externo: Any
    cd_unidade_educacao: Any
    cd_turma_escola: Any
    dc_turma_escola: Any
    cd_grade: Any
    cd_componente_curricular: Any
    dc_componente_curricular: Any
    cd_serie_grade: Any
    cd_turma_escola_grade_programa: Any
    ano_escolar: Any
    an_atribuicao: Any
    cd_etapa_ensino: Any
    dt_atribuicao: Any
    dt_inicio_turma: Any
    dt_fim_turma: Any
    dt_disponibilizacao: Any
    cd_motivo_disponibilizacao_externo: Any
    dt_cancelamento: Any

    def to_domain(self) -> "AtribuicaoExternoOut":
        from apps.professores.dtos.model_out import AtribuicaoExternoOut

        return AtribuicaoExternoOut(
            id=self.cd_atribuicao_externo,
            contrato_externo_id=self.cd_contrato_externo,
            codigo_unidade_educacao=str(self.cd_unidade_educacao).strip(),
            codigo_turma_escola=self.cd_turma_escola,
            descricao_turma_escola=self.dc_turma_escola,
            codigo_grade=self.cd_grade,
            codigo_componente_curricular=self.cd_componente_curricular,
            descricao_componente_curricular=self.dc_componente_curricular,
            codigo_serie_grade=self.cd_serie_grade,
            codigo_turma_escola_grade_programa=(
                self.cd_turma_escola_grade_programa
            ),
            ano_escolar=self.ano_escolar,
            ano_atribuicao=self.an_atribuicao,
            codigo_etapa_ensino=self.cd_etapa_ensino,
            dt_atribuicao=self.dt_atribuicao,
            dt_inicio_turma=self.dt_inicio_turma,
            dt_fim_turma=self.dt_fim_turma,
            dt_disponibilizacao=self.dt_disponibilizacao,
            codigo_motivo_disponibilizacao_externo=(
                self.cd_motivo_disponibilizacao_externo
            ),
            dt_cancelamento=self.dt_cancelamento,
        )


@dataclass(slots=True)
class FuncionarioUnidadeEducacionalIn:
    """Dados consolidados de funcionario por unidade educacional."""

    nome: Any
    nome_social: Any
    cpf: Any
    codigo_rf: Any
    codigo_ue: Any
    data_inicio: Any
    data_fim: Any
    cd_cargo: Any
    cargo: Any
    cd_tipo_funcao_atividade: Any
    eh_professor: Any
    esta_afastado: Any
    funcao_externo: Any
    tipo_funcao_externo: Any

    def to_domain(self) -> "FuncionarioUnidadeEducacionalOut":
        """Monta o DTO de destino a partir da linha de origem.

        Returns:
            Dados normalizados do funcionario.
        """
        from apps.professores.dtos.model_out import (
            FuncionarioUnidadeEducacionalOut,
        )

        return FuncionarioUnidadeEducacionalOut(
            nome=self.nome or "",
            nome_social=self.nome_social or None,
            cpf=str(self.cpf).strip() if self.cpf else None,
            codigo_rf=str(self.codigo_rf).strip(),
            codigo_ue=str(self.codigo_ue).strip(),
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            codigo_cargo=self.cd_cargo,
            cargo=self.cargo or None,
            codigo_tipo_funcao_atividade=self.cd_tipo_funcao_atividade,
            eh_professor=self.eh_professor,
            esta_afastado=self.esta_afastado,
            funcao_externo=self.funcao_externo,
            tipo_funcao_externo=self.tipo_funcao_externo,
        )


@dataclass(slots=True)
class TurmaAtribuidaUeIn:
    """Dados consolidados de turma atribuída por UE."""

    codigo_escola: Any
    codigo_turma: Any
    ano_letivo: Any
    modalidade: Any
    semestre: Any
    codigo_modalidade: Any
    codigo_dre: Any
    dre: Any
    dre_abreviacao: Any
    ue: Any
    ue_abreviacao: Any
    nome_turma: Any
    ano: Any
    tipo_ue: Any
    codigo_tipo_ue: Any
    codigo_tipo_escola: Any
    tipo_escola: Any
    duracao_turno: Any
    tipo_turno: Any
    usuario_rf: Any
    cargo: Any
    cargo_sobreposto: Any

    def to_domain(self) -> "TurmaAtribuidaUeOut":
        """Monta o DTO de destino a partir da linha de origem."""
        from apps.professores.dtos.model_out import TurmaAtribuidaUeOut

        return TurmaAtribuidaUeOut(
            codigo_escola=str(self.codigo_escola).strip(),
            codigo_turma=self.codigo_turma,
            ano_letivo=self.ano_letivo,
            modalidade=self.modalidade,
            semestre=self.semestre,
            codigo_modalidade=self.codigo_modalidade,
            codigo_dre=self.codigo_dre,
            dre=self.dre,
            dre_abreviacao=self.dre_abreviacao,
            ue=self.ue,
            ue_abreviacao=self.ue_abreviacao,
            nome_turma=self.nome_turma,
            ano=self.ano,
            tipo_ue=self.tipo_ue,
            codigo_tipo_ue=self.codigo_tipo_ue,
            codigo_tipo_escola=self.codigo_tipo_escola,
            tipo_escola=self.tipo_escola,
            duracao_turno=self.duracao_turno,
            tipo_turno=self.tipo_turno,
            usuario_rf=str(self.usuario_rf).strip(),
            cargo=self.cargo,
            cargo_sobreposto=self.cargo_sobreposto,
        )


@dataclass(slots=True)
class DisciplinaTurmaAtribuidaUeIn:
    """Dados de disciplina atribuída por vínculo com UE."""

    codigo_escola: Any
    codigo_turma: Any
    ano_letivo: Any
    usuario_rf: Any
    codigo_componente_curricular: Any
    descricao_componente_curricular: Any
    codigo_componente_curricular_pai: Any
    regencia: Any
    codigo_componente_territorio_saber: Any
    territorio_saber: Any
    codigo_dre: Any
    codigo_tipo_escola: Any
    tipo_escola: Any
    cargo: Any
    cargo_sobreposto: Any

    def to_domain(self) -> "DisciplinaTurmaAtribuidaUeOut":
        """Monta o DTO de destino a partir da linha de origem."""
        from apps.professores.dtos.model_out import (
            DisciplinaTurmaAtribuidaUeOut,
        )

        return DisciplinaTurmaAtribuidaUeOut(
            codigo_escola=str(self.codigo_escola).strip(),
            codigo_turma=self.codigo_turma,
            ano_letivo=self.ano_letivo,
            usuario_rf=str(self.usuario_rf).strip(),
            codigo_componente_curricular=self.codigo_componente_curricular,
            descricao_componente_curricular=(
                self.descricao_componente_curricular
            ),
            codigo_componente_curricular_pai=(
                self.codigo_componente_curricular_pai
            ),
            regencia=self.regencia,
            codigo_componente_territorio_saber=(
                self.codigo_componente_territorio_saber
            ),
            territorio_saber=self.territorio_saber,
            codigo_dre=self.codigo_dre,
            codigo_tipo_escola=self.codigo_tipo_escola,
            tipo_escola=self.tipo_escola,
            cargo=self.cargo,
            cargo_sobreposto=self.cargo_sobreposto,
        )
