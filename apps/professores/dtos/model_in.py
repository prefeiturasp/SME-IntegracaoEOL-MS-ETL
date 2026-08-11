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
        FuncionarioCargoOut,
        FuncionarioConectaFormacaoOut,
        FuncionarioConectaModalidadeEscolaOut,
        FuncionarioSistemaPerfilOut,
        FuncionarioUnidadeEducacionalOut,
        FuncionarioVinculoFuncionalOut,
        LaudoMedicoOut,
        LotacaoServidorOut,
        PessoaOut,
        ProfessorEscolaAnoOut,
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
        """Retorna dados normalizados do professor.

        Returns:
            Dados do professor para persistência.
        """
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
        """Retorna dados normalizados do cargo base.

        Returns:
            Dados do cargo base para persistência.
        """
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
class FuncionarioCargoIn:
    """Dados de funcionário por cargo."""

    nm_pessoa: Any
    cd_registro_funcional: Any
    dt_posse: Any
    dt_fim_nomeacao: Any
    dc_cargo: Any
    cd_cargo: Any

    def to_domain(self) -> "FuncionarioCargoOut":
        """Retorna dados normalizados do funcionário por cargo.

        Returns:
            Dados do funcionário por cargo para persistência.
        """
        from apps.professores.dtos.model_out import FuncionarioCargoOut

        return FuncionarioCargoOut(
            nome=self.nm_pessoa,
            codigo_rf=self.cd_registro_funcional,
            data_inicio=self.dt_posse,
            data_fim=self.dt_fim_nomeacao,
            cargo=self.dc_cargo,
            codigo_cargo=self.cd_cargo,
        )


@dataclass(slots=True)
class ProfessorEscolaAnoIn:
    """Dados de professor por escola e ano."""

    origem: Any
    codigo_escola: Any
    ano_letivo: Any
    codigo_turma: Any
    codigo_rf: Any
    codigo_componente_curricular: Any
    nome: Any
    cargo: Any
    cpf: Any
    data_inicio_exercicio: Any

    def to_domain(self) -> "ProfessorEscolaAnoOut":
        """Retorna dados normalizados de professor por escola e ano.

        Returns:
            Dados de professor por escola e ano para persistência.
        """
        from apps.professores.dtos.model_out import ProfessorEscolaAnoOut

        return ProfessorEscolaAnoOut(
            origem=self.origem,
            codigo_escola=self.codigo_escola,
            ano_letivo=self.ano_letivo,
            codigo_turma=self.codigo_turma,
            codigo_rf=self.codigo_rf,
            codigo_componente_curricular=self.codigo_componente_curricular,
            nome=self.nome,
            cargo=self.cargo,
            cpf=self.cpf,
            data_inicio_exercicio=self.data_inicio_exercicio,
        )


@dataclass(slots=True)
class FuncionarioVinculoFuncionalIn:
    """Dados de vínculo funcional consolidado."""

    rf: Any
    cpf: Any
    cd_cargo_base: Any
    cargo_base: Any
    cd_dre_cargo_base: Any
    cd_ue_cargo_base: Any
    ue_cargo_base: Any
    tipo_vinculo_cargo_base: Any
    data_inicio_cargo_base: Any
    cd_cargo_sobreposto: Any
    cargo_sobreposto: Any
    cd_dre_cargo_sobreposto: Any
    cd_ue_cargo_sobreposto: Any
    ue_cargo_sobreposto: Any
    tipo_vinculo_cargo_sobreposto: Any
    data_inicio_cargo_sobreposto: Any
    cd_funcao_atividade: Any
    funcao_atividade: Any
    cd_dre_funcao_atividade: Any
    cd_ue_funcao_atividade: Any
    ue_funcao_atividade: Any
    tipo_vinculo_funcao_atividade: Any
    data_inicio_funcao_atividade: Any
    dt_cancelamento_funcao_atividade: Any
    dt_fim_funcao_atividade: Any

    def to_domain(self) -> "FuncionarioVinculoFuncionalOut":
        """Retorna dados normalizados do vínculo funcional.

        Returns:
            Dados do vínculo funcional para persistência.
        """
        from apps.professores.dtos.model_out import (
            FuncionarioVinculoFuncionalOut,
        )

        return FuncionarioVinculoFuncionalOut(
            rf=self.rf,
            cpf=self.cpf,
            cd_cargo_base=self.cd_cargo_base,
            cargo_base=self.cargo_base,
            cd_dre_cargo_base=self.cd_dre_cargo_base,
            cd_ue_cargo_base=self.cd_ue_cargo_base,
            ue_cargo_base=self.ue_cargo_base,
            tipo_vinculo_cargo_base=self.tipo_vinculo_cargo_base,
            data_inicio_cargo_base=self.data_inicio_cargo_base,
            cd_cargo_sobreposto=self.cd_cargo_sobreposto,
            cargo_sobreposto=self.cargo_sobreposto,
            cd_dre_cargo_sobreposto=self.cd_dre_cargo_sobreposto,
            cd_ue_cargo_sobreposto=self.cd_ue_cargo_sobreposto,
            ue_cargo_sobreposto=self.ue_cargo_sobreposto,
            tipo_vinculo_cargo_sobreposto=(self.tipo_vinculo_cargo_sobreposto),
            data_inicio_cargo_sobreposto=self.data_inicio_cargo_sobreposto,
            cd_funcao_atividade=self.cd_funcao_atividade,
            funcao_atividade=self.funcao_atividade,
            cd_dre_funcao_atividade=self.cd_dre_funcao_atividade,
            cd_ue_funcao_atividade=self.cd_ue_funcao_atividade,
            ue_funcao_atividade=self.ue_funcao_atividade,
            tipo_vinculo_funcao_atividade=(self.tipo_vinculo_funcao_atividade),
            data_inicio_funcao_atividade=self.data_inicio_funcao_atividade,
            dt_cancelamento_funcao_atividade=(
                self.dt_cancelamento_funcao_atividade
            ),
            dt_fim_funcao_atividade=self.dt_fim_funcao_atividade,
        )


@dataclass(slots=True)
class FuncionarioConectaFormacaoIn:
    """Dados de funcionário elegível para o Conecta Formação."""

    rf: Any
    nome: Any
    cpf: Any
    cargo_codigo: Any
    cargo: Any
    cargo_dre_codigo: Any
    cargo_ue_codigo: Any
    funcao_codigo: Any
    funcao: Any
    funcao_dre_codigo: Any
    funcao_ue_codigo: Any
    tipo_vinculo: Any
    codigo_modalidade: Any
    ano_turma: Any
    codigo_componente_curricular: Any
    eh_tipo_jornada_jeif: Any

    def to_domain(self) -> "FuncionarioConectaFormacaoOut":
        """Retorna dados normalizados do funcionário.

        Returns:
            Dados do funcionário para persistência.
        """
        from apps.professores.dtos.model_out import (
            FuncionarioConectaFormacaoOut,
        )

        return FuncionarioConectaFormacaoOut(
            rf=self.rf,
            nome=self.nome,
            cpf=self.cpf,
            cargo_codigo=self.cargo_codigo,
            cargo=self.cargo,
            cargo_dre_codigo=self.cargo_dre_codigo,
            cargo_ue_codigo=self.cargo_ue_codigo,
            funcao_codigo=self.funcao_codigo,
            funcao=self.funcao,
            funcao_dre_codigo=self.funcao_dre_codigo,
            funcao_ue_codigo=self.funcao_ue_codigo,
            tipo_vinculo=self.tipo_vinculo,
            codigo_modalidade=self.codigo_modalidade,
            ano_turma=self.ano_turma,
            codigo_componente_curricular=self.codigo_componente_curricular,
            eh_tipo_jornada_jeif=self.eh_tipo_jornada_jeif,
        )


@dataclass(slots=True)
class FuncionarioConectaModalidadeEscolaIn:
    """Dados de modalidade por unidade do Conecta Formação."""

    codigo_ue: Any
    codigo_modalidade: Any

    def to_domain(self) -> "FuncionarioConectaModalidadeEscolaOut":
        """Retorna dados normalizados da modalidade por unidade.

        Returns:
            Dados da modalidade por unidade para persistência.
        """
        from apps.professores.dtos.model_out import (
            FuncionarioConectaModalidadeEscolaOut,
        )

        return FuncionarioConectaModalidadeEscolaOut(
            codigo_ue=self.codigo_ue,
            codigo_modalidade=self.codigo_modalidade,
        )


@dataclass(slots=True)
class FuncionarioSistemaPerfilIn:
    """Dados de perfil de sistema do funcionário."""

    login: Any
    nome_servidor: Any
    cpf: Any
    email: Any
    perfil: Any
    uad_codigo: Any
    sis_id: Any

    def to_domain(self) -> "FuncionarioSistemaPerfilOut":
        """Retorna dados normalizados do perfil de sistema.

        Returns:
            Dados do perfil para persistência.
        """
        from apps.professores.dtos.model_out import (
            FuncionarioSistemaPerfilOut,
        )

        return FuncionarioSistemaPerfilOut(
            login=self.login,
            nome_servidor=self.nome_servidor,
            cpf=self.cpf,
            email=self.email,
            uad_codigo=self.uad_codigo,
            perfil=self.perfil,
            sis_id=self.sis_id,
        )


@dataclass(slots=True)
class LotacaoServidorIn:
    """Dados da tabela `lotacao_servidor`."""

    cd_cargo_base_servidor: Any
    cd_unidade_educacao: Any
    codigo_dre: Any
    dt_inicio: Any
    dt_fim: Any

    def to_domain(self) -> "LotacaoServidorOut":
        """Retorna dados normalizados da lotação.

        Returns:
            Dados da lotação para persistência.
        """
        from apps.professores.dtos.model_out import LotacaoServidorOut

        return LotacaoServidorOut(
            cargo_base_id=self.cd_cargo_base_servidor,
            codigo_unidade_educacao=str(self.cd_unidade_educacao).strip(),
            codigo_dre=(
                str(self.codigo_dre).strip() if self.codigo_dre else None
            ),
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
        """Retorna dados normalizados do cargo sobreposto.

        Returns:
            Dados do cargo sobreposto para persistência.
        """
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
        """Retorna dados normalizados da função atividade.

        Returns:
            Dados da função atividade para persistência.
        """
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
        """Retorna dados normalizados do laudo médico.

        Returns:
            Dados do laudo médico para persistência.
        """
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
    nm_pai_pessoa: Any
    nm_mae_pessoa: Any
    dt_nascimento_pessoa: Any
    nr_rg_pessoa: Any
    nr_titulo_eleitor_pessoa: Any
    cd_pis_pasep: Any

    def to_domain(self) -> "PessoaOut":
        """Retorna dados normalizados da pessoa.

        Returns:
            Dados da pessoa para persistência.
        """
        from apps.professores.dtos.model_out import PessoaOut

        return PessoaOut(
            codigo_pessoa=self.cd_pessoa,
            cpf=str(self.cd_cpf_pessoa).strip(),
            nome=self.nm_pessoa or "",
            nome_social=self.nm_social or None,
            nome_pai=self.nm_pai_pessoa,
            nome_mae=self.nm_mae_pessoa,
            data_nascimento=self.dt_nascimento_pessoa,
            rg=self.nr_rg_pessoa,
            titulo_eleitoral=self.nr_titulo_eleitor_pessoa,
            pis_pasep=self.cd_pis_pasep,
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
        """Retorna dados normalizados do contrato externo.

        Returns:
            Dados do contrato externo para persistência.
        """
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
    dt_disponibilizacao_aulas_origem: Any = None

    def to_domain(self) -> "AtribuicaoAulaOut":
        """Retorna dados normalizados da atribuição de aula.

        Returns:
            Dados da atribuição de aula para persistência.
        """
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
            dt_disponibilizacao_aulas_origem=(
                self.dt_disponibilizacao_aulas_origem
            ),
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
        """Retorna dados normalizados da atribuição externa.

        Returns:
            Dados da atribuição externa para persistência.
        """
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
    codigo_dre: Any
    data_inicio: Any
    data_fim: Any
    dt_fim_nomeacao: Any
    dt_fim_funcao_atividade: Any
    origem_vinculo: Any
    cd_cargo: Any
    cargo: Any
    cd_tipo_funcao_atividade: Any
    eh_professor: Any
    esta_afastado: Any
    funcao_externo: Any
    tipo_funcao_externo: Any
    pessoa_id: Any
    nome_ue: Any
    tipo_funcionario_externo: Any
    dc_funcao_externo: Any
    supervisor_dre: Any

    def to_domain(self) -> "FuncionarioUnidadeEducacionalOut":
        """Retorna dados normalizados do funcionário por unidade.

        Returns:
            Dados do funcionário por unidade para persistência.
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
            codigo_dre=(
                str(self.codigo_dre).strip() if self.codigo_dre else None
            ),
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            dt_fim_nomeacao=self.dt_fim_nomeacao,
            dt_fim_funcao_atividade=self.dt_fim_funcao_atividade,
            origem_vinculo=self.origem_vinculo,
            codigo_cargo=self.cd_cargo,
            cargo=self.cargo or None,
            codigo_tipo_funcao_atividade=self.cd_tipo_funcao_atividade,
            pessoa_id=self.pessoa_id,
            nome_ue=self.nome_ue,
            tipo_funcionario_externo=self.tipo_funcionario_externo,
            dc_funcao_externo=self.dc_funcao_externo,
            supervisor_dre=self.supervisor_dre,
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
        """Retorna dados normalizados da turma atribuída por UE.

        Returns:
            Dados da turma atribuída por UE para persistência.
        """
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
        """Retorna dados normalizados da disciplina atribuída por UE.

        Returns:
            Dados da disciplina atribuída por UE para persistência.
        """
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
