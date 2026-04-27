"""Servico ETL do dominio PEDAGOGICO_DB.

Responsabilidade:
    Ler dados do EOL (SQL Server via EOLService) e popular os models
    do app pedagogico no banco pedagogico_db.

Estratégia de escrita: upsert incremental com hash SHA-256 via BaseEtlService.
    ComponenteCurricular           — unique: codigo
    AgrupamentoAtribuicaoTS        — unique: cod_agrupamento
    ComponenteCurricularAgrupamento — unique: (componente_codigo,
                                              turma_codigo, codigo_agrupamento)
    ComponenteCurricularPorTurma   — unique: (codigo, turma_codigo, professor)
    ComponenteInicioTurma          — unique: (componente_codigo, turma_codigo)
    GradeCurricularSerie — unique: (codigo_componente_curricular,
                                                ano_letivo, modalidade)
"""

import logging
from collections.abc import Callable, Iterator
from typing import Any, cast
from uuid import UUID

from django.utils import timezone

from apps.core.libs.base_etl_service import (
    BaseEtlService,
    PhaseConfig,
    PipelineMetrics,
)
from apps.core.libs.thread_processor import calcular_hash
from apps.eol_connection.libs.servico_eol import EOLService
from apps.pedagogico.dtos.model_in import (
    AtribuicaoTerritorioSaberIn,
    ComponenteCurricularSimplesIn,
    ComponenteInicioTurmaIn,
    ComponentePorTurmaIn,
    GradeCurricularSerieIn,
    RegenciaComponenteCurricularIn,
)
from apps.pedagogico.models import (
    AgrupamentoAtribuicaoTerritorioSaber,
    ComponenteCurricular,
    ComponenteCurricularAgrupamento,
    ComponenteCurricularPorTurma,
    ComponenteInicioTurma,
    GradeCurricularSerie,
)
from apps.pedagogico.queries import (
    SQL_ANOS_LETIVOS,
    SQL_ATRIBUICOES_TERRITORIO_SABER,
    SQL_COMPONENTE_INICIO_TURMA,
    SQL_COMPONENTES_NAO_CANCELADOS,
    SQL_COMPONENTES_POR_TURMA,
    SQL_GRADE_CURRICULAR_SERIE,
    SQL_LOOKUP_PLANEJAMENTO_REGENCIA,
)
from apps.pedagogico.services.agrupamentos import (
    agrupar_atribuicoes_territorio_saber,
    montar_indices_agrupamentos_existentes,
)

logger = logging.getLogger(__name__)

_DB = "pedagogico_db"
ProcessedRecord = tuple[str, str, Any]
TransformResult = ProcessedRecord | None
A3ExactKey = tuple[int, Any, Any]
A3ExactSet = set[A3ExactKey]
A3FallbackSet = set[int]

# ---------------------------------------------------------------------------
# Helpers de planejamento de regência
# ---------------------------------------------------------------------------


def _build_a3_index(
    rows_a3: list[RegenciaComponenteCurricularIn],
) -> tuple[A3ExactSet, A3FallbackSet]:
    exact: A3ExactSet = set()
    fallback: A3FallbackSet = set()
    for r in rows_a3:
        codigo = int(r.id_componente_curricular)
        if r.turno is None and r.ano is None:
            fallback.add(codigo)
        else:
            exact.add((codigo, r.turno, r.ano))
    return exact, fallback


def _planejamento_regencia(
    codigo: int,
    turno_turma: Any,
    ano_turma: Any,
    exact: A3ExactSet,
    fallback: A3FallbackSet,
) -> bool:
    if (codigo, turno_turma, ano_turma) in exact:
        return True
    return codigo in fallback


# ---------------------------------------------------------------------------
# Servico principal
# ---------------------------------------------------------------------------

_UPDATE_AGRUP = (
    "cod_territorio_saber",
    "cod_experiencia_pedagogica",
    "dt_inicio_atribuicao",
    "dt_fim_atribuicao",
    "dt_fim_turma",
    "rf_professor",
    "cod_turma",
    "cod_componentes_curriculares",
    "cod_motivo_disponibilizacao",
    "desc_territorio_saber",
    "desc_experiencia_pedagogica",
    "encerramento_atribuicao_agrupamento_atualizado",
    "transferido_em",
)
_UPDATE_ITEM = ("rf_professor", "ano_letivo", "transferido_em")


class EtlPedagogicoService(BaseEtlService):
    """Orquestra o ETL completo do dominio PEDAGOGICO_DB.

    Herda de ``BaseEtlService`` para reutilizar o pipeline
    Producer-Consumer com ThreadPool, auditoria incremental via SHA-256
    (``pg_engine``), controle de ``primeiro_run`` e retry em deadlock.

    Customizações em relação ao padrão base:
        - ``_iter_chunks``: suporta templates com ``?`` para iteração
          por ano letivo (phases 2, 4, 5, 6).
        - ``_criar_transform``: injeta ``_agora`` e lookups de regência
          via closure, sem alocação extra a cada linha.
        - ``_executar_fase``: fase 3 (agrupamentos) é tratada à parte
          por escrever em duas tabelas após agregação completa em memória.
        - ``executar``: pré-carrega lookups antes das fases que precisam
          deles e trata o resultado duplo da fase 3.
    """

    _dominio = "PEDAGOGICO"

    def __init__(
        self,
        db_alias: str = _DB,
        id_execucao: UUID | None = None,
        repositorio_auditoria: Any | None = None,
        primeiro_run: bool = False,
        eol: EOLService | None = None,
        ano_letivo: int | None = None,
    ) -> None:
        super().__init__(
            db_alias=db_alias,
            id_execucao=id_execucao,
            repositorio_auditoria=repositorio_auditoria,
            primeiro_run=primeiro_run,
        )
        self.eol = eol or EOLService()
        self._agora = timezone.now()
        self._exact: A3ExactSet = set()
        self._fallback: A3FallbackSet = set()
        self._total_itens_agrupamento: int = 0
        self._cache_anos: list[int] | None = None
        self._ano_letivo: int | None = ano_letivo
        self._fases = self._init_fases()

    # ------------------------------------------------------------------
    # Contrato BaseEtlService
    # ------------------------------------------------------------------

    def _iter_chunks(self, sql: str) -> Iterator[list[tuple]]:
        """Itera chunks do SQL Server via EOLService.

        Quando o SQL contém ``?``, itera para cada ano letivo
        substituindo o placeholder — permite o Producer-Consumer operar
        de forma transparente sobre queries parametrizadas por ano.
        """
        if "?" in sql:
            for ano in self._anos_letivos():
                yield from self.eol.iter_query(sql.replace("?", str(ano)))
        else:
            yield from self.eol.iter_query(sql)

    def _criar_transform(  # type: ignore[override]
        self, config: PhaseConfig
    ) -> Callable[[tuple[Any, ...]], TransformResult]:
        """Override: roteia para o transform correto por fase.

        Captura ``_agora`` e lookups em closure — sem overhead de
        atributo por linha durante o processamento paralelo.
        """
        agora = self._agora
        hash_fields = sorted(config.update_fields)
        dto_in = config.dto_in
        model_class = config.model_class

        transform_factories = {
            "componente_curricular": self._transform_componente_curricular,
            "componente_por_turma": self._transform_componente_por_turma,
            "componente_inicio_turma": self._transform_componente_inicio_turma,
            "grade_curricular_serie": (self._transform_grade_curricular_serie),
        }
        factory = transform_factories.get(config.nome)
        if factory is None:
            return super()._criar_transform(config)
        return factory(dto_in, model_class, agora, hash_fields)

    def _transform_componente_curricular(
        self,
        dto_in: Any,
        model_class: Any,
        agora: Any,
        hash_fields: list[str],
    ) -> Callable[[tuple[Any, ...]], TransformResult]:
        def transform(row: tuple[Any, ...]) -> TransformResult:
            dto = dto_in(*row)
            obj = model_class(**dto.to_domain(agora))
            return str(obj.codigo), calcular_hash(obj, hash_fields), obj

        return transform

    def _transform_componente_por_turma(
        self,
        dto_in: Any,
        model_class: Any,
        agora: Any,
        hash_fields: list[str],
    ) -> Callable[[tuple[Any, ...]], TransformResult]:
        exact = self._exact
        fallback = self._fallback

        def transform(row: tuple[Any, ...]) -> TransformResult:
            dto = dto_in(*row)
            if dto.codigo is None or dto.turma_codigo is None:
                return None
            codigo = int(dto.codigo)
            plan = _planejamento_regencia(
                codigo, dto.turno_turma, dto.ano_turma, exact, fallback
            )
            obj = model_class(**dto.to_domain(agora, plan))
            pk = (
                f"{obj.codigo}"
                f"-{obj.turma_codigo or ''}"
                f"-{obj.professor or ''}"
            )
            return pk, calcular_hash(obj, hash_fields), obj

        return transform

    def _transform_componente_inicio_turma(
        self,
        dto_in: Any,
        model_class: Any,
        agora: Any,
        hash_fields: list[str],
    ) -> Callable[[tuple[Any, ...]], TransformResult]:
        def transform(row: tuple[Any, ...]) -> TransformResult:
            dto = dto_in(*row)
            obj = model_class(**dto.to_domain(agora))
            pk = f"{obj.componente_codigo}-{obj.turma_codigo}"
            return pk, calcular_hash(obj, hash_fields), obj

        return transform

    def _transform_grade_curricular_serie(
        self,
        dto_in: Any,
        model_class: Any,
        agora: Any,
        hash_fields: list[str],
    ) -> Callable[[tuple[Any, ...]], TransformResult]:
        def transform(row: tuple[Any, ...]) -> TransformResult:
            dto = dto_in(*row)
            if (
                dto.codigo_componente_curricular is None
                or dto.ano_letivo is None
            ):
                return None
            obj = model_class(**dto.to_domain(agora))
            pk = (
                f"{obj.codigo_componente_curricular}"
                f"-{obj.ano_letivo}"
                f"-{obj.modalidade or ''}"
            )
            return pk, calcular_hash(obj, hash_fields), obj

        return transform

    def _processar_batch(
        self,
        config: PhaseConfig,
        chunk: list[Any],
        **kwargs: Any,
    ) -> tuple[int, int]:
        """Filtra transforms nulos antes de delegar ao pipeline base."""
        transform = kwargs.get("transform") or (lambda x: x)
        lote_transformado = [
            item
            for item in (transform(row) for row in chunk)
            if item is not None
        ]
        if not lote_transformado:
            return 0, len(chunk)

        meta = self._get_batch_meta(config)
        return self.sync_batch(
            cast(list[ProcessedRecord], lote_transformado),
            meta,
            batch_num=kwargs.get("batch_num", 0),
        )

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _anos_letivos(self) -> list[int]:
        """Retorna anos letivos do EOL, com cache por instância."""
        if self._cache_anos is None:
            anos = [
                int(r[0])
                for chunk in self.eol.iter_query(SQL_ANOS_LETIVOS)
                for r in chunk
            ]
            if self._ano_letivo is not None:
                anos = [a for a in anos if a >= self._ano_letivo]
            self._cache_anos = anos
        return self._cache_anos

    def _carregar_lookups(self) -> None:
        """Pré-carrega índice de planejamento de regência.

        Chamado uma vez em ``executar()`` antes das fases que precisam
        de lookup (componente_por_turma e componente_regencia).
        """
        rows_a3: list[RegenciaComponenteCurricularIn] = []
        for chunk in self.eol.iter_query(SQL_LOOKUP_PLANEJAMENTO_REGENCIA):
            for r in chunk:
                rows_a3.append(RegenciaComponenteCurricularIn(*r))
        self._exact, self._fallback = _build_a3_index(rows_a3)

        logger.info(
            "[ETL PEDAG] Lookups: %d exact, %d fallback.",
            len(self._exact),
            len(self._fallback),
        )

    # ------------------------------------------------------------------
    # Fase 3 — Agrupamentos (escrita em duas tabelas)
    # ------------------------------------------------------------------

    def _executar_agrupamentos(self, config: PhaseConfig) -> PipelineMetrics:
        """Fase de agrupamentos com persistência em duas tabelas.

        Coleta todas as linhas, agrega em Python e persiste em
        AgrupamentoAtribuicaoTerritorioSaber e
        ComponenteCurricularAgrupamento.

        Retorna PipelineMetrics com total_escritos = agrupamentos.
        O total de itens fica em ``self._total_itens_agrupamento``.
        """
        agora = self._agora
        rows: list[AtribuicaoTerritorioSaberIn] = []
        total_lidos = 0

        for chunk in self._iter_chunks(config.sql):
            total_lidos += len(chunk)
            for r in chunk:
                rows.append(AtribuicaoTerritorioSaberIn(*r))

        (
            agrupamentos_exatos,
            agrupamentos_historicos,
            ultimo_id_gerado,
        ) = montar_indices_agrupamentos_existentes(self.db_alias)
        agrupamentos, itens = agrupar_atribuicoes_territorio_saber(
            rows,
            agora,
            agrupamentos_exatos=agrupamentos_exatos,
            agrupamentos_historicos=agrupamentos_historicos,
            ultimo_id_gerado=ultimo_id_gerado,
        )

        hash_agrup = sorted(_UPDATE_AGRUP)
        hash_item = sorted(_UPDATE_ITEM)

        proc_agrup = [
            (str(a.cod_agrupamento), calcular_hash(a, hash_agrup), a)
            for a in agrupamentos
        ]
        meta_agrup = self._get_batch_meta(
            None,
            table_name="agrupamento_atribuicao_territorio_saber",
            model_class=AgrupamentoAtribuicaoTerritorioSaber,
            update_fields=list(_UPDATE_AGRUP),
            unique_fields=["cod_agrupamento"],
            modo_escrita="upsert",
        )
        total_agrup = 0
        for i in range(0, len(proc_agrup), 500):
            escritos, _ = self.sync_batch(
                proc_agrup[i : i + 500],
                meta_agrup,
                batch_num=i,
            )
            total_agrup += escritos

        proc_itens = [
            (
                f"{it.componente_codigo}"
                f"-{it.turma_codigo}"
                f"-{it.codigo_agrupamento}",
                calcular_hash(it, hash_item),
                it,
            )
            for it in itens
        ]
        meta_itens = self._get_batch_meta(
            None,
            table_name="componente_curricular_agrupamento",
            model_class=ComponenteCurricularAgrupamento,
            update_fields=list(_UPDATE_ITEM),
            unique_fields=[
                "componente_codigo",
                "turma_codigo",
                "codigo_agrupamento",
            ],
            modo_escrita="upsert",
        )
        total_itens = 0
        for i in range(0, len(proc_itens), 500):
            escritos, _ = self.sync_batch(
                proc_itens[i : i + 500],
                meta_itens,
                batch_num=i,
            )
            total_itens += escritos

        self._total_itens_agrupamento = total_itens
        logger.info(
            "AgrupamentoTerritorioSaber: %d agrupamentos, %d itens.",
            total_agrup,
            total_itens,
        )
        return PipelineMetrics(
            total_lidos=total_lidos, total_escritos=total_agrup
        )

    # ------------------------------------------------------------------
    # Override _executar_fase para fase 3
    # ------------------------------------------------------------------

    def _executar_fase(
        self, config: PhaseConfig, numero_fase: int = 0
    ) -> PipelineMetrics:
        if config.nome == "agrupamento_territorio_saber":
            return self._executar_agrupamentos(config)
        return super()._executar_fase(config, numero_fase=numero_fase)

    # ------------------------------------------------------------------
    # Definição das fases
    # ------------------------------------------------------------------

    def _init_fases(self) -> list[PhaseConfig]:
        return [
            PhaseConfig(
                nome="componente_curricular",
                sql=SQL_COMPONENTES_NAO_CANCELADOS,
                table_name="componente_curricular",
                source_table="componente_curricular",
                model_class=ComponenteCurricular,
                dto_in=ComponenteCurricularSimplesIn,
                pk_field="codigo",
                update_fields=("descricao", "transferido_em"),
                unique_fields=("codigo",),
            ),
            PhaseConfig(
                nome="componente_por_turma",
                sql=SQL_COMPONENTES_POR_TURMA,
                table_name="componente_curricular_por_turma",
                source_table="componente_curricular_por_turma",
                model_class=ComponenteCurricularPorTurma,
                dto_in=ComponentePorTurmaIn,
                pk_field=["codigo", "turma_codigo", "professor"],
                update_fields=(
                    "codigo_componente_territorio_saber",
                    "codigo_componente_curricular_pai",
                    "descricao",
                    "regencia",
                    "planejamento_regencia",
                    "territorio_saber",
                    "exibir_componente_eol",
                    "ano_letivo",
                    "transferido_em",
                ),
                unique_fields=("codigo", "turma_codigo", "professor"),
            ),
            PhaseConfig(
                nome="agrupamento_territorio_saber",
                sql=SQL_ATRIBUICOES_TERRITORIO_SABER,
                table_name="agrupamento_atribuicao_territorio_saber",
                source_table="agrupamento_atribuicao_territorio_saber",
                model_class=AgrupamentoAtribuicaoTerritorioSaber,
                dto_in=AtribuicaoTerritorioSaberIn,
                pk_field="cod_agrupamento",
                update_fields=_UPDATE_AGRUP,
                unique_fields=("cod_agrupamento",),
            ),
            PhaseConfig(
                nome="componente_inicio_turma",
                sql=SQL_COMPONENTE_INICIO_TURMA,
                table_name="componente_inicio_turma",
                source_table="componente_inicio_turma",
                model_class=ComponenteInicioTurma,
                dto_in=ComponenteInicioTurmaIn,
                pk_field=["componente_codigo", "turma_codigo"],
                update_fields=(
                    "componente_descricao",
                    "data_inicio_turma",
                    "ue_codigo",
                    "ano_letivo",
                    "tipo_periodicidade",
                    "transferido_em",
                ),
                unique_fields=("componente_codigo", "turma_codigo"),
            ),
            PhaseConfig(
                nome="grade_curricular_serie",
                sql=SQL_GRADE_CURRICULAR_SERIE,
                table_name="grade_curricular_serie",
                source_table="grade_curricular_serie",
                model_class=GradeCurricularSerie,
                dto_in=GradeCurricularSerieIn,
                pk_field=[
                    "codigo_componente_curricular",
                    "ano_letivo",
                    "modalidade",
                ],
                update_fields=(
                    "descricao_componente_curricular",
                    "codigo_ano_turma",
                    "descricao_serie_ensino",
                    "codigo_serie_ensino",
                    "transferido_em",
                ),
                unique_fields=(
                    "codigo_componente_curricular",
                    "ano_letivo",
                    "modalidade",
                ),
            ),
        ]

    # ------------------------------------------------------------------
    # Execução completa
    # ------------------------------------------------------------------

    def executar(self, fase_inicial: int = 1) -> dict[str, int]:
        """Executa ETL do domínio PEDAGOGICO_DB a partir de ``fase_inicial``.

        Fases:
            1 — componente_curricular
            2 — componente_por_turma          (por ano letivo)
            3 — agrupamento_territorio_saber  (agregação → 2 tabelas)
            4 — componente_inicio_turma       (por ano letivo)
            5 — grade_curricular_serie        (por ano letivo)
        """
        self._agora = timezone.now()
        self._cache_anos = None  # reseta cache de anos para o run

        # Lookups necessários na fase 2
        if fase_inicial <= 2:
            self._carregar_lookups()

        resultados: dict[str, int] = {}
        logger.info(
            "[ETL PEDAG] Iniciando a partir da fase %d...", fase_inicial
        )

        for i, config in enumerate(self._fases, 1):
            if i < fase_inicial:
                continue

            logger.info("[ETL PEDAG] === Fase %d: %s ===", i, config.nome)
            metrics = self._executar_fase(config)

            # Fase 3 grava em 2 tabelas — registra ambas no resultado
            if config.nome == "agrupamento_territorio_saber":
                resultados["agrupamento_atribuicao_territorio_saber"] = (
                    metrics.total_escritos
                )
                resultados["componente_curricular_agrupamento"] = (
                    self._total_itens_agrupamento
                )
            else:
                resultados[config.table_name] = metrics.total_escritos

            self.ultima_fase_concluida = i
            self._registrar_auditoria_fase(config, metrics)
            logger.info("[ETL PEDAG] Fase %d concluída.", i)

        logger.info(
            "[ETL PEDAG] Concluído. Total: %d registros.",
            sum(resultados.values()),
        )
        return resultados
