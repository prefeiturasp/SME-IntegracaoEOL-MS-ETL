"""DTOs de entrada para o domínio Pedagógico (dados extraídos do EOL)."""

from dataclasses import dataclass
from typing import Any

from apps.core.libs.helpers import (
    aware_or_none,
    int_or_none,
    str_or_none,
    str_value_or_none,
    strip_or_none,
    strip_str,
)


@dataclass
class ComponenteCurricularSimplesIn:
    """Linha bruta da query ListarNaoCanceladasAsync."""

    codigo: Any
    """cd_componente_curricular."""

    descricao: Any
    """dc_componente_curricular (já com LTRIM/RTRIM aplicado pela query)."""

    regencia: Any
    """Indica se o componente é regência."""

    def to_domain(self, transferido_em: Any) -> dict:
        return {
            "codigo": int(self.codigo),
            "descricao": strip_str(self.descricao),
            "regencia": bool(self.regencia),
            "transferido_em": transferido_em,
        }


@dataclass
class ComponenteTurmaIn:
    """Linha de SQL_COMPONENTE_TURMA.

    Estrutura turma x componente sem professor. A ordem das colunas deve
    corresponder exatamente ao SELECT de SQL_COMPONENTE_TURMA.
    """

    turma_codigo: Any
    componente_codigo: Any
    codigo_componente_territorio_saber: Any
    desc_territorio_saber: Any = None
    desc_experiencia_pedagogica: Any = None

    def to_domain(self, transferido_em: Any) -> dict:
        return {
            "turma_codigo": (
                str(self.turma_codigo)
                if self.turma_codigo is not None
                else None
            ),
            "componente_codigo": int(self.componente_codigo),
            "codigo_componente_territorio_saber": (
                int(self.codigo_componente_territorio_saber)
                if self.codigo_componente_territorio_saber is not None
                else None
            ),
            "desc_territorio_saber": self.desc_territorio_saber,
            "desc_experiencia_pedagogica": self.desc_experiencia_pedagogica,
            "transferido_em": transferido_em,
        }


@dataclass
class AtribuicaoComponenteIn:
    """Linha para AtribuicaoComponente."""

    turma_codigo: Any
    componente_codigo: Any
    professor: Any
    atribuicao_externa: bool
    ano_letivo: Any
    id_atribuicao_origem: Any
    dt_atribuicao: Any
    dt_cancelamento: Any
    dt_disponibilizacao: Any
    cd_motivo_disponibilizacao: Any

    def to_domain(self, transferido_em: Any) -> dict:
        return {
            "turma_codigo": (
                str(self.turma_codigo)
                if self.turma_codigo is not None
                else None
            ),
            "componente_codigo": int(self.componente_codigo),
            "professor": (
                str(self.professor) if self.professor is not None else None
            ),
            "atribuicao_externa": self.atribuicao_externa,
            "ano_letivo": int(self.ano_letivo),
            "id_atribuicao_origem": (
                int(self.id_atribuicao_origem)
                if self.id_atribuicao_origem is not None
                else None
            ),
            "dt_atribuicao": aware_or_none(self.dt_atribuicao),
            "dt_cancelamento": aware_or_none(self.dt_cancelamento),
            "dt_disponibilizacao": aware_or_none(self.dt_disponibilizacao),
            "cd_motivo_disponibilizacao": (
                int(self.cd_motivo_disponibilizacao)
                if self.cd_motivo_disponibilizacao is not None
                else None
            ),
            "transferido_em": transferido_em,
        }


@dataclass
class GradeComponenteCurricularIn:
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
class TurmaIn:
    """Linha bruta da query SQL_TURMAS."""

    codigo: Any
    ano_letivo: Any
    ano: Any
    tipo_turma: Any
    nome_turma: Any
    duracao_turno: Any
    tipo_turno: Any
    data_inicio_turma: Any
    data_fim: Any
    extinta: Any
    situacao: Any
    ue_codigo: Any
    data_atualizacao: Any
    data_status_turma_escola: Any
    serie_ensino: Any
    codigo_serie_ensino: Any
    modalidade: Any
    codigo_modalidade: Any
    codigo_tipo_programa: Any
    codigo_modalidade_etapa: Any
    semestre: Any
    ensino_especial: Any
    codigo_etapa_ensino: Any
    codigo_ciclo_ensino: Any
    tipo_escola: Any
    codigo_grade_programa: Any
    descricao_grade_programa: Any
    tipo_grade_programa: Any

    def to_domain(self, transferido_em: Any) -> dict:
        return {
            "codigo": int(self.codigo),
            "ano_letivo": int(self.ano_letivo),
            "ano": str_value_or_none(self.ano),
            "tipo_turma": int(self.tipo_turma),
            "nome_turma": strip_str(self.nome_turma),
            "duracao_turno": int_or_none(self.duracao_turno),
            "tipo_turno": int_or_none(self.tipo_turno),
            "data_inicio_turma": aware_or_none(self.data_inicio_turma),
            "data_fim": aware_or_none(self.data_fim),
            "extinta": bool(self.extinta),
            "situacao": str_or_none(self.situacao),
            "ue_codigo": str_or_none(self.ue_codigo),
            "data_atualizacao": aware_or_none(self.data_atualizacao),
            "data_status_turma_escola": aware_or_none(
                self.data_status_turma_escola
            ),
            "serie_ensino": strip_or_none(self.serie_ensino),
            "codigo_serie_ensino": int_or_none(self.codigo_serie_ensino),
            "modalidade": strip_or_none(self.modalidade),
            "codigo_modalidade": int_or_none(self.codigo_modalidade),
            "codigo_tipo_programa": int_or_none(self.codigo_tipo_programa),
            "codigo_modalidade_etapa": int_or_none(
                self.codigo_modalidade_etapa
            ),
            "semestre": int_or_none(self.semestre) or 0,
            "ensino_especial": bool(self.ensino_especial),
            "codigo_etapa_ensino": int_or_none(self.codigo_etapa_ensino),
            "codigo_ciclo_ensino": int_or_none(self.codigo_ciclo_ensino),
            "tipo_escola": int_or_none(self.tipo_escola) or 0,
            "codigo_grade_programa": (
                int_or_none(self.codigo_grade_programa) or 0
            ),
            "descricao_grade_programa": (
                strip_or_none(self.descricao_grade_programa) or "NAO INFORMADA"
            ),
            "tipo_grade_programa": (
                int_or_none(self.tipo_grade_programa) or 0
            ),
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

    def to_domain(self, transferido_em: Any) -> dict:
        return {
            "turma_codigo": str_or_none(self.codigo_turma),
            "componente_codigo": int(self.codigo_componente_curricular),
            "professor": str_or_none(self.rf_professor),
            "codigo_territorio_saber": int(self.codigo_territorio_saber),
            "codigo_experiencia_pedagogica": int_or_none(
                self.codigo_experiencia_pedagogica
            ),
            "desc_territorio_saber": strip_or_none(
                self.descricao_territorio_saber
            ),
            "desc_experiencia_pedagogica": strip_or_none(
                self.descricao_experiencia_pedagogica
            ),
            "dt_atribuicao": aware_or_none(self.data_atribuicao),
            "dt_disponibilizacao": aware_or_none(self.data_disponibilizacao),
            "cd_motivo_disponibilizacao": int_or_none(
                self.codigo_motivo_disponibilizacao
            ),
            "dt_fim_turma": aware_or_none(self.data_fim_turma),
            "atribuicao_externa": bool(self.atribuicao_externa),
            "ano_letivo": int(self.ano_letivo),
            "transferido_em": transferido_em,
        }


@dataclass
class ApiEolComponenteCurricularHierarquiaIn:
    """Linha de componentecurricularpai da API EOL."""

    id: Any
    id_componente_curricular_pai: Any
    id_componente_curricular: Any
    vigencia: Any

    def to_domain(self) -> dict:
        return {
            "id": int(self.id),
            "id_componente_curricular_pai": int(
                self.id_componente_curricular_pai
            ),
            "id_componente_curricular": int(self.id_componente_curricular),
            "vigencia": aware_or_none(self.vigencia),
        }


@dataclass
class ApiEolComponenteCurricularPAPIn:
    """Linha de componentecurricularpap da API EOL."""

    id: Any
    id_componente_curricular: Any

    def to_domain(self) -> dict:
        return {
            "id": int(self.id),
            "id_componente_curricular": int(self.id_componente_curricular),
        }


@dataclass
class ApiEolComponenteCurricularPlanejamentoRegenciaIn:
    """Linha de regenciacomponentecurricular da API EOL."""

    id: Any
    id_componente_curricular: Any
    turno: Any
    ano: Any

    def to_domain(self) -> dict:
        return {
            "id": int(self.id),
            "id_componente_curricular": int(self.id_componente_curricular),
            "turno": int_or_none(self.turno),
            "ano": int_or_none(self.ano),
        }


@dataclass
class ApiEolTurmaItinerarioEnsinoMedioIn:
    """Linha de turma_tipo_itinerario da API EOL."""

    id: Any
    nome: Any
    serie: Any

    def to_domain(self) -> dict:
        return {
            "id": int(self.id),
            "nome": strip_str(self.nome),
            "serie": str_or_none(self.serie),
        }


@dataclass
class ApiEolAgrupamentoAtribuicaoTerritorioSaberIn:
    """Linha de agrupamentoatribuicaoterritoriosaber da API EOL."""

    cod_agrupamento: Any
    cod_territorio_saber: Any
    cod_experiencia_pedagogica: Any
    dt_inicio_atribuicao: Any
    ano_atribuicao: Any
    dt_fim_atribuicao: Any
    dt_fim_turma: Any
    rf_professor: Any
    cod_turma: Any
    cod_componentes_curriculares: Any
    ano_letivo: Any
    cod_motivo_disponibilizacao: Any
    desc_territorio_saber: Any
    desc_experiencia_pedagogica: Any
    encerramento_atribuicao_agrupamento_atualizado: Any

    def to_domain(self, transferido_em: Any) -> dict:
        return {
            "cod_agrupamento": int(self.cod_agrupamento),
            "cod_territorio_saber": int(self.cod_territorio_saber),
            "cod_experiencia_pedagogica": int_or_none(
                self.cod_experiencia_pedagogica
            ),
            "dt_inicio_atribuicao": aware_or_none(self.dt_inicio_atribuicao),
            "ano_atribuicao": int(self.ano_atribuicao),
            "dt_fim_atribuicao": aware_or_none(self.dt_fim_atribuicao),
            "dt_fim_turma": aware_or_none(self.dt_fim_turma),
            "rf_professor": str_or_none(self.rf_professor),
            "cod_turma": str_or_none(self.cod_turma),
            "cod_componentes_curriculares": str_or_none(
                self.cod_componentes_curriculares
            ),
            "ano_letivo": int(self.ano_letivo),
            "cod_motivo_disponibilizacao": int_or_none(
                self.cod_motivo_disponibilizacao
            ),
            "desc_territorio_saber": strip_or_none(self.desc_territorio_saber),
            "desc_experiencia_pedagogica": strip_or_none(
                self.desc_experiencia_pedagogica
            ),
            "encerramento_atribuicao_agrupamento_atualizado": (
                bool(self.encerramento_atribuicao_agrupamento_atualizado)
                if self.encerramento_atribuicao_agrupamento_atualizado
                is not None
                else None
            ),
            "transferido_em": transferido_em,
        }
