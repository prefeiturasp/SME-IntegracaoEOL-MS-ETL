"""DTOs de entrada para o domínio Pedagógico (dados extraídos do EOL)."""

from dataclasses import dataclass
from typing import Any

from apps.core.libs.helpers import make_aware, strip_str
from apps.pedagogico.queries import MAPA_COMPONENTE_PAI


@dataclass
class ComponenteCurricularSimplesIn:
    """Linha bruta da query ListarNaoCanceladasAsync."""

    codigo: Any
    """cd_componente_curricular."""

    descricao: Any
    """dc_componente_curricular (já com LTRIM/RTRIM aplicado pela query)."""

    def to_domain(self, transferido_em: Any) -> dict:
        return {
            "codigo": int(self.codigo),
            "descricao": strip_str(self.descricao),
            "transferido_em": transferido_em,
        }


@dataclass
class ComponentePorTurmaIn:
    """Linha bruta da query ObterComponentesPorTurmasAsync."""

    codigo: Any
    """cd_componente_curricular (com COALESCE para componente pai quando
       aplicável)."""

    descricao: Any
    """dc_componente_curricular."""

    eh_regencia: Any
    """1 se o componente curricular está na lista hardcoded de regência."""

    eh_territorio: Any
    """1 se o componente existe em turma_grade_territorio_experiencia."""

    tipo_escola: Any
    """tp_escola."""

    turno_turma: Any
    """qt_hora_duracao — horas de duração do turno."""

    ano_turma: Any
    """sg_resumida_serie — ex: "1", "2", "EI"."""

    ano_letivo: Any
    """an_letivo."""

    turma_codigo: Any
    """cd_turma_escola."""

    professor: Any
    """cd_registro_funcional (SME) ou cd_cpf_pessoa (externo)."""

    atribuicao_externa: Any
    """0 = professor SME (usar RF) | 1 = professor externo (usar CPF)."""

    def to_domain(
        self,
        transferido_em: Any,
        planejamento: bool = False,
    ) -> dict:
        codigo = int(self.codigo)
        regencia = bool(self.eh_regencia)
        territorio = bool(self.eh_territorio)
        return {
            "codigo": codigo,
            "descricao": strip_str(self.descricao),
            "regencia": regencia,
            "planejamento_regencia": planejamento,
            "territorio_saber": territorio,
            "codigo_componente_territorio_saber": (
                codigo if territorio else None
            ),
            "codigo_componente_curricular_pai": MAPA_COMPONENTE_PAI.get(
                codigo
            ),
            "turma_codigo": (
                str(self.turma_codigo)
                if self.turma_codigo is not None
                else None
            ),
            "exibir_componente_eol": not (
                int(self.ano_letivo) <= 2021 and codigo in MAPA_COMPONENTE_PAI
            ),
            "professor": (
                str(self.professor) if self.professor is not None else None
            ),
            "ano_letivo": int(self.ano_letivo),
            "transferido_em": transferido_em,
        }


@dataclass
class RegenciaComponenteCurricularIn:
    """Linha bruta da query AdicionarComponentesPlanejamentoAsync.

    Reutilizada para calcular ``planejamento_regencia`` /
    ``componente_planejamento_regencia``.
    """

    id_componente_curricular: Any
    turno: Any
    ano: Any


@dataclass
class ComponenteRegenciaIn:
    """ObterComponentesCurricularesTerritorioAtribuidos."""

    codigo_componente_curricular: Any
    descricao_componente_curricular: Any
    ano_turma: Any
    ano_letivo: Any
    turma_codigo: Any
    tipo_escola: Any
    turno_turma: Any
    rf_professor: Any
    codigo_experiencia_pedagogica: Any
    codigo_territorio_saber: Any
    descricao_territorio_saber: Any
    descricao_experiencia_pedagogica: Any
    data_atribuicao: Any
    ano_atribuicao: Any
    data_fim_turma: Any
    atribuicao_externa: Any
    data_disponibilizacao: Any
    codigo_motivo_disponibilizacao: Any

    def to_domain(
        self, transferido_em: Any, planejamento: bool = False
    ) -> dict:
        codigo = int(self.codigo_componente_curricular)
        territorio_saber = self.codigo_territorio_saber is not None
        return {
            "codigo": codigo,
            "codigo_componente_territorio_saber": (
                int(self.codigo_territorio_saber) if territorio_saber else None
            ),
            "descricao": strip_str(self.descricao_componente_curricular),
            "territorio_saber": territorio_saber,
            "tipo_escola": (
                str(self.tipo_escola) if self.tipo_escola is not None else None
            ),
            "turno_turma": (
                int(self.turno_turma) if self.turno_turma is not None else None
            ),
            "componente_planejamento_regencia": planejamento,
            "turma_codigo": (
                str(self.turma_codigo)
                if self.turma_codigo is not None
                else None
            ),
            "professor": (
                str(self.rf_professor)
                if self.rf_professor is not None
                else None
            ),
            "ano_turma": str(self.ano_turma),
            "ano_letivo": int(self.ano_letivo),
            "inicio_atribuicao": make_aware(self.data_atribuicao),
            "fim_atribuicao": make_aware(self.data_disponibilizacao),
            "transferido_em": transferido_em,
        }


@dataclass
class DadosAulaTurmaIn:
    """ObterDadosComponentesCurricularesRegenciaPorUeEAnoLetivoAsync."""

    componente_codigo: Any
    componente_descricao: Any
    turma_codigo: Any
    data_inicio_turma: Any
    ue_codigo: Any
    ano_letivo: Any
    tipo_periodicidade: Any

    def to_domain(self, transferido_em: Any) -> dict:
        return {
            "componente_codigo": str(self.componente_codigo),
            "componente_descricao": strip_str(self.componente_descricao),
            "turma_codigo": str(self.turma_codigo),
            "data_inicio_turma": make_aware(self.data_inicio_turma),
            "ue_codigo": (
                str(self.ue_codigo) if self.ue_codigo is not None else None
            ),
            "ano_letivo": (
                int(self.ano_letivo) if self.ano_letivo is not None else None
            ),
            "tipo_periodicidade": (
                int(self.tipo_periodicidade)
                if self.tipo_periodicidade is not None
                else None
            ),
            "transferido_em": transferido_em,
        }


@dataclass
class ComponentePorAnoLetivoIn:
    """ObterComponentesCurricularesEAnosTurmaApiEolPorAnoLetivo."""

    codigo_componente_curricular: Any
    descricao_componente_curricular: Any
    codigo_ano_turma: Any
    descricao_serie_ensino: Any
    codigo_serie_ensino: Any
    modalidade: Any
    ano_letivo: Any

    def to_domain(self, transferido_em: Any) -> dict:
        return {
            "codigo_componente_curricular": int(
                self.codigo_componente_curricular
            ),
            "descricao_componente_curricular": strip_str(
                self.descricao_componente_curricular
            ),
            "codigo_ano_turma": (
                str(self.codigo_ano_turma)
                if self.codigo_ano_turma is not None
                else None
            ),
            "descricao_serie_ensino": (
                strip_str(self.descricao_serie_ensino)
                if self.descricao_serie_ensino is not None
                else None
            ),
            "codigo_serie_ensino": (
                int(self.codigo_serie_ensino)
                if self.codigo_serie_ensino is not None
                else None
            ),
            "modalidade": (
                int(self.modalidade) if self.modalidade is not None else None
            ),
            "ano_letivo": int(self.ano_letivo),
            "transferido_em": transferido_em,
        }


@dataclass
class AtribuicaoTerritorioSaberIn:
    """Linha bruta da query SQL_ATRIBUICOES_TERRITORIO_SABER.

    Cada linha representa um componente atribuído por turma com território
    saber. O agrupamento ocorre em Python: linhas com mesma chave natural
    e mais de 1 componente geram registros em
    AgrupamentoAtribuicaoTerritorioSaber e filhos em
    ComponenteCurricularAgrupamento.
    """

    codigo_componente_curricular: Any
    codigo_turma: Any
    ano_letivo: Any
    rf_professor: Any
    codigo_territorio_saber: Any
    codigo_experiencia_pedagogica: Any
    descricao_territorio_saber: Any
    descricao_experiencia_pedagogica: Any
    data_atribuicao: Any
    data_disponibilizacao: Any
    codigo_motivo_disponibilizacao: Any
    data_fim_turma: Any
    atribuicao_externa: Any
