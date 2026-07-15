"""Lógica de agrupamento de atribuições de Território do Saber.

Agrupa componentes curriculares de território por
(turma, território, experiência, professor, data_atribuição,
data_disponibilização) e reutiliza IDs já persistidos em
AgrupamentoAtribuicaoTerritorioSaber, seguindo a mesma lógica
do legado C# (chave exata → chave histórica → novo sequencial).
"""

from collections.abc import Iterable
from datetime import date, datetime
from itertools import groupby
from typing import Any

from django.db.models import Max

from apps.core.libs.helpers import make_aware
from apps.pedagogico.dtos.model_in import AtribuicaoTerritorioSaberIn
from apps.pedagogico.models import (
    AgrupamentoAtribuicaoTerritorioSaber,
    ComponenteCurricularAgrupamento,
)

AgrupamentoExatoKey = tuple[str, int, int, str, Any, str]
AgrupamentoHistoricoKey = tuple[str, int, int, str]

_AGRUPAMENTO_ID_INICIAL = 800_000


def _normalizar_data_atribuicao(data_atribuicao: Any) -> Any:
    if hasattr(data_atribuicao, "date"):
        return data_atribuicao.date()
    return data_atribuicao


def _chave_agrupamento_exato(
    codigo_turma: Any,
    codigo_territorio_saber: Any,
    codigo_experiencia_pedagogica: Any,
    rf_professor: Any,
    data_atribuicao: Any,
    componentes_csv: str,
) -> AgrupamentoExatoKey:
    return (
        str(codigo_turma),
        int(codigo_territorio_saber),
        (
            int(codigo_experiencia_pedagogica)
            if codigo_experiencia_pedagogica is not None
            else -1
        ),
        str(rf_professor) if rf_professor is not None else "",
        _normalizar_data_atribuicao(data_atribuicao),
        componentes_csv,
    )


def _chave_agrupamento_historico(
    codigo_turma: Any,
    codigo_territorio_saber: Any,
    codigo_experiencia_pedagogica: Any,
    componentes_csv: str,
) -> AgrupamentoHistoricoKey:
    return (
        str(codigo_turma),
        int(codigo_territorio_saber),
        (
            int(codigo_experiencia_pedagogica)
            if codigo_experiencia_pedagogica is not None
            else -1
        ),
        componentes_csv,
    )


def montar_indices_agrupamentos_existentes(
    db_alias: str,
) -> tuple[
    dict[AgrupamentoExatoKey, int],
    dict[AgrupamentoHistoricoKey, int],
    int,
]:
    """Carrega índices de agrupamentos existentes e o maior ID gerado."""
    exatos: dict[AgrupamentoExatoKey, int] = {}
    historicos: dict[AgrupamentoHistoricoKey, int] = {}
    manager = AgrupamentoAtribuicaoTerritorioSaber.objects.using(db_alias)
    maior_id = (
        manager.aggregate(maior_id=Max("cod_agrupamento"))["maior_id"]
        or _AGRUPAMENTO_ID_INICIAL
    )

    queryset = manager.values_list(
        "cod_agrupamento",
        "cod_turma",
        "cod_territorio_saber",
        "cod_experiencia_pedagogica",
        "rf_professor",
        "dt_inicio_atribuicao",
        "cod_componentes_curriculares",
    )
    for (
        cod_agrupamento,
        cod_turma,
        cod_territorio_saber,
        cod_experiencia_pedagogica,
        rf_professor,
        dt_inicio_atribuicao,
        cod_componentes_curriculares,
    ) in queryset.iterator():
        componentes_csv = cod_componentes_curriculares or ""
        chave_exata = _chave_agrupamento_exato(
            cod_turma,
            cod_territorio_saber,
            cod_experiencia_pedagogica,
            rf_professor,
            dt_inicio_atribuicao,
            componentes_csv,
        )
        chave_historica = _chave_agrupamento_historico(
            cod_turma,
            cod_territorio_saber,
            cod_experiencia_pedagogica,
            componentes_csv,
        )
        exatos[chave_exata] = int(cod_agrupamento)
        historicos.setdefault(chave_historica, int(cod_agrupamento))

    return exatos, historicos, maior_id


def resolver_cod_agrupamento(
    codigo_turma: Any,
    codigo_territorio_saber: Any,
    codigo_experiencia_pedagogica: Any,
    rf_professor: Any,
    data_atribuicao: Any,
    componentes_ordenados: list[int],
    agrupamentos_exatos: dict[AgrupamentoExatoKey, int],
    agrupamentos_historicos: dict[AgrupamentoHistoricoKey, int],
    ultimo_id_gerado: int,
) -> tuple[int, int]:
    """Resolve o cod_agrupamento compatível com a regra do serviço C#."""
    componentes_csv = ",".join(str(c) for c in componentes_ordenados)
    chave_exata = _chave_agrupamento_exato(
        codigo_turma,
        codigo_territorio_saber,
        codigo_experiencia_pedagogica,
        rf_professor,
        data_atribuicao,
        componentes_csv,
    )
    if chave_exata in agrupamentos_exatos:
        return agrupamentos_exatos[chave_exata], ultimo_id_gerado

    chave_historica = _chave_agrupamento_historico(
        codigo_turma,
        codigo_territorio_saber,
        codigo_experiencia_pedagogica,
        componentes_csv,
    )
    if chave_historica in agrupamentos_historicos:
        cod_agrupamento = agrupamentos_historicos[chave_historica]
    else:
        cod_agrupamento = max(
            ultimo_id_gerado + 1,
            _AGRUPAMENTO_ID_INICIAL + 1,
        )
        ultimo_id_gerado = cod_agrupamento

    agrupamentos_exatos[chave_exata] = cod_agrupamento
    agrupamentos_historicos.setdefault(chave_historica, cod_agrupamento)
    return cod_agrupamento, ultimo_id_gerado


def chave_grupo_atribuicao(row: AtribuicaoTerritorioSaberIn) -> tuple:
    """Retorna a chave de agrupamento normalizada para uma atribuição."""
    return (
        str(row.codigo_turma),
        int(row.codigo_territorio_saber),
        (
            int(row.codigo_experiencia_pedagogica)
            if row.codigo_experiencia_pedagogica is not None
            else -1
        ),
        str(row.rf_professor) if row.rf_professor is not None else "",
        row.data_atribuicao or datetime.min,
        (
            row.data_disponibilizacao.date()
            if row.data_disponibilizacao
            else date.min
        ),
    )


def chave_agrupamento_persistido(
    agrupamento: AgrupamentoAtribuicaoTerritorioSaber,
) -> tuple:
    """Retorna a chave exata persistida para deduplicação/upsert."""
    return (
        str(agrupamento.cod_turma),
        int(agrupamento.cod_territorio_saber),
        (
            int(agrupamento.cod_experiencia_pedagogica)
            if agrupamento.cod_experiencia_pedagogica is not None
            else -1
        ),
        (
            str(agrupamento.rf_professor)
            if agrupamento.rf_professor is not None
            else ""
        ),
        _normalizar_data_atribuicao(agrupamento.dt_inicio_atribuicao),
        agrupamento.cod_componentes_curriculares or "",
    )


def agrupar_atribuicoes_territorio_saber(
    rows: list[AtribuicaoTerritorioSaberIn],
    transferido_em: Any,
    agrupamentos_exatos: dict[AgrupamentoExatoKey, int] | None = None,
    agrupamentos_historicos: dict[AgrupamentoHistoricoKey, int] | None = None,
    ultimo_id_gerado: int = _AGRUPAMENTO_ID_INICIAL,
) -> tuple[
    list[AgrupamentoAtribuicaoTerritorioSaber],
    list[ComponenteCurricularAgrupamento],
]:
    """Agrega atribuições em grupos e retorna agrupamentos e itens."""
    agrupamentos: list[AgrupamentoAtribuicaoTerritorioSaber] = []
    itens: list[ComponenteCurricularAgrupamento] = []
    agrupamentos_exatos = agrupamentos_exatos or {}
    agrupamentos_historicos = agrupamentos_historicos or {}

    grupos: Iterable[tuple[tuple, Iterable[AtribuicaoTerritorioSaberIn]]] = (
        groupby(
            sorted(rows, key=chave_grupo_atribuicao),
            key=chave_grupo_atribuicao,
        )
    )
    for _, grupo in grupos:
        grupo_list = list(grupo)
        componentes = sorted(
            {int(r.codigo_componente_curricular) for r in grupo_list}
        )
        if len(componentes) <= 1:
            continue

        primeiro = grupo_list[0]
        cod_agrupamento, ultimo_id_gerado = resolver_cod_agrupamento(
            primeiro.codigo_turma,
            primeiro.codigo_territorio_saber,
            primeiro.codigo_experiencia_pedagogica,
            primeiro.rf_professor,
            primeiro.data_atribuicao,
            componentes,
            agrupamentos_exatos,
            agrupamentos_historicos,
            ultimo_id_gerado,
        )

        dt_inicio = (
            make_aware(primeiro.data_atribuicao)
            if primeiro.data_atribuicao
            else None
        )
        dt_fim_raw = max(
            (
                row.data_disponibilizacao
                for row in grupo_list
                if row.data_disponibilizacao
            ),
            default=None,
        )
        dt_fim = make_aware(dt_fim_raw) if dt_fim_raw else None
        dt_fim_turma = (
            make_aware(primeiro.data_fim_turma)
            if primeiro.data_fim_turma
            else None
        )

        agrupamentos.append(
            AgrupamentoAtribuicaoTerritorioSaber(
                cod_agrupamento=cod_agrupamento,
                cod_territorio_saber=primeiro.codigo_territorio_saber,
                cod_experiencia_pedagogica=(
                    primeiro.codigo_experiencia_pedagogica
                ),
                dt_inicio_atribuicao=dt_inicio,
                ano_atribuicao=dt_inicio.year if dt_inicio else None,
                dt_fim_atribuicao=dt_fim,
                dt_fim_turma=dt_fim_turma,
                rf_professor=primeiro.rf_professor,
                cod_turma=str(primeiro.codigo_turma),
                cod_componentes_curriculares=",".join(
                    str(codigo) for codigo in componentes
                ),
                ano_letivo=primeiro.ano_letivo,
                cod_motivo_disponibilizacao=(
                    primeiro.codigo_motivo_disponibilizacao
                ),
                desc_territorio_saber=primeiro.descricao_territorio_saber,
                desc_experiencia_pedagogica=(
                    primeiro.descricao_experiencia_pedagogica
                ),
                encerramento_atribuicao_agrupamento_atualizado=None,
                transferido_em=transferido_em,
            )
        )

        for codigo in componentes:
            itens.append(
                ComponenteCurricularAgrupamento(
                    componente_codigo=codigo,
                    turma_codigo=str(primeiro.codigo_turma),
                    codigo_agrupamento=cod_agrupamento,
                    rf_professor=primeiro.rf_professor,
                    ano_letivo=primeiro.ano_letivo,
                    transferido_em=transferido_em,
                )
            )

    agrupamentos = list(
        {
            chave_agrupamento_persistido(item): item for item in agrupamentos
        }.values()
    )
    itens = list(
        {
            (
                item.componente_codigo,
                item.turma_codigo,
                item.codigo_agrupamento,
                item.rf_professor,
            ): item
            for item in itens
        }.values()
    )
    return agrupamentos, itens
