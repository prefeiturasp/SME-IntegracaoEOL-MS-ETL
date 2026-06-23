"""Serviço ETL do domínio pedagógico.

Lê dados do EOL, transforma para os modelos do app `pedagogico` e grava no
banco `pedagogico_db`. As regras de origem, chaves e filtros ficam
documentadas em `docs/dominios/pedagogico/`.
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
    AtribuicaoComponenteIn,
    AtribuicaoTerritorioSaberIn,
    ComponenteCurricularSimplesIn,
    ComponenteTurmaIn,
    GradeComponenteCurricularIn,
    TurmaIn,
)
from apps.pedagogico.models import (
    AgrupamentoAtribuicaoTerritorioSaber,
    AtribuicaoComponente,
    ComponenteCurricular,
    ComponenteCurricularAgrupamento,
    ComponenteTurma,
    GradeComponenteCurricular,
    Turma,
)
from apps.pedagogico.queries import (
    SQL_ANOS_LETIVOS,
    SQL_ATRIBUICAO_COMPONENTE,
    SQL_ATRIBUICOES_TERRITORIO_SABER,
    SQL_COMPONENTE_TURMA,
    SQL_COMPONENTES_NAO_CANCELADOS,
    SQL_GRADE_COMPONENTE_CURRICULAR,
    SQL_TURMAS,
)
from apps.pedagogico.services.agrupamentos import (
    agrupar_atribuicoes_territorio_saber,
    chave_agrupamento_persistido,
    montar_indices_agrupamentos_existentes,
)

logger = logging.getLogger(__name__)

_DB = "pedagogico_db"
ProcessedRecord = tuple[str, str, Any]
TransformResult = ProcessedRecord | None


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
_UNIQUE_AGRUP = (
    "cod_turma",
    "cod_territorio_saber",
    "cod_experiencia_pedagogica",
    "rf_professor",
    "dt_inicio_atribuicao",
    "cod_componentes_curriculares",
)
_UNIQUE_ITEM = (
    "componente_codigo",
    "turma_codigo",
    "codigo_agrupamento",
    "rf_professor",
)


class EtlPedagogicoService(BaseEtlService):
    """Orquestra o ETL completo do dominio PEDAGOGICO_DB.

    Herda de ``BaseEtlService`` para reutilizar o pipeline
    Producer-Consumer com ThreadPool, auditoria incremental via SHA-256
    (``pg_engine``), controle de ``primeiro_run`` e retry em deadlock.

    Customizações em relação ao padrão base:
        - ``_iter_chunks``: suporta templates com ``?`` para iteração
          por ano letivo (phases 2, 4, 5, 6).
        - ``_criar_transform``: injeta ``_agora`` via closure, sem
          alocação extra a cada linha.
        - ``_executar_fase``: fase 3 (agrupamentos) é tratada à parte
          por escrever em duas tabelas após agregação completa em memória.
        - ``executar``: trata o resultado duplo da fase 3.
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
        fases: list[str] | None = None,
    ) -> None:
        super().__init__(
            db_alias=db_alias,
            id_execucao=id_execucao,
            repositorio_auditoria=repositorio_auditoria,
            primeiro_run=primeiro_run,
            fases=fases,
        )
        self.eol = eol or EOLService()
        self._agora = timezone.now()
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
            "componente_turma": self._transform_componente_turma,
            "atribuicao_componente": self._transform_atribuicao_componente,
            "grade_componente_curricular": (
                self._transform_grade_componente_curricular
            ),
            "turma": self._transform_componente_curricular,
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

    def _transform_componente_turma(
        self,
        dto_in: Any,
        model_class: Any,
        agora: Any,
        hash_fields: list[str],
    ) -> Callable[[tuple[Any, ...]], TransformResult]:
        def transform(row: tuple[Any, ...]) -> TransformResult:
            dto = dto_in(*row)
            if dto.turma_codigo is None or dto.componente_codigo is None:
                return None
            obj = model_class(**dto.to_domain(agora))
            pk = f"{obj.turma_codigo}-{obj.componente_codigo}"
            return pk, calcular_hash(obj, hash_fields), obj

        return transform

    def _transform_atribuicao_componente(
        self,
        dto_in: Any,
        model_class: Any,
        agora: Any,
        hash_fields: list[str],
    ) -> Callable[[tuple[Any, ...]], TransformResult]:
        def transform(row: tuple[Any, ...]) -> TransformResult:
            dto = dto_in(*row)
            if dto.turma_codigo is None or dto.professor is None:
                return None
            obj = model_class(**dto.to_domain(agora))
            pk = f"{obj.turma_codigo}-{obj.componente_codigo}-{obj.professor}"
            return pk, calcular_hash(obj, hash_fields), obj

        return transform

    def _transform_grade_componente_curricular(
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
                f"-{obj.codigo_serie_ensino or ''}"
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
            (
                "|".join(
                    str(valor) for valor in chave_agrupamento_persistido(a)
                ),
                calcular_hash(a, hash_agrup),
                a,
            )
            for a in agrupamentos
        ]
        meta_agrup = self._get_batch_meta(
            None,
            table_name="agrupamento_atribuicao_territorio_saber",
            model_class=AgrupamentoAtribuicaoTerritorioSaber,
            update_fields=list(_UPDATE_AGRUP),
            unique_fields=list(_UNIQUE_AGRUP),
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
                f"-{it.codigo_agrupamento}"
                f"-{it.rf_professor or ''}",
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
                *_UNIQUE_ITEM,
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
    # Override _executar_fase para fase de agrupamentos
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
                update_fields=("descricao", "regencia", "transferido_em"),
                unique_fields=("codigo",),
            ),
            PhaseConfig(
                nome="componente_turma",
                sql=SQL_COMPONENTE_TURMA,
                table_name="componente_turma",
                source_table="componente_turma",
                model_class=ComponenteTurma,
                dto_in=ComponenteTurmaIn,
                pk_field=["turma_codigo", "componente_codigo"],
                update_fields=(
                    "codigo_componente_territorio_saber",
                    "transferido_em",
                ),
                unique_fields=("turma_codigo", "componente_codigo"),
            ),
            PhaseConfig(
                nome="atribuicao_componente",
                sql=SQL_ATRIBUICAO_COMPONENTE,
                table_name="atribuicao_componente",
                source_table="atribuicao_componente",
                model_class=AtribuicaoComponente,
                dto_in=AtribuicaoComponenteIn,
                pk_field=["turma_codigo", "componente_codigo", "professor"],
                update_fields=(
                    "atribuicao_externa",
                    "ano_letivo",
                    "id_atribuicao_origem",
                    "dt_atribuicao",
                    "dt_cancelamento",
                    "dt_disponibilizacao",
                    "cd_motivo_disponibilizacao",
                    "transferido_em",
                ),
                unique_fields=(
                    "turma_codigo",
                    "componente_codigo",
                    "professor",
                ),
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
                unique_fields=_UNIQUE_AGRUP,
            ),
            PhaseConfig(
                nome="grade_componente_curricular",
                sql=SQL_GRADE_COMPONENTE_CURRICULAR,
                table_name="grade_componente_curricular",
                source_table="grade_componente_curricular",
                model_class=GradeComponenteCurricular,
                dto_in=GradeComponenteCurricularIn,
                pk_field=[
                    "codigo_componente_curricular",
                    "ano_letivo",
                    "modalidade",
                    "codigo_serie_ensino",
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
                    "codigo_serie_ensino",
                ),
            ),
            PhaseConfig(
                nome="turma",
                sql=SQL_TURMAS,
                table_name="turma",
                source_table="turma_escola",
                model_class=Turma,
                dto_in=TurmaIn,
                pk_field="codigo",
                update_fields=(
                    "ano_letivo",
                    "ano",
                    "tipo_turma",
                    "nome_turma",
                    "duracao_turno",
                    "tipo_turno",
                    "data_inicio_turma",
                    "data_fim",
                    "extinta",
                    "situacao",
                    "ue_codigo",
                    "data_atualizacao",
                    "data_status_turma_escola",
                    "serie_ensino",
                    "codigo_serie_ensino",
                    "modalidade",
                    "codigo_modalidade",
                    "codigo_tipo_programa",
                    "codigo_modalidade_etapa",
                    "semestre",
                    "ensino_especial",
                    "codigo_etapa_ensino",
                    "codigo_ciclo_ensino",
                    "tipo_escola",
                    "codigo_grade_programa",
                    "descricao_grade_programa",
                    "tipo_grade_programa",
                    "transferido_em",
                ),
                unique_fields=("codigo",),
            ),
        ]

    # ------------------------------------------------------------------
    # Execução completa
    # ------------------------------------------------------------------

    def executar(self, fase_inicial: int = 1) -> dict[str, int]:
        """Executa ETL do domínio PEDAGOGICO_DB a partir de ``fase_inicial``.

        Fases:
            1 — componente_curricular
            2 — componente_turma             (por ano letivo)
            3 — atribuicao_componente        (por ano letivo)
            4 — agrupamento_territorio_saber (agregação → 2 tabelas)
            5 — grade_componente_curricular  (por ano letivo)
            6 — turma                        (por ano letivo)
        """
        self._agora = timezone.now()
        self._cache_anos = None  # reseta cache de anos para o run

        resultados: dict[str, int] = {}
        logger.info(
            "[ETL PEDAG] Iniciando a partir da fase %d...", fase_inicial
        )

        for i, config in enumerate(self._fases, 1):
            if i < fase_inicial:
                continue
            if (
                self._fases_selecionadas is not None
                and config.nome not in self._fases_selecionadas
            ):
                logger.info(
                    "[ETL PEDAG] Fase %d ignorada (não selecionada): %s",
                    i,
                    config.nome,
                )
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
