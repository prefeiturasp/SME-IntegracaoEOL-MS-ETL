"""Servico ETL do dominio PROFESSORES_DB.

Responsabilidade:
    Ler dados do EOL (SQL Server via EOLService) e popular os models
    do app professores no banco professores_db.

    Domínios externos (DRE, Escola, ComponenteCurricular, SerieEnsino,
    TerritorioSaber, ExperienciaPedagogica, Cargo) NÃO são replicados.
    Apenas os IDs são armazenados nos models de professores.
    Descrições são resolvidas pelo Transition Gateway.

Estrategia de escrita por tabela:
    upsert incremental (bulk_create update_conflicts + hash SHA-256):
        UnidadeEducacional, TurmaEscola, Professor, Pessoa,
        SerieTurmaGrade, TurmaEscolaGradePrograma,
        CargoBaseServidor, ContratoExterno,
        AtribuicaoAula, AtribuicaoExterno,
        AgrupamentoAtribuicaoTerritorioSaber

    full-refresh (delete-all + bulk_create por lote, sem transação global):
        TurmaGradeTerritorioExperiencia (PK auto-gerada — sem chave natural)
        LotacaoServidor, CargoSobrepostoServidor,
        FuncaoAtividadeCargoServidor, LaudoMedico

Cargos de professor reconhecidos pelo EOL:
    3239, 3247, 3255, 3263, 3271, 3280, 3298, 3301,
    3310, 3336, 3344, 3840, 3859, 3867, 3874, 3875,
    3883, 3884
"""

import hashlib
import logging
from collections.abc import Callable, Iterator
from datetime import datetime
from itertools import groupby
from typing import Any

from apps.controle_auditoria.models import EtlAuditoriaLinha
from apps.core.libs.helpers import make_aware
from apps.core.libs.thread_processor import ThreadPoolProcessor
from apps.eol_connection.libs.servico_eol import EOLService
from apps.professores.dtos.model_in import (
    AtribuicaoAulaIn,
    AtribuicaoExternoIn,
    AtribuicaoTerritorioSaberIn,
    CargoBaseServidorIn,
    CargoSobrepostoServidorIn,
    ContratoExternoIn,
    FuncaoAtividadeCargoServidorIn,
    LaudoMedicoIn,
    LotacaoServidorIn,
    PessoaIn,
    ProfessorIn,
    SerieTurmaGradeIn,
    TurmaEscolaGradeProgramaIn,
    TurmaEscolaIn,
    TurmaGradeTerritorioExperienciaIn,
    UnidadeEducacionalIn,
)
from apps.professores.dtos.model_out import (
    AtribuicaoAulaOut,
    AtribuicaoExternoOut,
    CargoBaseServidorOut,
    ContratoExternoOut,
    PessoaOut,
    ProfessorOut,
    SerieTurmaGradeOut,
    TurmaEscolaGradeProgramaOut,
    TurmaEscolaOut,
    UnidadeEducacionalOut,
)
from apps.professores.models import (
    AgrupamentoAtribuicaoTerritorioSaber,
    AtribuicaoAula,
    AtribuicaoExterno,
    CargoBaseServidor,
    CargoSobrepostoServidor,
    ContratoExterno,
    FuncaoAtividadeCargoServidor,
    LaudoMedico,
    LotacaoServidor,
    Pessoa,
    Professor,
    SerieTurmaGrade,
    TurmaEscola,
    TurmaEscolaGradePrograma,
    TurmaGradeTerritorioExperiencia,
    UnidadeEducacional,
)

logger = logging.getLogger(__name__)

CARGOS_PROFESSOR = (
    3239,
    3247,
    3255,
    3263,
    3271,
    3280,
    3298,
    3301,
    3310,
    3336,
    3344,
    3840,
    3859,
    3867,
    3874,
    3875,
    3883,
    3884,
)

_PLACEHOLDERS_CARGO = ",".join(["%s"] * len(CARGOS_PROFESSOR))

# ---------------------------------------------------------------------------
# SQLs — Tabelas de suporte (estruturais para filtros de professores)
# ---------------------------------------------------------------------------

# Apenas IDs necessários para filtros: cd_unidade_educacao, codigo_dre,
# codigo_tipo_escola. Nomes/siglas resolvidos pelo Transition Gateway.
SQL_UNIDADES_EDUCACIONAIS = """
    SELECT
        ue.cd_unidade_educacao,
        ue.cd_unidade_administrativa_referencia AS cd_dre,
        ue.tp_unidade_educacao                  AS cd_tipo_escola
    FROM v_cadastro_unidade_educacao ue
"""

# Campos necessários para filtros e resultados de atribuição.
# cd_tipo_turma: obrigatório para VerificaSeEhTurmaDeProgramaAsync.
# dt_inicio_turma: retornado como DataInicioAtribuicao
# em BuscaProfessoresAsync.
# nome_turma, turno resolvidos pelo Transition Gateway (não armazenados).
SQL_TURMAS_ESCOLA = """
    SELECT
        cd_turma_escola,
        cd_escola,
        an_letivo,
        st_turma_escola,
        cd_tipo_turma,
        dt_inicio_turma,
        dt_fim_turma,
        dt_fim
    FROM turma_escola
"""

SQL_SERIE_TURMA_GRADE = """
    SELECT
        cd_serie_grade,
        cd_turma_escola,
        cd_escola,
        cd_escola_grade,
        dt_fim
    FROM serie_turma_grade
"""

SQL_TURMA_ESCOLA_GRADE_PROGRAMA = """
    SELECT
        cd_turma_escola_grade_programa,
        cd_turma_escola,
        cd_escola_grade,
        dt_fim
    FROM turma_escola_grade_programa
"""

SQL_TURMA_GRADE_TERRITORIO = """
    SELECT
        cd_serie_grade,
        cd_componente_curricular,
        cd_territorio_saber,
        cd_experiencia_pedagogica,
        dt_inicio
    FROM turma_grade_territorio_experiencia
"""

# ---------------------------------------------------------------------------
# SQLs — Dados de professores (EolConnection SQL Server)
# ---------------------------------------------------------------------------

SQL_PROFESSORES = f"""
    SELECT DISTINCT
        sc.cd_registro_funcional,
        sc.nm_pessoa,
        sc.nm_social,
        sc.cd_cpf_pessoa
    FROM v_servidor_cotic sc
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_servidor = sc.cd_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_CARGOS_BASE = f"""
    SELECT
        cbs.cd_cargo_base_servidor,
        sc.cd_registro_funcional,
        cbs.cd_cargo,
        cbs.cd_situacao_funcional,
        cbs.dt_posse,
        cbs.dt_fim_nomeacao,
        cbs.dt_cancelamento
    FROM v_cargo_base_cotic cbs
    INNER JOIN v_servidor_cotic sc ON sc.cd_servidor = cbs.cd_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_LOTACOES = """
    SELECT
        ls.cd_cargo_base_servidor,
        ls.cd_unidade_educacao,
        ls.dt_inicio,
        ls.dt_fim
    FROM lotacao_servidor ls
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = ls.cd_cargo_base_servidor
"""

SQL_CARGOS_SOBREPOSTOS = f"""
    SELECT
        css.cd_cargo_base_servidor,
        css.cd_cargo,
        css.cd_unidade_local_servico,
        css.dt_fim_cargo_sobreposto
    FROM cargo_sobreposto_servidor css
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = css.cd_cargo_base_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_FUNCOES_ATIVIDADE = f"""
    SELECT
        facs.cd_cargo_base_servidor,
        facs.cd_unidade_local_servico,
        facs.dt_fim_funcao_atividade
    FROM funcao_atividade_cargo_servidor facs
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = facs.cd_cargo_base_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_LAUDOS = f"""
    SELECT lm.cd_cargo_base_servidor
    FROM laudo_medico lm
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = lm.cd_cargo_base_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_PESSOAS = """
    SELECT
        cd_pessoa,
        cd_cpf_pessoa,
        nm_pessoa,
        nm_social
    FROM pessoa
    WHERE cd_pessoa IN (
        SELECT DISTINCT cd_pessoa
        FROM contrato_externo
        WHERE dt_cancelamento IS NULL
    )
"""

SQL_CONTRATOS_EXTERNOS = """
    SELECT
        cd_contrato_externo,
        cd_pessoa,
        cd_tipo_funcao_funcionario_externo,
        cd_unidade_educacao,
        dt_cancelamento,
        cd_motivo_desligamento_externo
    FROM contrato_externo
"""

SQL_ATRIBUICOES_AULA = f"""
    SELECT
        aa.cd_atribuicao_aula,
        aa.cd_cargo_base_servidor,
        aa.cd_unidade_educacao,
        NULL AS cd_turma_escola,
        aa.cd_turma_escola_grade_programa,
        aa.cd_grade,
        aa.cd_componente_curricular,
        aa.cd_serie_grade,
        aa.an_atribuicao,
        aa.dt_atribuicao_aula,
        aa.dt_disponibilizacao_aulas,
        aa.cd_motivo_disponibilizacao,
        aa.dt_cancelamento
    FROM atribuicao_aula aa
    INNER JOIN v_cargo_base_cotic cbs
        ON cbs.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
    WHERE cbs.cd_cargo IN ({_PLACEHOLDERS_CARGO})
"""

SQL_ATRIBUICOES_EXTERNO = """
    SELECT
        ae.cd_atribuicao_externo,
        ae.cd_contrato_externo,
        ae.cd_unidade_educacao,
        ae.cd_grade,
        ae.cd_componente_curricular,
        ae.cd_serie_grade,
        ae.cd_turma_escola_grade_programa,
        ae.an_atribuicao,
        ae.dt_atribuicao,
        ae.dt_disponibilizacao,
        ae.cd_motivo_disponibilizacao_externo,
        ae.dt_cancelamento
    FROM atribuicao_externo ae
    INNER JOIN contrato_externo ce
        ON ce.cd_contrato_externo = ae.cd_contrato_externo
    WHERE ce.dt_cancelamento IS NULL
"""


# ---------------------------------------------------------------------------
# Transformadores de linha (row → dict)
# ---------------------------------------------------------------------------


def _row_to_unidade_educacional(row: tuple) -> dict:
    return UnidadeEducacionalIn(*row).to_domain().to_dict()


def _row_to_turma_escola(row: tuple) -> dict:
    return TurmaEscolaIn(*row).to_domain().to_dict()


def _row_to_serie_turma_grade(row: tuple) -> dict:
    return SerieTurmaGradeIn(*row).to_domain().to_dict()


def _row_to_turma_escola_grade_programa(row: tuple) -> dict:
    return TurmaEscolaGradeProgramaIn(*row).to_domain().to_dict()


def _row_to_turma_grade_territorio(row: tuple) -> dict:
    return TurmaGradeTerritorioExperienciaIn(*row).to_domain().to_dict()


def _row_to_professor(row: tuple) -> dict:
    return ProfessorIn(*row).to_domain().to_dict()


def _row_to_cargo_base(row: tuple) -> dict:
    return CargoBaseServidorIn(*row).to_domain().to_dict()


def _row_to_lotacao(row: tuple) -> dict:
    return LotacaoServidorIn(*row).to_domain().to_dict()


def _row_to_cargo_sobreposto(row: tuple) -> dict:
    return CargoSobrepostoServidorIn(*row).to_domain().to_dict()


def _row_to_funcao_atividade(row: tuple) -> dict:
    return FuncaoAtividadeCargoServidorIn(*row).to_domain().to_dict()


def _row_to_laudo(row: tuple) -> dict:
    return LaudoMedicoIn(*row).to_domain().to_dict()


def _row_to_pessoa(row: tuple) -> dict:
    return PessoaIn(*row).to_domain().to_dict()


def _row_to_contrato_externo(row: tuple) -> dict:
    return ContratoExternoIn(*row).to_domain().to_dict()


def _row_to_atribuicao_aula(row: tuple) -> dict:
    return AtribuicaoAulaIn(*row).to_domain().to_dict()


def _row_to_atribuicao_externo(row: tuple) -> dict:
    return AtribuicaoExternoIn(*row).to_domain().to_dict()


# ---------------------------------------------------------------------------
# Helpers de escrita
# ---------------------------------------------------------------------------


def _full_refresh_por_lote(
    model_class: Any,
    lotes: Iterator[list[Any]],
) -> int:
    """Delete-all uma vez + bulk_create a cada lote.

    Estratégia:
        1. Remove todos os registros da tabela destino.
        2. Para cada lote recebido do EOL: bulk_create imediato.
    Não usa transação global — a tabela fica temporariamente vazia
    durante a carga, comportamento idêntico ao full-refresh original.
    """
    model_class.objects.using("professores_db").all().delete()
    total = 0
    for objs in lotes:
        if objs:
            criados = model_class.objects.using("professores_db").bulk_create(
                objs, batch_size=500
            )
            total += len(criados)
    return total


def _full_refresh(model_class: Any, objs: list[Any]) -> int:
    """Full refresh a partir de uma lista de objetos já instanciados.

    Wrapper sobre _full_refresh_por_lote para uso com listas simples.
    """
    return _full_refresh_por_lote(model_class, iter([objs]))


def _params_cargo() -> list[int]:
    """Retorna cargos de professor como parâmetros posicionais (%s)."""
    return list(CARGOS_PROFESSOR)


# ---------------------------------------------------------------------------
# Controle incremental por hash de linha
# ---------------------------------------------------------------------------

_HASH_LOOKUP_BATCH = 1000


def _calcular_hash(campos: dict[str, Any]) -> str:
    """SHA-256 dos campos relevantes para controle incremental de mudança.

    Serializa pares chave=valor em ordem alfabética e calcula o digest hex.
    """
    conteudo = "|".join(f"{k}={v!r}" for k, v in sorted(campos.items()))
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def _reinsere_se_ausente(
    model_class: Any,
    pk_name: str,
    pks: list[str],
    map_linha: dict[str, tuple[str, str, dict[str, Any]]],
    objs: list[Any],
    hashes: dict[str, str],
) -> None:
    """Força reinserção se o hash não mudou mas o registro sumiu do destino."""
    if not pks:
        return
    existentes: set[str] = set()
    for i in range(0, len(pks), _HASH_LOOKUP_BATCH):
        lote = pks[i : i + _HASH_LOOKUP_BATCH]
        existentes.update(
            str(pk)
            for pk in model_class.objects.using("professores_db")
            .filter(**{f"{pk_name}__in": lote})
            .values_list(pk_name, flat=True)
        )
    for pk_str, (id_dest, novo_h, row_dict) in map_linha.items():
        if pk_str not in existentes:
            objs.append(model_class(**row_dict))
            hashes[id_dest] = novo_h


def _upsert_incremental(
    model_class: Any,
    tabela: str,
    rows: list[dict[str, Any]],
    update_fields: list[str],
) -> int:
    """Upsert apenas registros cujo hash de linha mudou.

    Fluxo:
        1. Calcula SHA-256 dos ``update_fields`` de cada linha.
        2. Consulta ``EtlAuditoriaLinha`` para os IDs do lote.
        3. Filtra apenas linhas com hash divergente (novas ou alteradas).
        4. Grava no destino via ``bulk_create(update_conflicts=True)``.
        5. Atualiza ``EtlAuditoriaLinha`` com os novos hashes.

    Retorna:
        Número de registros efetivamente escritos no destino.
    """
    if not rows:
        return 0

    pk_name: str = model_class._meta.pk.name

    # Construir (id_destino, hash, row_dict) para cada linha
    linhas: list[tuple[str, str, dict[str, Any]]] = []
    for row_dict in rows:
        pk_str = str(row_dict[pk_name])
        id_destino = f"{tabela}:{pk_str}"
        campos_hash = {k: row_dict.get(k) for k in update_fields}
        linhas.append((id_destino, _calcular_hash(campos_hash), row_dict))

    ids_destino = [item[0] for item in linhas]
    hashes_existentes: dict[str, str] = {}
    for i in range(0, len(ids_destino), _HASH_LOOKUP_BATCH):
        lote = ids_destino[i : i + _HASH_LOOKUP_BATCH]
        hashes_existentes.update(
            EtlAuditoriaLinha.objects.filter(id_destino__in=lote).values_list(
                "id_destino", "hash_controle"
            )
        )

    objs_para_salvar: list[Any] = []
    novos_hashes: dict[str, str] = {}
    pks_hash_inalterado: list[str] = []
    map_pk_para_linha: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for id_destino, novo_hash, row_dict in linhas:
        pk_str = str(row_dict[pk_name])
        if hashes_existentes.get(id_destino) != novo_hash:
            objs_para_salvar.append(model_class(**row_dict))
            novos_hashes[id_destino] = novo_hash
        else:
            pks_hash_inalterado.append(pk_str)
            map_pk_para_linha[pk_str] = (id_destino, novo_hash, row_dict)

    # Proteção contra dessincronização: se o hash não mudou mas o registro
    # não existe mais no destino (ex: migration reset), forçar reinserção.
    _reinsere_se_ausente(
        model_class,
        pk_name,
        pks_hash_inalterado,
        map_pk_para_linha,
        objs_para_salvar,
        novos_hashes,
    )

    if not objs_para_salvar:
        return 0

    # Deduplicar por PK antes do bulk_create: ON CONFLICT DO UPDATE falha se o
    # mesmo PK aparecer mais de uma vez no mesmo lote.
    seen_pks: set[Any] = set()
    objs_dedup: list[Any] = []
    for obj in objs_para_salvar:
        pk_val = getattr(obj, pk_name)
        if pk_val not in seen_pks:
            seen_pks.add(pk_val)
            objs_dedup.append(obj)
    objs_para_salvar = objs_dedup

    model_class.objects.using("professores_db").bulk_create(
        objs_para_salvar,
        update_conflicts=True,
        unique_fields=[pk_name],
        update_fields=update_fields,
        batch_size=500,
    )

    hash_objs = [
        EtlAuditoriaLinha(id_destino=id_d, hash_controle=h)
        for id_d, h in novos_hashes.items()
    ]
    EtlAuditoriaLinha.objects.bulk_create(
        hash_objs,
        update_conflicts=True,
        unique_fields=["id_destino"],
        update_fields=["hash_controle"],
        batch_size=500,
    )

    return len(objs_para_salvar)


# ---------------------------------------------------------------------------
# Helpers — agrupamento território do saber
# ---------------------------------------------------------------------------

# Alimenta: agrupamento_atribuicao_territorio_saber
# UNION ALL: professor via RF (SME) + professor externo via CPF
SQL_AGRUPAMENTOS_TERRITORIO_SABER = """
-- SME — professor via RF
SELECT
    cc.cd_componente_curricular       AS CodigoComponenteCurricular,
    te.cd_turma_escola                AS CodigoTurma,
    te.an_letivo                      AS AnoLetivo,
    vsc.cd_registro_funcional         AS RfProfessor,
    tgt.cd_territorio_saber           AS CodigoTerritorioSaber,
    tgt.cd_experiencia_pedagogica     AS CodigoExperienciaPedagogica,
    aa.dt_atribuicao_aula             AS DataAtribuicao,
    aa.dt_disponibilizacao_aulas      AS DataDisponibilizacao,
    aa.cd_motivo_disponibilizacao     AS CodigoMotivoDisponibilizacao,
    te.dt_fim_turma                   AS DataFimTurma
FROM turma_escola te
    INNER JOIN escola esc ON te.cd_escola = esc.cd_escola
    INNER JOIN serie_turma_escola ste
        ON ste.cd_turma_escola = te.cd_turma_escola
    INNER JOIN serie_turma_grade stg
        ON stg.cd_turma_escola = ste.cd_turma_escola
        AND stg.dt_fim IS NULL
    INNER JOIN escola_grade eg ON eg.cd_escola_grade = stg.cd_escola_grade
    INNER JOIN grade g ON g.cd_grade = eg.cd_grade
    INNER JOIN grade_componente_curricular gcc ON gcc.cd_grade = g.cd_grade
    INNER JOIN componente_curricular cc
        ON cc.cd_componente_curricular = gcc.cd_componente_curricular
        AND cc.dt_cancelamento IS NULL
    INNER JOIN serie_ensino se ON se.cd_serie_ensino = g.cd_serie_ensino
    INNER JOIN turma_grade_territorio_experiencia tgt
        ON tgt.cd_serie_grade = stg.cd_serie_grade
        AND tgt.cd_componente_curricular = cc.cd_componente_curricular
    INNER JOIN tipo_experiencia_pedagogica exp
        ON exp.cd_experiencia_pedagogica = tgt.cd_experiencia_pedagogica
    INNER JOIN território_saber ter
        ON ter.cd_territorio_saber = tgt.cd_territorio_saber
    INNER JOIN atribuicao_aula aa
        ON gcc.cd_grade = aa.cd_grade
        AND gcc.cd_componente_curricular = aa.cd_componente_curricular
        AND aa.cd_serie_grade = stg.cd_serie_grade
        AND aa.dt_cancelamento IS NULL
        AND aa.an_atribuicao = te.an_letivo
        AND (aa.cd_motivo_disponibilizacao <> 26
             OR aa.cd_motivo_disponibilizacao IS NULL)
    INNER JOIN v_cargo_base_cotic vcbc
        ON vcbc.cd_cargo_base_servidor = aa.cd_cargo_base_servidor
    INNER JOIN v_servidor_cotic vsc ON vsc.cd_servidor = vcbc.cd_servidor
WHERE te.st_turma_escola IN ('O', 'A', 'C', 'E')

UNION ALL

-- Externos (CEI_INDIR=11, CRP_CONV=12, EMEFPFOM=32, EMEIPFOM=33)
SELECT
    cc.cd_componente_curricular           AS CodigoComponenteCurricular,
    te.cd_turma_escola                    AS CodigoTurma,
    te.an_letivo                          AS AnoLetivo,
    pe.cd_cpf_pessoa                      AS RfProfessor,
    tgt.cd_territorio_saber               AS CodigoTerritorioSaber,
    tgt.cd_experiencia_pedagogica         AS CodigoExperienciaPedagogica,
    ae.dt_atribuicao                      AS DataAtribuicao,
    ae.dt_disponibilizacao                AS DataDisponibilizacao,
    ae.cd_motivo_disponibilizacao_externo AS CodigoMotivoDisponibilizacao,
    te.dt_fim_turma                       AS DataFimTurma
FROM turma_escola te
    INNER JOIN escola esc ON te.cd_escola = esc.cd_escola
    INNER JOIN serie_turma_escola ste
        ON ste.cd_turma_escola = te.cd_turma_escola
    INNER JOIN serie_turma_grade stg
        ON stg.cd_turma_escola = ste.cd_turma_escola
        AND stg.dt_fim IS NULL
    INNER JOIN escola_grade eg ON eg.cd_escola_grade = stg.cd_escola_grade
    INNER JOIN grade g ON g.cd_grade = eg.cd_grade
    INNER JOIN grade_componente_curricular gcc ON gcc.cd_grade = g.cd_grade
    INNER JOIN componente_curricular cc
        ON cc.cd_componente_curricular = gcc.cd_componente_curricular
        AND cc.dt_cancelamento IS NULL
    INNER JOIN turma_grade_territorio_experiencia tgt
        ON tgt.cd_serie_grade = stg.cd_serie_grade
        AND tgt.cd_componente_curricular = cc.cd_componente_curricular
    INNER JOIN tipo_experiencia_pedagogica exp
        ON exp.cd_experiencia_pedagogica = tgt.cd_experiencia_pedagogica
    INNER JOIN território_saber ter
        ON ter.cd_territorio_saber = tgt.cd_territorio_saber
    INNER JOIN atribuicao_externo ae
        ON gcc.cd_grade = ae.cd_grade
        AND gcc.cd_componente_curricular = ae.cd_componente_curricular
        AND ae.dt_cancelamento IS NULL
        AND ae.an_atribuicao = te.an_letivo
        AND (ae.cd_motivo_disponibilizacao_externo <> 1
             OR ae.cd_motivo_disponibilizacao_externo IS NULL)
    INNER JOIN contrato_externo ce
        ON ce.cd_contrato_externo = ae.cd_contrato_externo
    INNER JOIN pessoa pe ON pe.cd_pessoa = ce.cd_pessoa
WHERE te.st_turma_escola IN ('O', 'A', 'C', 'E')
  AND esc.tp_escola IN (11, 12, 32, 33)

ORDER BY CodigoTurma, CodigoTerritorioSaber, CodigoExperienciaPedagogica,
         RfProfessor, DataAtribuicao, DataDisponibilizacao
"""

_UPDATE_FIELDS_AGRUP = [
    "dt_fim_atribuicao",
    "dt_fim_turma",
    "codigo_motivo_disponibilizacao",
    "codigos_componentes_curriculares",
]


def _cod_agrupamento_ts(
    codigo_turma: Any,
    codigo_territorio_saber: Any,
    codigo_experiencia_pedagogica: Any,
    rf_professor: Any,
    data_atribuicao: Any,
    componentes_ordenados: list[int],
) -> int:
    """Hash MD5 truncado da chave natural + componentes ordenados."""
    csv = ",".join(str(c) for c in componentes_ordenados)
    chave = (
        f"{codigo_turma}_{codigo_territorio_saber}_"
        f"{codigo_experiencia_pedagogica}_{rf_professor}_"
        f"{data_atribuicao}_{csv}"
    )
    return int(hashlib.md5(chave.encode()).hexdigest()[:15], 16)  # NOSONAR


def _chave_grupo_ts(row: AtribuicaoTerritorioSaberIn) -> tuple:
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
        row.data_disponibilizacao or datetime.min,
    )


def _agrupar_ts(
    rows: list[AtribuicaoTerritorioSaberIn],
) -> list[AgrupamentoAtribuicaoTerritorioSaber]:
    """Agrega linhas brutas em AgrupamentoAtribuicaoTerritorioSaber.

    Apenas grupos com mais de 1 componente curricular geram registro
    (definição do agrupamento: professor atribuído a múltiplos componentes
    de território do saber na mesma turma).
    """
    resultado: list[AgrupamentoAtribuicaoTerritorioSaber] = []

    for _, grupo in groupby(
        sorted(rows, key=_chave_grupo_ts), key=_chave_grupo_ts
    ):
        grupo_list = list(grupo)
        componentes = sorted(
            {int(r.codigo_componente_curricular) for r in grupo_list}
        )

        if len(componentes) <= 1:
            continue

        primeiro = grupo_list[0]
        cod_agrup = _cod_agrupamento_ts(
            primeiro.codigo_turma,
            primeiro.codigo_territorio_saber,
            primeiro.codigo_experiencia_pedagogica,
            primeiro.rf_professor,
            primeiro.data_atribuicao,
            componentes,
        )

        dt_inicio = make_aware(primeiro.data_atribuicao)
        dt_fim = make_aware(primeiro.data_disponibilizacao)
        dt_fim_turma = make_aware(primeiro.data_fim_turma)

        resultado.append(
            AgrupamentoAtribuicaoTerritorioSaber(
                codigo_agrupamento=cod_agrup,
                codigo_territorio_saber=primeiro.codigo_territorio_saber,
                codigo_experiencia_pedagogica=(
                    primeiro.codigo_experiencia_pedagogica
                ),
                dt_inicio_atribuicao=(dt_inicio.date() if dt_inicio else None),
                ano_atribuicao=dt_inicio.year if dt_inicio else None,
                dt_fim_atribuicao=dt_fim.date() if dt_fim else None,
                dt_fim_turma=dt_fim_turma.date() if dt_fim_turma else None,
                rf_professor=primeiro.rf_professor,
                codigo_turma=int(primeiro.codigo_turma),
                codigos_componentes_curriculares=",".join(
                    str(c) for c in componentes
                ),
                ano_letivo=primeiro.ano_letivo,
                codigo_motivo_disponibilizacao=(
                    primeiro.codigo_motivo_disponibilizacao
                ),
                encerramento_atribuicao_agrupamento_atualizado=None,
            )
        )

    return resultado


# ---------------------------------------------------------------------------
# Servico principal
# ---------------------------------------------------------------------------


# Tabelas que usam full-refresh (delete-all + bulk_create).
# Não suportam retomada por lote: ao reiniciar, processam do lote 1.
_TABELAS_FULL_REFRESH: frozenset[str] = frozenset(
    {
        "turma_grade_territorio_experiencia",
        "lotacao_servidor",
        "cargo_sobreposto_servidor",
        "funcao_atividade_cargo_servidor",
        "laudo_medico",
    }
)

# Ordem exata de processamento de todas as tabelas (todas as fases).
# Usada para determinar quais tabelas pular ao retomar por lote.
_ORDEM_TABELAS: tuple[str, ...] = (
    "unidade_educacional",
    "turma_escola",
    "professor",
    "pessoa",
    "serie_turma_grade",
    "turma_escola_grade_programa",
    "cargo_base_servidor",
    "contrato_externo",
    "turma_grade_territorio_experiencia",
    "lotacao_servidor",
    "cargo_sobreposto_servidor",
    "funcao_atividade_cargo_servidor",
    "laudo_medico",
    "atribuicao_aula",
    "atribuicao_externo",
    "agrupamento_atribuicao_territorio_saber",
)


class EtlProfessoresService:
    """Orquestra o ETL completo do dominio PROFESSORES_DB.

    Popula as tabelas de suporte (UnidadeEducacional, TurmaEscola, etc.)
    e as tabelas de domínio (Professor, CargoBaseServidor, AtribuicaoAula,
    etc.) — sem replicar dados de domínios externos.
    """

    def __init__(self, eol: EOLService | None = None) -> None:
        """Inicializa o serviço com instância de EOLService."""
        self.eol = eol or EOLService()
        self.ultima_fase_concluida: int = 0

    # ------------------------------------------------------------------
    # Fase 1 — Sem dependências internas
    # ------------------------------------------------------------------

    def popular_unidades_educacionais(self) -> int:
        """Popula UnidadeEducacional com IDs de DRE e tipo escola."""
        total = 0
        with ThreadPoolProcessor(
            prefixo_log="PROF:unidades_educacionais"
        ) as proc:
            for chunk in self.eol.iter_query(SQL_UNIDADES_EDUCACIONAIS):
                out_objs: list[UnidadeEducacionalOut] = proc.processar(
                    chunk,
                    lambda r: UnidadeEducacionalIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    UnidadeEducacional,
                    "unidade_educacional",
                    [o.to_dict() for o in out_objs],
                    ["codigo_dre", "codigo_tipo_escola"],
                )
        return total

    def popular_turmas_escola(self) -> int:
        """Popula TurmaEscola com campos necessários para filtros."""
        total = 0
        with ThreadPoolProcessor(prefixo_log="PROF:turma_escola") as proc:
            for chunk in self.eol.iter_query(SQL_TURMAS_ESCOLA):
                out_objs: list[TurmaEscolaOut] = proc.processar(
                    chunk,
                    lambda r: TurmaEscolaIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    TurmaEscola,
                    "turma_escola",
                    [o.to_dict() for o in out_objs],
                    [
                        "codigo_escola",
                        "ano_letivo",
                        "status",
                        "tipo_turma",
                        "dt_inicio_turma",
                        "dt_fim_turma",
                        "dt_fim",
                    ],
                )
        return total

    def popular_professores(self) -> int:
        """Popula a tabela Professor."""
        total = 0
        with ThreadPoolProcessor(prefixo_log="PROF:professor") as proc:
            for chunk in self.eol.iter_query(SQL_PROFESSORES, _params_cargo()):
                out_objs: list[ProfessorOut] = proc.processar(
                    chunk,
                    lambda r: ProfessorIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    Professor,
                    "professor",
                    [o.to_dict() for o in out_objs],
                    ["nome", "nome_social", "cpf"],
                )
        return total

    def popular_pessoas(self) -> int:
        """Popula a tabela Pessoa."""
        total = 0
        with ThreadPoolProcessor(prefixo_log="PROF:pessoa") as proc:
            for chunk in self.eol.iter_query(SQL_PESSOAS):
                out_objs: list[PessoaOut] = proc.processar(
                    chunk,
                    lambda r: PessoaIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    Pessoa,
                    "pessoa",
                    [o.to_dict() for o in out_objs],
                    ["cpf", "nome", "nome_social"],
                )
        return total

    # ------------------------------------------------------------------
    # Fase 2 — Dependem de fase 1
    # ------------------------------------------------------------------

    def popular_serie_turma_grade(self) -> int:
        """Popula a tabela SerieTurmaGrade."""
        total = 0
        with ThreadPoolProcessor(prefixo_log="PROF:serie_turma_grade") as proc:
            for chunk in self.eol.iter_query(SQL_SERIE_TURMA_GRADE):
                out_objs: list[SerieTurmaGradeOut] = proc.processar(
                    chunk,
                    lambda r: SerieTurmaGradeIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    SerieTurmaGrade,
                    "serie_turma_grade",
                    [o.to_dict() for o in out_objs],
                    [
                        "codigo_turma",
                        "codigo_escola",
                        "codigo_escola_grade",
                        "dt_fim",
                    ],
                )
        return total

    def popular_turma_escola_grade_programa(self) -> int:
        """Popula a tabela TurmaEscolaGradePrograma."""
        total = 0
        with ThreadPoolProcessor(
            prefixo_log="PROF:turma_escola_grade_programa"
        ) as proc:
            for chunk in self.eol.iter_query(SQL_TURMA_ESCOLA_GRADE_PROGRAMA):
                out_objs: list[TurmaEscolaGradeProgramaOut] = proc.processar(
                    chunk,
                    lambda r: TurmaEscolaGradeProgramaIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    TurmaEscolaGradePrograma,
                    "turma_escola_grade_programa",
                    [o.to_dict() for o in out_objs],
                    ["codigo_turma", "codigo_escola_grade", "dt_fim"],
                )
        return total

    def popular_cargos_base(self) -> int:
        """Popula a tabela CargoBaseServidor."""
        total = 0
        with ThreadPoolProcessor(
            prefixo_log="PROF:cargo_base_servidor"
        ) as proc:
            for chunk in self.eol.iter_query(SQL_CARGOS_BASE, _params_cargo()):
                out_objs: list[CargoBaseServidorOut] = proc.processar(
                    chunk,
                    lambda r: CargoBaseServidorIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    CargoBaseServidor,
                    "cargo_base_servidor",
                    [o.to_dict() for o in out_objs],
                    [
                        "professor_id",
                        "codigo_cargo",
                        "situacao_funcional",
                        "dt_posse",
                        "dt_fim_nomeacao",
                        "dt_cancelamento",
                    ],
                )
        return total

    def popular_contratos_externos(self) -> int:
        """Popula a tabela ContratoExterno."""
        total = 0
        with ThreadPoolProcessor(prefixo_log="PROF:contrato_externo") as proc:
            for chunk in self.eol.iter_query(SQL_CONTRATOS_EXTERNOS):
                out_objs: list[ContratoExternoOut] = proc.processar(
                    chunk,
                    lambda r: ContratoExternoIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    ContratoExterno,
                    "contrato_externo",
                    [o.to_dict() for o in out_objs],
                    [
                        "pessoa_id",
                        "codigo_tipo_funcao",
                        "codigo_unidade_educacao",
                        "dt_cancelamento",
                        "codigo_motivo_desligamento",
                    ],
                )
        return total

    # ------------------------------------------------------------------
    # Fase 3 — Dependem de fase 2
    # ------------------------------------------------------------------

    def popular_turma_grade_territorio_experiencia(self) -> int:
        """Full-refresh por lote — sem chave natural para upsert."""
        _dto_in = TurmaGradeTerritorioExperienciaIn
        with ThreadPoolProcessor(
            prefixo_log="PROF:turma_grade_territorio"
        ) as proc:
            return _full_refresh_por_lote(
                TurmaGradeTerritorioExperiencia,
                (
                    [
                        TurmaGradeTerritorioExperiencia(**o.to_dict())
                        for o in proc.processar(
                            chunk,
                            lambda r: _dto_in(*r).to_domain(),
                        )
                    ]
                    for chunk in self.eol.iter_query(
                        SQL_TURMA_GRADE_TERRITORIO
                    )
                ),
            )

    def popular_lotacoes(self) -> int:
        """Popula a tabela LotacaoServidor por lote."""
        with ThreadPoolProcessor(prefixo_log="PROF:lotacao_servidor") as proc:
            return _full_refresh_por_lote(
                LotacaoServidor,
                (
                    [
                        LotacaoServidor(**o.to_dict())
                        for o in proc.processar(
                            chunk,
                            lambda r: LotacaoServidorIn(*r).to_domain(),
                        )
                    ]
                    for chunk in self.eol.iter_query(SQL_LOTACOES)
                ),
            )

    def popular_cargos_sobrepostos(self) -> int:
        """Popula a tabela CargoSobrepostoServidor por lote."""
        _dto_in = CargoSobrepostoServidorIn
        with ThreadPoolProcessor(
            prefixo_log="PROF:cargo_sobreposto_servidor"
        ) as proc:
            return _full_refresh_por_lote(
                CargoSobrepostoServidor,
                (
                    [
                        CargoSobrepostoServidor(**o.to_dict())
                        for o in proc.processar(
                            chunk,
                            lambda r: _dto_in(*r).to_domain(),
                        )
                    ]
                    for chunk in self.eol.iter_query(
                        SQL_CARGOS_SOBREPOSTOS, _params_cargo()
                    )
                ),
            )

    def popular_funcoes_atividade(self) -> int:
        """Popula a tabela FuncaoAtividadeCargoServidor por lote."""
        _dto_in = FuncaoAtividadeCargoServidorIn
        with ThreadPoolProcessor(
            prefixo_log="PROF:funcao_atividade_cargo_servidor"
        ) as proc:
            return _full_refresh_por_lote(
                FuncaoAtividadeCargoServidor,
                (
                    [
                        FuncaoAtividadeCargoServidor(**o.to_dict())
                        for o in proc.processar(
                            chunk,
                            lambda r: _dto_in(*r).to_domain(),
                        )
                    ]
                    for chunk in self.eol.iter_query(
                        SQL_FUNCOES_ATIVIDADE, _params_cargo()
                    )
                ),
            )

    def popular_laudos(self) -> int:
        """Popula a tabela LaudoMedico por lote."""
        with ThreadPoolProcessor(prefixo_log="PROF:laudo_medico") as proc:
            return _full_refresh_por_lote(
                LaudoMedico,
                (
                    [
                        LaudoMedico(**o.to_dict())
                        for o in proc.processar(
                            chunk,
                            lambda r: LaudoMedicoIn(*r).to_domain(),
                        )
                    ]
                    for chunk in self.eol.iter_query(
                        SQL_LAUDOS, _params_cargo()
                    )
                ),
            )

    def popular_atribuicoes_aula(self) -> int:
        """Popula a tabela AtribuicaoAula via hash incremental.

        EOL usa cancelamento lógico (dt_cancelamento), não deleção física,
        por isso upsert incremental é seguro: registros cancelados têm o
        campo atualizado e o hash diverge, forçando a escrita.
        """
        total = 0
        with ThreadPoolProcessor(prefixo_log="PROF:atribuicao_aula") as proc:
            for chunk in self.eol.iter_query(
                SQL_ATRIBUICOES_AULA, _params_cargo()
            ):
                out_objs: list[AtribuicaoAulaOut] = proc.processar(
                    chunk,
                    lambda r: AtribuicaoAulaIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    AtribuicaoAula,
                    "atribuicao_aula",
                    [o.to_dict() for o in out_objs],
                    [
                        "cargo_base_id",
                        "codigo_unidade_educacao",
                        "codigo_turma_escola",
                        "codigo_turma_escola_grade_programa",
                        "codigo_grade",
                        "codigo_componente_curricular",
                        "codigo_serie_grade",
                        "ano_atribuicao",
                        "dt_atribuicao_aula",
                        "dt_disponibilizacao_aulas",
                        "codigo_motivo_disponibilizacao",
                        "dt_cancelamento",
                    ],
                )
        return total

    def popular_atribuicoes_externo(self) -> int:
        """Popula a tabela AtribuicaoExterno via hash incremental."""
        total = 0
        with ThreadPoolProcessor(
            prefixo_log="PROF:atribuicao_externo"
        ) as proc:
            for chunk in self.eol.iter_query(SQL_ATRIBUICOES_EXTERNO):
                out_objs: list[AtribuicaoExternoOut] = proc.processar(
                    chunk,
                    lambda r: AtribuicaoExternoIn(*r).to_domain(),
                )
                total += _upsert_incremental(
                    AtribuicaoExterno,
                    "atribuicao_externo",
                    [o.to_dict() for o in out_objs],
                    [
                        "contrato_externo_id",
                        "codigo_unidade_educacao",
                        "codigo_grade",
                        "codigo_componente_curricular",
                        "codigo_serie_grade",
                        "codigo_turma_escola_grade_programa",
                        "ano_atribuicao",
                        "dt_atribuicao",
                        "dt_disponibilizacao",
                        "codigo_motivo_disponibilizacao_externo",
                        "dt_cancelamento",
                    ],
                )
        return total

    # ------------------------------------------------------------------
    # Fase 4 — Agrupamentos território do saber
    # ------------------------------------------------------------------

    def popular_agrupamentos_territorio_saber(self) -> int:
        """Popula AgrupamentoAtribuicaoTerritorioSaber via SQL Server (EOL).

        Coleta todas as atribuições de território do saber (SME + externos),
        agrega em Python e persiste via upsert incremental.
        Apenas grupos com mais de 1 componente curricular geram registro.
        """
        rows: list[AtribuicaoTerritorioSaberIn] = []
        for chunk in self.eol.iter_query(SQL_AGRUPAMENTOS_TERRITORIO_SABER):
            for r in chunk:
                rows.append(AtribuicaoTerritorioSaberIn(*r))

        agrupamentos = _agrupar_ts(rows)

        return _upsert_incremental(
            AgrupamentoAtribuicaoTerritorioSaber,
            "agrupamento_atribuicao_territorio_saber",
            [
                {
                    "codigo_agrupamento": a.codigo_agrupamento,
                    "codigo_territorio_saber": a.codigo_territorio_saber,
                    "codigo_experiencia_pedagogica": (
                        a.codigo_experiencia_pedagogica
                    ),
                    "dt_inicio_atribuicao": a.dt_inicio_atribuicao,
                    "ano_atribuicao": a.ano_atribuicao,
                    "dt_fim_atribuicao": a.dt_fim_atribuicao,
                    "dt_fim_turma": a.dt_fim_turma,
                    "rf_professor": a.rf_professor,
                    "codigo_turma": a.codigo_turma,
                    "codigos_componentes_curriculares": (
                        a.codigos_componentes_curriculares
                    ),
                    "ano_letivo": a.ano_letivo,
                    "codigo_motivo_disponibilizacao": (
                        a.codigo_motivo_disponibilizacao
                    ),
                    "encerramento_atribuicao_agrupamento_atualizado": (
                        a.encerramento_atribuicao_agrupamento_atualizado
                    ),
                }
                for a in agrupamentos
            ],
            _UPDATE_FIELDS_AGRUP,
        )

    # ------------------------------------------------------------------
    # Fases de execução
    # ------------------------------------------------------------------

    def _fase_1(
        self,
        executar_tabela: Callable[[str, Callable[[], int]], None],
    ) -> None:
        """Fase 1 — tabelas sem dependências internas."""
        logger.info("[ETL PROF] === Fase 1: Suporte e Professores ===")
        executar_tabela(
            "unidade_educacional", self.popular_unidades_educacionais
        )
        executar_tabela("turma_escola", self.popular_turmas_escola)
        executar_tabela("professor", self.popular_professores)
        executar_tabela("pessoa", self.popular_pessoas)
        self.ultima_fase_concluida = 1
        logger.info("[ETL PROF] Fase 1 concluída.")

    def _fase_2(
        self,
        executar_tabela: Callable[[str, Callable[[], int]], None],
    ) -> None:
        """Fase 2 — vínculos cargo/contrato (dependem da fase 1)."""
        logger.info("[ETL PROF] === Fase 2: Vínculos ===")
        executar_tabela("serie_turma_grade", self.popular_serie_turma_grade)
        executar_tabela(
            "turma_escola_grade_programa",
            self.popular_turma_escola_grade_programa,
        )
        executar_tabela("cargo_base_servidor", self.popular_cargos_base)
        executar_tabela("contrato_externo", self.popular_contratos_externos)
        self.ultima_fase_concluida = 2
        logger.info("[ETL PROF] Fase 2 concluída.")

    def _fase_3(
        self,
        executar_tabela: Callable[[str, Callable[[], int]], None],
    ) -> None:
        """Fase 3 — atribuições e bloqueios (dependem da fase 2)."""
        logger.info("[ETL PROF] === Fase 3: Atribuições e Bloqueios ===")
        executar_tabela(
            "turma_grade_territorio_experiencia",
            self.popular_turma_grade_territorio_experiencia,
        )
        executar_tabela("lotacao_servidor", self.popular_lotacoes)
        executar_tabela(
            "cargo_sobreposto_servidor", self.popular_cargos_sobrepostos
        )
        executar_tabela(
            "funcao_atividade_cargo_servidor",
            self.popular_funcoes_atividade,
        )
        executar_tabela("laudo_medico", self.popular_laudos)
        executar_tabela("atribuicao_aula", self.popular_atribuicoes_aula)
        executar_tabela("atribuicao_externo", self.popular_atribuicoes_externo)
        self.ultima_fase_concluida = 3
        logger.info("[ETL PROF] Fase 3 concluída.")

    # ------------------------------------------------------------------
    # Execucao completa na ordem correta
    # ------------------------------------------------------------------

    def _iter_lotes(
        self,
        sql: str,
        parametros: list | dict | None,
        original: Callable,
        offset: int,
        nome: str,
        lote_counter: list[int],
        on_lote: Callable[[str, int], None] | None,
    ) -> Iterator[list[tuple[Any, ...]]]:
        """Itera chunks do EOL aplicando offset e disparando on_lote."""
        for i, chunk in enumerate(original(sql, parametros)):
            if i < offset:
                continue
            lote_counter[0] += 1
            yield chunk
            if on_lote is not None:
                on_lote(nome, lote_counter[0])

    def executar(
        self,
        fase_inicial: int = 1,
        pular_ate: str | None = None,
        lote_inicial: int = 0,
        on_lote: Callable[[str, int], None] | None = None,
        on_tabela_concluida: Callable[[str, int], None] | None = None,
    ) -> dict[str, int]:
        """Executa ETL do dominio PROFESSORES_DB a partir de ``fase_inicial``.

        Args:
            fase_inicial: Fase de início (1–4). Use > 1 para retomar após
                falha.
                - 1: Tabelas sem dependências (UEs, turmas, professores)
                - 2: Vínculos cargo/contrato (dependem da fase 1)
                - 3: Atribuições e bloqueios (dependem da fase 2)
                - 4: Agrupamentos território do saber
            pular_ate: Nome da última tabela completamente concluída.
                Todas as tabelas até ela (inclusive) são puladas.
            lote_inicial: Número de lotes já processados na tabela
                imediatamente após ``pular_ate``. Esses lotes são
                descartados (lidos do cursor mas não escritos).
                Ignorado para tabelas full-refresh.
            on_lote: Callback chamado após cada lote processado com
                assinatura ``(nome_tabela, numero_lote)``. Usado para
                salvar checkpoints por lote.
            on_tabela_concluida: Callback chamado após cada tabela
                concluir, com assinatura ``(nome_tabela, linhas)``.

        Retorna:
            Dict com contagem de registros *alterados* escritos por tabela.
            Registros sem mudança de hash não são contabilizados.
        """
        r: dict[str, int] = {}
        log = logger.info

        log("[ETL PROF] Iniciando carga a partir da fase %d...", fase_inicial)

        # pular_ate aplica-se só à fase inicial;
        # fases seguintes rodam completas.
        _pular = pular_ate
        # lote_inicial é consumido uma única vez,
        # na primeira tabela processada.
        _li = [lote_inicial]

        original_iter_query = self.eol.iter_query

        def _executar_tabela(nome: str, metodo: Callable[[], int]) -> None:
            """Executa tabela, pulando se ainda no intervalo a pular.

            Tabelas são puladas enquanto ``_pular`` não for None.
            Quando ``nome == _pular``, essa também é pulada (última já
            concluída) e ``_pular`` é zerado para as próximas processarem.
            """
            nonlocal _pular
            if _pular is not None:
                if _pular == nome:
                    _pular = None
                    _li[0] = 0
                log("[ETL PROF] Pulando %s (já concluída).", nome)
                return

            # Lote inicial só aplicável a tabelas upsert (full-refresh
            # precisam reprocessar tudo para manter consistência).
            li = 0 if nome in _TABELAS_FULL_REFRESH else _li[0]
            _li[0] = 0

            if li:
                log(
                    "[ETL PROF] %s: retomando do lote %d.",
                    nome,
                    li + 1,
                )

            # Substitui iter_query temporariamente para rastrear lotes
            # e aplicar o offset sem modificar os métodos popular_*.
            _lote_counter = [li]

            def _iter_rastreavel(
                sql: str,
                parametros: list | dict | None = None,
            ) -> Iterator[list[tuple[Any, ...]]]:
                return self._iter_lotes(
                    sql,
                    parametros,
                    original_iter_query,
                    li,
                    nome,
                    _lote_counter,
                    on_lote,
                )

            self.eol.iter_query = _iter_rastreavel  # type: ignore[method-assign]
            try:
                r[nome] = metodo()
            finally:
                self.eol.iter_query = original_iter_query  # type: ignore[method-assign]

            log("[ETL PROF] %s: %d", nome, r[nome])
            if on_tabela_concluida is not None:
                on_tabela_concluida(nome, r[nome])

        if fase_inicial <= 1:
            self._fase_1(_executar_tabela)
            _pular = None  # fases seguintes rodam completas

        if fase_inicial <= 2:
            self._fase_2(_executar_tabela)
            _pular = None

        if fase_inicial <= 3:
            self._fase_3(_executar_tabela)

        # ------------------------------------------------------------------
        # Fase 4 — Agrupamentos território do saber
        # ------------------------------------------------------------------
        if fase_inicial <= 4:
            log("[ETL PROF] === Fase 4: Agrupamentos Território do Saber ===")
            _executar_tabela(
                "agrupamento_atribuicao_territorio_saber",
                self.popular_agrupamentos_territorio_saber,
            )
            self.ultima_fase_concluida = 4
            log("[ETL PROF] Fase 4 concluída.")

        total = sum(r.values())
        log(
            "[ETL PROF] Concluído. Linhas alteradas: %d (fases %d–4).",
            total,
            fase_inicial,
        )
        return r
