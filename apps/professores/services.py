"""Servico ETL do dominio PROFESSORES_DB.

Responsabilidade:
    Ler dados do EOL (SQL Server via EOLService) e popular os models
    do app professores no banco professores_db.

    Domínios externos (DRE, Escola, ComponenteCurricular, SerieEnsino,
    TerritorioSaber, ExperienciaPedagogica, Cargo) NÃO são replicados.
    Apenas os IDs são armazenados nos models de professores.
    Descrições são resolvidas pelo Transition Gateway.

Estrategia de escrita por tabela:
    upsert (bulk_create update_conflicts):
        UnidadeEducacional, TurmaEscola, SerieTurmaGrade,
        TurmaEscolaGradePrograma,
        Professor, Pessoa,
        CargoBaseServidor, ContratoExterno,
        AtribuicaoAula, AtribuicaoExterno

    full-refresh (delete + bulk_create em transação):
        TurmaGradeTerritorioExperiencia (PK auto-gerada — sem chave natural)
        LotacaoServidor, CargoSobrepostoServidor,
        FuncaoAtividadeCargoServidor, LaudoMedico

    pendente (ApiEolConnection — PostgreSQL separado):
        AgrupamentoAtribuicaoTerritorioSaber

Cargos de professor reconhecidos pelo EOL:
    3239, 3247, 3255, 3263, 3271, 3280, 3298, 3301,
    3336, 3344, 3840, 3859, 3867, 3874, 3883, 3884
"""

import hashlib
import logging
from collections.abc import Callable, Iterator
from typing import Any

from apps.controle_auditoria.models import EtlAuditoriaLinha
from apps.eol_connection.libs.servico_eol import EOLService
from apps.professores.models import (
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
# Transformadores: tupla EOL → dict de campos do model
# ---------------------------------------------------------------------------


def _row_to_unidade_educacional(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_ue": str(row[0]).strip(),
        "codigo_dre": str(row[1]).strip() if row[1] else None,
        "codigo_tipo_escola": row[2] or None,
    }


def _row_to_turma_escola(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_turma": row[0],
        "codigo_escola": str(row[1]).strip(),
        "ano_letivo": row[2],
        "status": row[3] or "",
        "tipo_turma": row[4],
        "dt_inicio_turma": row[5],
        "dt_fim_turma": row[6],
        "dt_fim": row[7],
    }


def _row_to_serie_turma_grade(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_serie_grade": row[0],
        "codigo_turma": row[1],
        "codigo_escola": str(row[2]).strip(),
        "codigo_escola_grade": row[3],
        "dt_fim": row[4],
    }


def _row_to_turma_escola_grade_programa(
    row: tuple[Any, ...]
) -> dict[str, Any]:
    return {
        "codigo": row[0],
        "codigo_turma": row[1],
        "codigo_escola_grade": row[2],
        "dt_fim": row[3],
    }


def _row_to_turma_grade_territorio(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_serie_grade": row[0],
        "codigo_componente_curricular": row[1],
        "codigo_territorio_saber": row[2],
        "codigo_experiencia_pedagogica": row[3],
        "dt_inicio": row[4],
    }


def _row_to_professor(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_rf": str(row[0]).strip(),
        "nome": row[1] or "",
        "nome_social": row[2] or None,
        "cpf": str(row[3]).strip() if row[3] else None,
    }


def _row_to_cargo_base(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "professor_id": str(row[1]).strip(),
        "codigo_cargo": row[2],
        "situacao_funcional": row[3],
        "dt_posse": row[4],
        "dt_fim_nomeacao": row[5],
        "dt_cancelamento": row[6],
    }


def _row_to_lotacao(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "cargo_base_id": row[0],
        "codigo_unidade_educacao": str(row[1]).strip(),
        "dt_inicio": row[2],
        "dt_fim": row[3],
    }


def _row_to_cargo_sobreposto(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "cargo_base_id": row[0],
        "codigo_cargo": row[1],
        "codigo_unidade_local_servico": str(row[2]).strip(),
        "dt_fim_cargo_sobreposto": row[3],
    }


def _row_to_funcao_atividade(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "cargo_base_id": row[0],
        "codigo_unidade_local_servico": str(row[1]).strip(),
        "dt_fim_funcao_atividade": row[2],
    }


def _row_to_laudo(row: tuple[Any, ...]) -> dict[str, Any]:
    return {"cargo_base_id": row[0]}


def _row_to_pessoa(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_pessoa": row[0],
        "cpf": str(row[1]).strip(),
        "nome": row[2] or "",
        "nome_social": row[3] or None,
    }


def _row_to_contrato_externo(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "codigo_contrato": row[0],
        "pessoa_id": row[1],
        "codigo_tipo_funcao": row[2],
        "codigo_unidade_educacao": str(row[3]).strip(),
        "dt_cancelamento": row[4],
        "codigo_motivo_desligamento": row[5],
    }


def _row_to_atribuicao_aula(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "cargo_base_id": row[1],
        "codigo_unidade_educacao": str(row[2]).strip(),
        "codigo_turma_escola": row[3],
        "codigo_turma_escola_grade_programa": row[4],
        "codigo_grade": row[5],
        "codigo_componente_curricular": row[6],
        "codigo_serie_grade": row[7],
        "ano_atribuicao": row[8],
        "dt_atribuicao_aula": row[9],
        "dt_disponibilizacao_aulas": row[10],
        "codigo_motivo_disponibilizacao": row[11],
        "dt_cancelamento": row[12],
    }


def _row_to_atribuicao_externo(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "contrato_externo_id": row[1],
        "codigo_unidade_educacao": str(row[2]).strip(),
        "codigo_grade": row[3],
        "codigo_componente_curricular": row[4],
        "codigo_serie_grade": row[5],
        "codigo_turma_escola_grade_programa": row[6],
        "ano_atribuicao": row[7],
        "dt_atribuicao": row[8],
        "dt_disponibilizacao": row[9],
        "codigo_motivo_disponibilizacao_externo": row[10],
        "dt_cancelamento": row[11],
    }


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
        for chunk in self.eol.iter_query(SQL_UNIDADES_EDUCACIONAIS):
            total += _upsert_incremental(
                UnidadeEducacional,
                "unidade_educacional",
                [_row_to_unidade_educacional(r) for r in chunk],
                ["codigo_dre", "codigo_tipo_escola"],
            )
        return total

    def popular_turmas_escola(self) -> int:
        """Popula TurmaEscola com campos necessários para filtros."""
        total = 0
        for chunk in self.eol.iter_query(SQL_TURMAS_ESCOLA):
            total += _upsert_incremental(
                TurmaEscola,
                "turma_escola",
                [_row_to_turma_escola(r) for r in chunk],
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
        for chunk in self.eol.iter_query(SQL_PROFESSORES, _params_cargo()):
            total += _upsert_incremental(
                Professor,
                "professor",
                [_row_to_professor(r) for r in chunk],
                ["nome", "nome_social", "cpf"],
            )
        return total

    def popular_pessoas(self) -> int:
        """Popula a tabela Pessoa."""
        total = 0
        for chunk in self.eol.iter_query(SQL_PESSOAS):
            total += _upsert_incremental(
                Pessoa,
                "pessoa",
                [_row_to_pessoa(r) for r in chunk],
                ["cpf", "nome", "nome_social"],
            )
        return total

    # ------------------------------------------------------------------
    # Fase 2 — Dependem de fase 1
    # ------------------------------------------------------------------

    def popular_serie_turma_grade(self) -> int:
        """Popula a tabela SerieTurmaGrade."""
        total = 0
        for chunk in self.eol.iter_query(SQL_SERIE_TURMA_GRADE):
            total += _upsert_incremental(
                SerieTurmaGrade,
                "serie_turma_grade",
                [_row_to_serie_turma_grade(r) for r in chunk],
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
        for chunk in self.eol.iter_query(SQL_TURMA_ESCOLA_GRADE_PROGRAMA):
            total += _upsert_incremental(
                TurmaEscolaGradePrograma,
                "turma_escola_grade_programa",
                [_row_to_turma_escola_grade_programa(r) for r in chunk],
                ["codigo_turma", "codigo_escola_grade", "dt_fim"],
            )
        return total

    def popular_cargos_base(self) -> int:
        """Popula a tabela CargoBaseServidor."""
        total = 0
        for chunk in self.eol.iter_query(SQL_CARGOS_BASE, _params_cargo()):
            total += _upsert_incremental(
                CargoBaseServidor,
                "cargo_base_servidor",
                [_row_to_cargo_base(r) for r in chunk],
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
        for chunk in self.eol.iter_query(SQL_CONTRATOS_EXTERNOS):
            total += _upsert_incremental(
                ContratoExterno,
                "contrato_externo",
                [_row_to_contrato_externo(r) for r in chunk],
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
        return _full_refresh_por_lote(
            TurmaGradeTerritorioExperiencia,
            (
                [
                    TurmaGradeTerritorioExperiencia(
                        **_row_to_turma_grade_territorio(r)
                    )
                    for r in chunk
                ]
                for chunk in self.eol.iter_query(SQL_TURMA_GRADE_TERRITORIO)
            ),
        )

    def popular_lotacoes(self) -> int:
        """Popula a tabela LotacaoServidor por lote."""
        return _full_refresh_por_lote(
            LotacaoServidor,
            (
                [LotacaoServidor(**_row_to_lotacao(r)) for r in chunk]
                for chunk in self.eol.iter_query(SQL_LOTACOES)
            ),
        )

    def popular_cargos_sobrepostos(self) -> int:
        """Popula a tabela CargoSobrepostoServidor por lote."""
        return _full_refresh_por_lote(
            CargoSobrepostoServidor,
            (
                [
                    CargoSobrepostoServidor(**_row_to_cargo_sobreposto(r))
                    for r in chunk
                ]
                for chunk in self.eol.iter_query(
                    SQL_CARGOS_SOBREPOSTOS, _params_cargo()
                )
            ),
        )

    def popular_funcoes_atividade(self) -> int:
        """Popula a tabela FuncaoAtividadeCargoServidor por lote."""
        return _full_refresh_por_lote(
            FuncaoAtividadeCargoServidor,
            (
                [
                    FuncaoAtividadeCargoServidor(**_row_to_funcao_atividade(r))
                    for r in chunk
                ]
                for chunk in self.eol.iter_query(
                    SQL_FUNCOES_ATIVIDADE, _params_cargo()
                )
            ),
        )

    def popular_laudos(self) -> int:
        """Popula a tabela LaudoMedico por lote."""
        return _full_refresh_por_lote(
            LaudoMedico,
            (
                [LaudoMedico(**_row_to_laudo(r)) for r in chunk]
                for chunk in self.eol.iter_query(SQL_LAUDOS, _params_cargo())
            ),
        )

    def popular_atribuicoes_aula(self) -> int:
        """Popula a tabela AtribuicaoAula via hash incremental.

        EOL usa cancelamento lógico (dt_cancelamento), não deleção física,
        por isso upsert incremental é seguro: registros cancelados têm o
        campo atualizado e o hash diverge, forçando a escrita.
        """
        total = 0
        for chunk in self.eol.iter_query(
            SQL_ATRIBUICOES_AULA, _params_cargo()
        ):
            total += _upsert_incremental(
                AtribuicaoAula,
                "atribuicao_aula",
                [_row_to_atribuicao_aula(r) for r in chunk],
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
        for chunk in self.eol.iter_query(SQL_ATRIBUICOES_EXTERNO):
            total += _upsert_incremental(
                AtribuicaoExterno,
                "atribuicao_externo",
                [_row_to_atribuicao_externo(r) for r in chunk],
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
    # Execucao completa na ordem correta
    # ------------------------------------------------------------------

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
            fase_inicial: Fase de início (1–3). Use > 1 para retomar após
                falha.
                - 1: Tabelas sem dependências (UEs, turmas, professores)
                - 2: Vínculos cargo/contrato (dependem da fase 1)
                - 3: Atribuições e bloqueios (dependem da fase 2)
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
                for i, chunk in enumerate(
                    original_iter_query(sql, parametros)
                ):
                    if i < li:
                        continue
                    _lote_counter[0] += 1
                    yield chunk
                    if on_lote is not None:
                        on_lote(nome, _lote_counter[0])

            self.eol.iter_query = _iter_rastreavel  # type: ignore[method-assign]
            try:
                r[nome] = metodo()
            finally:
                self.eol.iter_query = original_iter_query  # type: ignore[method-assign]

            log("[ETL PROF] %s: %d", nome, r[nome])
            if on_tabela_concluida is not None:
                on_tabela_concluida(nome, r[nome])

        # ------------------------------------------------------------------
        # Fase 1 — Sem dependências internas
        # ------------------------------------------------------------------
        if fase_inicial <= 1:
            log("[ETL PROF] === Fase 1: Suporte e Professores ===")
            _executar_tabela(
                "unidade_educacional",
                self.popular_unidades_educacionais,
            )
            _executar_tabela("turma_escola", self.popular_turmas_escola)
            _executar_tabela("professor", self.popular_professores)
            _executar_tabela("pessoa", self.popular_pessoas)
            self.ultima_fase_concluida = 1
            _pular = None  # fases seguintes rodam completas
            log("[ETL PROF] Fase 1 concluída.")

        # ------------------------------------------------------------------
        # Fase 2 — Dependem de fase 1
        # ------------------------------------------------------------------
        if fase_inicial <= 2:
            log("[ETL PROF] === Fase 2: Vínculos ===")
            _executar_tabela(
                "serie_turma_grade", self.popular_serie_turma_grade
            )
            _executar_tabela(
                "turma_escola_grade_programa",
                self.popular_turma_escola_grade_programa,
            )
            _executar_tabela("cargo_base_servidor", self.popular_cargos_base)
            _executar_tabela(
                "contrato_externo", self.popular_contratos_externos
            )
            self.ultima_fase_concluida = 2
            _pular = None
            log("[ETL PROF] Fase 2 concluída.")

        # ------------------------------------------------------------------
        # Fase 3 — Dependem de fase 2
        # ------------------------------------------------------------------
        if fase_inicial <= 3:
            log("[ETL PROF] === Fase 3: Atribuições e Bloqueios ===")
            _executar_tabela(
                "turma_grade_territorio_experiencia",
                self.popular_turma_grade_territorio_experiencia,
            )
            _executar_tabela("lotacao_servidor", self.popular_lotacoes)
            _executar_tabela(
                "cargo_sobreposto_servidor", self.popular_cargos_sobrepostos
            )
            _executar_tabela(
                "funcao_atividade_cargo_servidor",
                self.popular_funcoes_atividade,
            )
            _executar_tabela("laudo_medico", self.popular_laudos)
            _executar_tabela("atribuicao_aula", self.popular_atribuicoes_aula)
            _executar_tabela(
                "atribuicao_externo", self.popular_atribuicoes_externo
            )
            self.ultima_fase_concluida = 3
            log("[ETL PROF] Fase 3 concluída.")

        # Pendente: agrupamento_atribuicao_territorio_saber
        # Requer ApiEolConnection (PostgreSQL API EOL — não implementado).

        total = sum(r.values())
        log(
            "[ETL PROF] Concluído. Linhas alteradas: %d (fases %d–3).",
            total,
            fase_inicial,
        )
        return r
