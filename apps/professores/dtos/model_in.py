"""DTOs de entrada para o domínio Professores.

Cada dataclass representa fielmente uma linha retornada pelo cursor SQL
(EOL/SQL Server via pyodbc). Todos os campos são tipados como ``Any``
pois o tipo exato depende do driver (datas podem chegar como
``datetime.date``, ``datetime.datetime`` ou ``None``).

O método ``to_domain()`` encapsula a lógica de transformação: recebe
o dado bruto e retorna o DTO de saída (``model_out``) pronto para
persistência.

Fluxo:
    tupla SQL → XxxIn(*row) → in_obj.to_domain() → XxxOut → XxxOut.to_dict()
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.professores.dtos.model_out import (
        AtribuicaoAulaOut,
        AtribuicaoExternoOut,
        CargoBaseServidorOut,
        CargoSobrepostoServidorOut,
        ContratoExternoOut,
        FuncaoAtividadeCargoServidorOut,
        LaudoMedicoOut,
        LotacaoServidorOut,
        PessoaOut,
        ProfessorOut,
        SerieTurmaGradeOut,
        TurmaEscolaGradeProgramaOut,
        TurmaEscolaOut,
        TurmaGradeTerritorioExperienciaOut,
        UnidadeEducacionalOut,
    )


@dataclass(slots=True)
class UnidadeEducacionalIn:
    """Dados brutos da view `v_cadastro_unidade_educacao`."""

    cd_unidade_educacao: Any
    cd_dre: Any
    cd_tipo_escola: Any

    def to_domain(self) -> "UnidadeEducacionalOut":
        from apps.professores.dtos.model_out import UnidadeEducacionalOut

        return UnidadeEducacionalOut(
            codigo_ue=str(self.cd_unidade_educacao).strip(),
            codigo_dre=str(self.cd_dre).strip() if self.cd_dre else None,
            codigo_tipo_escola=self.cd_tipo_escola or None,
        )


@dataclass(slots=True)
class TurmaEscolaIn:
    """Dados brutos da tabela `turma_escola`."""

    cd_turma_escola: Any
    cd_escola: Any
    an_letivo: Any
    st_turma_escola: Any
    cd_tipo_turma: Any
    dt_inicio_turma: Any
    dt_fim_turma: Any
    dt_fim: Any

    def to_domain(self) -> "TurmaEscolaOut":
        from apps.professores.dtos.model_out import TurmaEscolaOut

        return TurmaEscolaOut(
            codigo_turma=self.cd_turma_escola,
            codigo_escola=str(self.cd_escola).strip(),
            ano_letivo=self.an_letivo,
            status=self.st_turma_escola or "",
            tipo_turma=self.cd_tipo_turma,
            dt_inicio_turma=self.dt_inicio_turma,
            dt_fim_turma=self.dt_fim_turma,
            dt_fim=self.dt_fim,
        )


@dataclass(slots=True)
class SerieTurmaGradeIn:
    """Dados brutos da tabela `serie_turma_grade`."""

    cd_serie_grade: Any
    cd_turma_escola: Any
    cd_escola: Any
    cd_escola_grade: Any
    dt_fim: Any

    def to_domain(self) -> "SerieTurmaGradeOut":
        from apps.professores.dtos.model_out import SerieTurmaGradeOut

        return SerieTurmaGradeOut(
            codigo_serie_grade=self.cd_serie_grade,
            codigo_turma=self.cd_turma_escola,
            codigo_escola=str(self.cd_escola).strip(),
            codigo_escola_grade=self.cd_escola_grade,
            dt_fim=self.dt_fim,
        )


@dataclass(slots=True)
class TurmaEscolaGradeProgramaIn:
    """Dados brutos da tabela `turma_escola_grade_programa`."""

    cd_turma_escola_grade_programa: Any
    cd_turma_escola: Any
    cd_escola_grade: Any
    dt_fim: Any

    def to_domain(self) -> "TurmaEscolaGradeProgramaOut":
        from apps.professores.dtos.model_out import TurmaEscolaGradeProgramaOut

        return TurmaEscolaGradeProgramaOut(
            codigo=self.cd_turma_escola_grade_programa,
            codigo_turma=self.cd_turma_escola,
            codigo_escola_grade=self.cd_escola_grade,
            dt_fim=self.dt_fim,
        )


@dataclass(slots=True)
class TurmaGradeTerritorioExperienciaIn:
    """Dados brutos da tabela `turma_grade_territorio_experiencia`."""

    cd_serie_grade: Any
    cd_componente_curricular: Any
    cd_territorio_saber: Any
    cd_experiencia_pedagogica: Any
    dt_inicio: Any

    def to_domain(self) -> "TurmaGradeTerritorioExperienciaOut":
        from apps.professores.dtos.model_out import (
            TurmaGradeTerritorioExperienciaOut,
        )

        return TurmaGradeTerritorioExperienciaOut(
            codigo_serie_grade=self.cd_serie_grade,
            codigo_componente_curricular=self.cd_componente_curricular,
            codigo_territorio_saber=self.cd_territorio_saber,
            codigo_experiencia_pedagogica=self.cd_experiencia_pedagogica,
            dt_inicio=self.dt_inicio,
        )


@dataclass(slots=True)
class ProfessorIn:
    """Dados brutos da view `v_servidor_cotic`."""

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
    """Dados brutos da view `v_cargo_base_cotic`."""

    cd_cargo_base_servidor: Any
    cd_registro_funcional: Any
    cd_cargo: Any
    cd_situacao_funcional: Any
    dt_posse: Any
    dt_fim_nomeacao: Any
    dt_cancelamento: Any

    def to_domain(self) -> "CargoBaseServidorOut":
        from apps.professores.dtos.model_out import CargoBaseServidorOut

        return CargoBaseServidorOut(
            id=self.cd_cargo_base_servidor,
            professor_id=str(self.cd_registro_funcional).strip(),
            codigo_cargo=self.cd_cargo,
            situacao_funcional=self.cd_situacao_funcional,
            dt_posse=self.dt_posse,
            dt_fim_nomeacao=self.dt_fim_nomeacao,
            dt_cancelamento=self.dt_cancelamento,
        )


@dataclass(slots=True)
class LotacaoServidorIn:
    """Dados brutos da tabela `lotacao_servidor`."""

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
    """Dados brutos da tabela `cargo_sobreposto_servidor`."""

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
    """Dados brutos da tabela `funcao_atividade_cargo_servidor`."""

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
    """Dados brutos da tabela `laudo_medico`."""

    cd_cargo_base_servidor: Any

    def to_domain(self) -> "LaudoMedicoOut":
        from apps.professores.dtos.model_out import LaudoMedicoOut

        return LaudoMedicoOut(
            cargo_base_id=self.cd_cargo_base_servidor,
        )


@dataclass(slots=True)
class PessoaIn:
    """Dados brutos da tabela `pessoa`."""

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
    """Dados brutos da tabela `contrato_externo`."""

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
    """Dados brutos da tabela `atribuicao_aula`.

    ``cd_turma_escola`` é sempre NULL no SQL atual (fixado como
    ``NULL AS cd_turma_escola``), mas é mantido como campo para
    fidelidade à query.
    """

    cd_atribuicao_aula: Any
    cd_cargo_base_servidor: Any
    cd_unidade_educacao: Any
    cd_turma_escola: Any  # sempre NULL no SQL atual
    cd_turma_escola_grade_programa: Any
    cd_grade: Any
    cd_componente_curricular: Any
    cd_serie_grade: Any
    an_atribuicao: Any
    dt_atribuicao_aula: Any
    dt_disponibilizacao_aulas: Any
    cd_motivo_disponibilizacao: Any
    dt_cancelamento: Any

    def to_domain(self) -> "AtribuicaoAulaOut":
        from apps.professores.dtos.model_out import AtribuicaoAulaOut

        return AtribuicaoAulaOut(
            id=self.cd_atribuicao_aula,
            cargo_base_id=self.cd_cargo_base_servidor,
            codigo_unidade_educacao=str(self.cd_unidade_educacao).strip(),
            codigo_turma_escola=self.cd_turma_escola,
            codigo_turma_escola_grade_programa=(
                self.cd_turma_escola_grade_programa
            ),
            codigo_grade=self.cd_grade,
            codigo_componente_curricular=self.cd_componente_curricular,
            codigo_serie_grade=self.cd_serie_grade,
            ano_atribuicao=self.an_atribuicao,
            dt_atribuicao_aula=self.dt_atribuicao_aula,
            dt_disponibilizacao_aulas=self.dt_disponibilizacao_aulas,
            codigo_motivo_disponibilizacao=self.cd_motivo_disponibilizacao,
            dt_cancelamento=self.dt_cancelamento,
        )


@dataclass(slots=True)
class AtribuicaoExternoIn:
    """Dados brutos da tabela `atribuicao_externo`."""

    cd_atribuicao_externo: Any
    cd_contrato_externo: Any
    cd_unidade_educacao: Any
    cd_grade: Any
    cd_componente_curricular: Any
    cd_serie_grade: Any
    cd_turma_escola_grade_programa: Any
    an_atribuicao: Any
    dt_atribuicao: Any
    dt_disponibilizacao: Any
    cd_motivo_disponibilizacao_externo: Any
    dt_cancelamento: Any

    def to_domain(self) -> "AtribuicaoExternoOut":
        from apps.professores.dtos.model_out import AtribuicaoExternoOut

        return AtribuicaoExternoOut(
            id=self.cd_atribuicao_externo,
            contrato_externo_id=self.cd_contrato_externo,
            codigo_unidade_educacao=str(self.cd_unidade_educacao).strip(),
            codigo_grade=self.cd_grade,
            codigo_componente_curricular=self.cd_componente_curricular,
            codigo_serie_grade=self.cd_serie_grade,
            codigo_turma_escola_grade_programa=(
                self.cd_turma_escola_grade_programa
            ),
            ano_atribuicao=self.an_atribuicao,
            dt_atribuicao=self.dt_atribuicao,
            dt_disponibilizacao=self.dt_disponibilizacao,
            codigo_motivo_disponibilizacao_externo=(
                self.cd_motivo_disponibilizacao_externo
            ),
            dt_cancelamento=self.dt_cancelamento,
        )
