"""Serviço de ETL do domínio PROGRAMAS_DB.

Responsabilidade:
    Orquestrar a extração de dados do EOL (SQL Server) e a persistência
    incremental no banco programas_db.

Estratégia:
    Usa processamento incremental baseado em Hash SHA-256 (EtlAuditoriaLinha)
    para minimizar escritas no banco destino.

Mapeamento:
    Utiliza DTOs (ModelIn/ModelOut) para garantir tipagem e centralizar
    a lógica de transformação.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from django.utils import timezone

from apps.controle_auditoria.models import EtlAuditoriaLinha
from apps.eol_connection.libs.servico_eol import EOLService
from apps.programas.enums import ComponenteCurricularEOL, TipoProgramaEOL
from apps.programas.dtos.model_in import (
    ComponenteCurricularProgramaIn,
    MatriculaTurmaProgramaIn,
    TipoProgramaIn,
    TurmaProgramaComponenteCurricularIn,
    TurmaProgramaIn,
)
from apps.programas.dtos.model_out import (
    ComponenteCurricularProgramaOut,
    MatriculaTurmaProgramaOut,
    TipoProgramaOut,
    TurmaProgramaComponenteCurricularOut,
    TurmaProgramaOut,
)
from apps.programas.models import (
    ComponenteCurricularPrograma,
    MatriculaTurmaPrograma,
    TipoPrograma,
    TurmaPrograma,
    TurmaProgramaComponenteCurricular,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQLs — Extração
# ---------------------------------------------------------------------------

# Listas de códigos aceitos (derivadas dos enums — fonte única de verdade)
_TIPOS_PROGRAMA_IN = ", ".join(str(c) for c in TipoProgramaEOL.codigos())
_COMPONENTES_IN = ", ".join(str(c) for c in ComponenteCurricularEOL.codigos())

SQL_TIPO_PROGRAMA = f"""
SELECT
    cd_tipo_programa
  , LTRIM(RTRIM(sg_tipo_programa)) AS sigla
  , LTRIM(RTRIM(dc_tipo_programa)) AS descricao
FROM tipo_programa
WHERE cd_tipo_programa IN ({_TIPOS_PROGRAMA_IN})
"""

SQL_COMPONENTE_CURRICULAR_PROGRAMA = f"""
SELECT
    cc.cd_componente_curricular
  , LTRIM(RTRIM(cc.dc_componente_curricular)) AS nome_componente_curricular
FROM componente_curricular cc
WHERE cc.cd_componente_curricular IN ({_COMPONENTES_IN})
"""

SQL_TURMA_PROGRAMA = f"""
SELECT
    te.cd_turma_escola
  , LTRIM(RTRIM(te.dc_turma_escola)) AS nome_turma
  , CAST(te.cd_escola AS VARCHAR(20)) AS codigo_ue
  , CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20)) AS codigo_dre
  , te.an_letivo
  , te.cd_tipo_turno
  , tt.dc_exibicao_portal AS descricao_turno
  , te.st_turma_escola AS situacao
  , te.cd_tipo_programa
FROM turma_escola te
INNER JOIN v_cadastro_unidade_educacao vcue
    ON vcue.cd_unidade_educacao = te.cd_escola
LEFT JOIN tipo_turno tt
    ON tt.cd_tipo_turno = te.cd_tipo_turno
WHERE te.cd_tipo_turma = 3
  AND te.cd_tipo_programa IN ({_TIPOS_PROGRAMA_IN})
ORDER BY te.cd_turma_escola
"""

SQL_TURMA_PROGRAMA_COMPONENTE_CURRICULAR = f"""
SELECT DISTINCT
    tegp.cd_turma_escola
  , gcc.cd_componente_curricular
  , LTRIM(RTRIM(cc.dc_componente_curricular)) AS nome_componente_curricular
FROM turma_escola_grade_programa tegp
INNER JOIN escola_grade egp
    ON egp.cd_escola_grade = tegp.cd_escola_grade
INNER JOIN grade_componente_curricular gcc
    ON gcc.cd_grade = egp.cd_grade
INNER JOIN componente_curricular cc
    ON cc.cd_componente_curricular = gcc.cd_componente_curricular
INNER JOIN turma_escola te
    ON te.cd_turma_escola = tegp.cd_turma_escola
WHERE te.cd_tipo_turma = 3
  AND te.cd_tipo_programa IN ({_TIPOS_PROGRAMA_IN})
  AND gcc.cd_componente_curricular IN ({_COMPONENTES_IN})
ORDER BY tegp.cd_turma_escola
"""

SQL_MATRICULA_TURMA_PROGRAMA = f"""
SELECT
      vm.cd_aluno
    , m.cd_turma_escola
    , gcc.cd_componente_curricular
    , LTRIM(RTRIM(cc.dc_componente_curricular)) AS nome_componente_curricular
    , m.cd_situacao_aluno
    , m.dt_situacao_aluno
    , m.dt_situacao_aluno AS dt_situacao
    , te.an_letivo
    , CAST(te.cd_escola AS VARCHAR(20)) AS codigo_ue
    , CAST(vcue.cd_unidade_administrativa_referencia AS VARCHAR(20)) AS codigo_dre
    , te.cd_tipo_programa
  FROM matricula_turma_escola m
  INNER JOIN v_matricula_cotic vm
      ON vm.cd_matricula = m.cd_matricula
  INNER JOIN turma_escola te
      ON te.cd_turma_escola = m.cd_turma_escola
  INNER JOIN v_cadastro_unidade_educacao vcue
      ON vcue.cd_unidade_educacao = te.cd_escola
  INNER JOIN turma_escola_grade_programa tegp
      ON tegp.cd_turma_escola = te.cd_turma_escola
  INNER JOIN escola_grade eg
      ON eg.cd_escola_grade = tegp.cd_escola_grade
  INNER JOIN grade_componente_curricular gcc
      ON gcc.cd_grade = eg.cd_grade
  INNER JOIN componente_curricular cc
      ON cc.cd_componente_curricular = gcc.cd_componente_curricular
  WHERE te.cd_tipo_turma = 3
    AND te.cd_tipo_programa IN ({_TIPOS_PROGRAMA_IN})
    AND gcc.cd_componente_curricular IN ({_COMPONENTES_IN})
  ORDER BY vm.cd_aluno, te.cd_turma_escola
"""

# ---------------------------------------------------------------------------
# Helpers de Controle Incremental
# ---------------------------------------------------------------------------


def _calcular_hash(obj: Any, campos: list[str]) -> str:
    """Calcula SHA-256 dos campos de conteúdo de uma instância Django."""
    data = {f: getattr(obj, f) for f in campos}
    conteudo = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(conteudo).hexdigest()


def _upsert_incremental(
    model_class: Any,
    tabela: str,
    objs: list[Any],
    update_fields: list[str],
    unique_fields: list[str] | None = None,
    timestamp_field: str | None = None,
) -> int:
    """Upsert incremental: salva apenas o que mudou comparando com EtlAuditoriaLinha.

    Args:
        unique_fields: campos que formam a chave de conflito no bulk_create.
            Padrão: PK do model. Aceita campos simples ou compostos.
        timestamp_field: campo de timestamp atualizado nos registros alterados.
            Excluído do cálculo de hash para não forçar escrita em toda execução.
    """
    if not objs:
        return 0

    pk_name = model_class._meta.pk.name
    key_fields = unique_fields or [pk_name]

    # Campos de conteúdo para hash: exclui o timestamp de atualização
    campos_hash = [f for f in update_fields if f != timestamp_field]

    def _chave(obj: Any) -> tuple:
        return tuple(getattr(obj, f) for f in key_fields)

    # Deduplicar por chave natural (mantém o último em caso de duplicata na origem)
    objs_unicos: dict[tuple, Any] = {_chave(obj): obj for obj in objs}

    linhas_com_hash = []
    for chave, obj in objs_unicos.items():
        id_destino = tabela + ":" + ":".join(str(v) for v in chave)
        linhas_com_hash.append((id_destino, _calcular_hash(obj, campos_hash), obj))

    # Busca hashes existentes no banco de auditoria (banco default)
    ids_destino = [item[0] for item in linhas_com_hash]
    hashes_existentes = dict(
        EtlAuditoriaLinha.objects.filter(id_destino__in=ids_destino).values_list(
            "id_destino", "hash_controle"
        )
    )

    # Filtra apenas o que mudou ou é novo
    objs_para_salvar = []
    novos_hashes: dict[str, str] = {}
    for id_destino, novo_hash, obj in linhas_com_hash:
        if hashes_existentes.get(id_destino) != novo_hash:
            objs_para_salvar.append(obj)
            novos_hashes[id_destino] = novo_hash

    if not objs_para_salvar:
        return 0

    # Atualiza timestamp nos registros que mudaram
    if timestamp_field:
        agora = timezone.now()
        for obj in objs_para_salvar:
            setattr(obj, timestamp_field, agora)

    # Grava no banco destino (programas_db)
    model_class.objects.using("programas_db").bulk_create(
        objs_para_salvar,
        update_conflicts=True,
        unique_fields=key_fields,
        update_fields=update_fields,
        batch_size=500,
    )

    # Atualiza hashes no banco de auditoria (banco default)
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
# Serviço Principal: EtlProgramasService
# ---------------------------------------------------------------------------


@dataclass
class _FaseInfo:
    """Metadados mínimos de fase — compat com contrato do BaseEtlCommand."""

    table_name: str


class EtlProgramasService:
    """Orquestra o ETL unificado para o domínio Programas."""

    _FASES: tuple[_FaseInfo, ...] = (
        _FaseInfo(table_name="tipo_programa"),
        _FaseInfo(table_name="componente_curricular_programa"),
        _FaseInfo(table_name="turma_programa"),
        _FaseInfo(table_name="turma_programa_componente_curricular"),
        _FaseInfo(table_name="matricula_turma_programa"),
    )

    def __init__(
        self,
        db_alias: str = "programas_db",
        id_execucao: UUID | None = None,
        repositorio_auditoria: Any | None = None,
        primeiro_run: bool = False,
        eol: EOLService | None = None,
    ) -> None:
        """Inicia o serviço injetando dependências mockáveis.

        A assinatura espelha BaseEtlService para compatibilidade com
        BaseEtlCommand._handle_sync, mas o service é síncrono próprio.
        """
        self.db_alias = db_alias
        self.id_execucao = id_execucao
        self.repositorio_auditoria = repositorio_auditoria
        self.primeiro_run = primeiro_run
        self.eol = eol or EOLService()
        self.ultima_fase_concluida = 0
        self.ultimo_token: str | None = None
        self._fases = list(self._FASES)

    def popular_tipos_programa(self) -> int:
        """Fase 1: Extrai e persiste TipoPrograma (seed do EOL).

        O codigo_tipo_programa preserva o cd_tipo_programa do EOL.
        A categoria (PAP/PAEE) é derivada do id via mapeamento em model_out.
        """
        rows = self.eol.executar_query(SQL_TIPO_PROGRAMA)
        objs = [TipoProgramaOut.from_in(TipoProgramaIn(*r)) for r in rows]
        update_fields = ["nome", "categoria", "ativo"]
        total = _upsert_incremental(TipoPrograma, "tipo_programa", objs, update_fields)
        logger.info("[ETL PROG] tipo_programa: %d", total)
        return total

    def popular_componentes_curriculares(self) -> int:
        """Fase 2: Extrai e persiste ComponenteCurricularPrograma (seed do EOL).

        Substitui as constantes hardcoded IDS_COMPONENTES_CURRICULARES_PAP_NOVO
        e COMPONENTE_CURRICULAR_ID_SRM do Pedagogico-API.
        A categoria e o flag vigente são derivados do id via mapeamento em model_out.
        """
        rows = self.eol.executar_query(SQL_COMPONENTE_CURRICULAR_PROGRAMA)
        objs = [
            ComponenteCurricularProgramaOut.from_in(ComponenteCurricularProgramaIn(*r))
            for r in rows
        ]
        update_fields = [
            "nome_componente_curricular",
            "categoria",
            "vigente",
        ]
        total = _upsert_incremental(
            ComponenteCurricularPrograma,
            "componente_curricular_programa",
            objs,
            update_fields,
            unique_fields=["codigo_componente_curricular"],
        )
        logger.info("[ETL PROG] componente_curricular_programa: %d", total)
        return total

    def popular_turmas_programa(self) -> int:
        """Fase 3: Extrai e persiste TurmaPrograma (ETL incremental).

        Cobre turmas com cd_tipo_turma=3 e cd_tipo_programa PAP/PAEE do EOL.
        """
        rows = self.eol.executar_query(SQL_TURMA_PROGRAMA)
        objs = [TurmaProgramaOut.from_in(TurmaProgramaIn(*r)) for r in rows]
        update_fields = [
            "nome_turma",
            "codigo_ue",
            "codigo_dre",
            "ano_letivo",
            "tipo_turno",
            "descricao_turno",
            "situacao",
            "codigo_tipo_programa",
            "categoria",
            "atualizado_em",
        ]
        total = _upsert_incremental(
            TurmaPrograma,
            "turma_programa",
            objs,
            update_fields,
            unique_fields=["codigo_turma"],
            timestamp_field="atualizado_em",
        )
        logger.info("[ETL PROG] turma_programa: %d", total)
        return total

    def popular_turmas_programa_componentes(self) -> int:
        """Fase 4: Extrai e persiste TurmaProgramaComponenteCurricular (ETL incremental).

        Depende de TurmaPrograma estar carregado (FK lógica).
        """
        rows = self.eol.executar_query(SQL_TURMA_PROGRAMA_COMPONENTE_CURRICULAR)
        objs = [
            TurmaProgramaComponenteCurricularOut.from_in(
                TurmaProgramaComponenteCurricularIn(*r)
            )
            for r in rows
        ]
        update_fields = ["nome_componente_curricular"]
        total = _upsert_incremental(
            TurmaProgramaComponenteCurricular,
            "turma_programa_componente_curricular",
            objs,
            update_fields,
            unique_fields=["codigo_turma", "codigo_componente_curricular"],
        )
        logger.info("[ETL PROG] turma_programa_componente_curricular: %d", total)
        return total

    def popular_matriculas_turma_programa(self) -> int:
        """Fase 5: Extrai e persiste MatriculaTurmaPrograma (ETL incremental).

        Depende de TurmaPrograma estar carregado (FK lógica).
        """
        rows = self.eol.executar_query(SQL_MATRICULA_TURMA_PROGRAMA)
        objs = [MatriculaTurmaProgramaOut.from_in(MatriculaTurmaProgramaIn(*r)) for r in rows]
        update_fields = [
            "nome_componente_curricular",
            "codigo_situacao_matricula",
            "descricao_situacao_matricula",
            "data_matricula",
            "data_situacao",
            "ano_letivo",
            "codigo_ue",
            "codigo_dre",
            "categoria",
            "atualizado_em",
        ]
        total = _upsert_incremental(
            MatriculaTurmaPrograma,
            "matricula_turma_programa",
            objs,
            update_fields,
            unique_fields=["codigo_turma", "codigo_aluno", "codigo_componente_curricular"],
            timestamp_field="atualizado_em",
        )
        logger.info("[ETL PROG] matricula_turma_programa: %d", total)
        return total

    def executar(self, fase_inicial: int = 1) -> dict[str, int]:
        """Executa as fases do ETL de programas em ordem de dependência."""
        resultados: dict[str, int] = {}
        log = logger.info

        log("[ETL PROG] Iniciando carga a partir da fase %d...", fase_inicial)

        if fase_inicial <= 1:
            log("[ETL PROG] === Fase 1: TipoPrograma ===")
            resultados["tipo_programa"] = self.popular_tipos_programa()
            self.ultima_fase_concluida = 1
            log("[ETL PROG] Fase 1 concluída.")

        if fase_inicial <= 2:
            log("[ETL PROG] === Fase 2: ComponenteCurricularPrograma ===")
            resultados["componente_curricular_programa"] = self.popular_componentes_curriculares()
            self.ultima_fase_concluida = 2
            log("[ETL PROG] Fase 2 concluída.")

        if fase_inicial <= 3:
            log("[ETL PROG] === Fase 3: TurmaPrograma ===")
            resultados["turma_programa"] = self.popular_turmas_programa()
            self.ultima_fase_concluida = 3
            log("[ETL PROG] Fase 3 concluída.")

        if fase_inicial <= 4:
            log("[ETL PROG] === Fase 4: TurmaProgramaComponenteCurricular ===")
            resultados["turma_programa_componente_curricular"] = (
                self.popular_turmas_programa_componentes()
            )
            self.ultima_fase_concluida = 4
            log("[ETL PROG] Fase 4 concluída.")

        if fase_inicial <= 5:
            log("[ETL PROG] === Fase 5: MatriculaTurmaPrograma ===")
            resultados["matricula_turma_programa"] = self.popular_matriculas_turma_programa()
            self.ultima_fase_concluida = 5
            log("[ETL PROG] Fase 5 concluída.")

        total = sum(resultados.values())
        log(
            "[ETL PROG] Concluído. Linhas alteradas: %d (fases %d–5).",
            total,
            fase_inicial,
        )
        return resultados
