"""DTOs de entrada para o domínio Pedagógico (dados extraídos do EOL)."""

from dataclasses import dataclass
from typing import Any

from apps.core.libs.helpers import make_aware, strip_str


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
class ComponenteTurmaIn:
    """Linha de SQL_COMPONENTE_TURMA — estrutura turma × componente sem professor.

    Ordem das colunas deve corresponder exatamente ao SELECT de SQL_COMPONENTE_TURMA.
    planejamento_regencia não vem do SQL — é calculado no transform via índice A3.
    """

    turma_codigo: Any
    componente_codigo: Any
    descricao: Any
    regencia: Any
    territorio_saber: Any
    codigo_componente_territorio_saber: Any
    codigo_componente_curricular_pai: Any
    tipo_escola: Any
    turno_turma: Any
    ano_turma: Any
    codigo_serie_ensino: Any
    ano_letivo: Any

    def to_domain(self, transferido_em: Any, planejamento_regencia: bool = False) -> dict:
        return {
            "turma_codigo": str(self.turma_codigo) if self.turma_codigo is not None else None,
            "componente_codigo": int(self.componente_codigo),
            "descricao": strip_str(self.descricao),
            "regencia": bool(self.regencia),
            "planejamento_regencia": planejamento_regencia,
            "territorio_saber": bool(self.territorio_saber),
            "codigo_componente_territorio_saber": (
                int(self.codigo_componente_territorio_saber)
                if self.codigo_componente_territorio_saber is not None else None
            ),
            "codigo_componente_curricular_pai": (
                int(self.codigo_componente_curricular_pai)
                if self.codigo_componente_curricular_pai is not None else None
            ),
            "tipo_escola": str(self.tipo_escola) if self.tipo_escola is not None else None,
            "turno_turma": int(self.turno_turma) if self.turno_turma is not None else None,
            "ano_turma": str(self.ano_turma) if self.ano_turma is not None else None,
            "codigo_serie_ensino": (
                int(self.codigo_serie_ensino)
                if self.codigo_serie_ensino is not None
                else None
            ),
            "ano_letivo": int(self.ano_letivo),
            "transferido_em": transferido_em,
        }


@dataclass
class AtribuicaoComponenteIn:
    """Linha para AtribuicaoComponente (L2) — professor × turma × componente."""

    turma_codigo: Any
    componente_codigo: Any
    professor: Any
    atribuicao_externa: bool
    ano_letivo: Any

    def to_domain(self, transferido_em: Any) -> dict:
        return {
            "turma_codigo": str(self.turma_codigo) if self.turma_codigo is not None else None,
            "componente_codigo": int(self.componente_codigo),
            "professor": str(self.professor) if self.professor is not None else None,
            "atribuicao_externa": self.atribuicao_externa,
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
    modalidade: Any
    codigo_modalidade: Any
    codigo_tipo_programa: Any
    codigo_modalidade_etapa: Any
    semestre: Any
    ensino_especial: Any

    def to_domain(self, transferido_em: Any) -> dict:
        return {
            "codigo": int(self.codigo),
            "ano_letivo": int(self.ano_letivo),
            "ano": str(self.ano) if self.ano is not None else None,
            "tipo_turma": int(self.tipo_turma),
            "nome_turma": strip_str(self.nome_turma),
            "duracao_turno": (
                int(self.duracao_turno)
                if self.duracao_turno is not None
                else None
            ),
            "tipo_turno": (
                int(self.tipo_turno) if self.tipo_turno is not None else None
            ),
            "data_inicio_turma": (
                make_aware(self.data_inicio_turma)
                if self.data_inicio_turma
                else None
            ),
            "data_fim": (make_aware(self.data_fim) if self.data_fim else None),
            "extinta": bool(self.extinta),
            "situacao": str(self.situacao) if self.situacao else None,
            "ue_codigo": str(self.ue_codigo) if self.ue_codigo else None,
            "data_atualizacao": (
                make_aware(self.data_atualizacao)
                if self.data_atualizacao
                else None
            ),
            "data_status_turma_escola": (
                make_aware(self.data_status_turma_escola)
                if self.data_status_turma_escola
                else None
            ),
            "serie_ensino": (
                strip_str(self.serie_ensino) if self.serie_ensino else None
            ),
            "modalidade": (
                strip_str(self.modalidade) if self.modalidade else None
            ),
            "codigo_modalidade": (
                int(self.codigo_modalidade)
                if self.codigo_modalidade is not None
                else None
            ),
            "codigo_tipo_programa": (
                int(self.codigo_tipo_programa)
                if self.codigo_tipo_programa is not None
                else None
            ),
            "codigo_modalidade_etapa": (
                int(self.codigo_modalidade_etapa)
                if self.codigo_modalidade_etapa is not None
                else None
            ),
            "semestre": (
                int(self.semestre) if self.semestre is not None else 0
            ),
            "ensino_especial": bool(self.ensino_especial),
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
