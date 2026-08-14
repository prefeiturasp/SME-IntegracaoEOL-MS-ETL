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
from apps.eol_connection.libs.servico_api_eol import ApiEOLService
from apps.eol_connection.libs.servico_eol import EOLService
from apps.pedagogico.dtos.model_in import (
    ApiEolAgrupamentoAtribuicaoTerritorioSaberIn,
    ApiEolComponenteCurricularHierarquiaIn,
    ApiEolComponenteCurricularIn,
    ApiEolComponenteCurricularPAPIn,
    ApiEolComponenteCurricularPlanejamentoRegenciaIn,
    ApiEolTurmaItinerarioEnsinoMedioIn,
    AtribuicaoComponenteIn,
    AtribuicaoTerritorioSaberIn,
    ComponenteCurricularSimplesIn,
    ComponenteTurmaIn,
    EtapaEnsinoIn,
    GradeComponenteCurricularIn,
    TurmaAtribuidaDreUeIn,
    TurmaIn,
)
from apps.pedagogico.models import (
    AgrupamentoAtribuicaoTerritorioSaber,
    AtribuicaoComponente,
    AtribuicaoTerritorioSaber,
    ComponenteCurricular,
    ComponenteCurricularAgrupamento,
    ComponenteCurricularApiEol,
    ComponenteCurricularHierarquia,
    ComponenteCurricularPAP,
    ComponenteCurricularPlanejamentoRegencia,
    ComponenteTurma,
    EtapaEnsino,
    GradeComponenteCurricular,
    Turma,
    TurmaAtribuidaDreUe,
    TurmaItinerarioEnsinoMedio,
)
from apps.pedagogico.queries import (
    API_EOL_PEDAGOGICO_TABLE_MAPPINGS,
    SQL_ANOS_LETIVOS,
    SQL_API_EOL_AGRUPAMENTO_ATRIBUICAO_TERRITORIO_SABER,
    SQL_API_EOL_COMPONENTE_CURRICULAR,
    SQL_API_EOL_COMPONENTE_CURRICULAR_HIERARQUIA,
    SQL_API_EOL_COMPONENTE_CURRICULAR_PAP,
    SQL_API_EOL_COMPONENTE_CURRICULAR_PLANEJAMENTO_REGENCIA,
    SQL_API_EOL_TURMA_ITINERARIO_ENSINO_MEDIO,
    SQL_ATRIBUICAO_COMPONENTE,
    SQL_ATRIBUICOES_TERRITORIO_SABER,
    SQL_COMPONENTE_TURMA,
    SQL_COMPONENTES_NAO_CANCELADOS,
    SQL_ETAPA_ENSINO,
    SQL_GRADE_COMPONENTE_CURRICULAR,
    SQL_TURMAS,
    SQL_TURMAS_ATRIBUIDAS_DRE_UE,
)
from apps.pedagogico.services.agrupamentos import (
    agrupar_atribuicoes_territorio_saber,
    montar_indices_agrupamentos_existentes,
)

logger = logging.getLogger(__name__)

_DB = "pedagogico_db"
_AGRUPAMENTO_GERADO_BACKUP = "agrupamento_territorio_saber_gerado"
_API_EOL_SQLS = frozenset(
    str(mapping["sql"])
    for mapping in API_EOL_PEDAGOGICO_TABLE_MAPPINGS.values()
)
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
_UNIQUE_AGRUP = (
    "cod_turma",
    "cod_territorio_saber",
    "cod_experiencia_pedagogica",
    "rf_professor",
    "dt_inicio_atribuicao",
    "cod_componentes_curriculares",
)


class EtlPedagogicoService(BaseEtlService):
    """Orquestra a carga do domínio pedagógico."""

    _dominio = "PEDAGOGICO"

    def __init__(
        self,
        db_alias: str = _DB,
        id_execucao: UUID | None = None,
        repositorio_auditoria: Any | None = None,
        primeiro_run: bool = False,
        eol: EOLService | None = None,
        api_eol: ApiEOLService | None = None,
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
        self.api_eol = api_eol or ApiEOLService()
        self._agora = timezone.now()
        self._total_itens_agrupamento: int = 0
        self._cache_anos: list[int] | None = None
        self._ano_letivo: int | None = ano_letivo
        self._fases = self._init_fases()
        if self._fases_selecionadas and (
            _AGRUPAMENTO_GERADO_BACKUP in self._fases_selecionadas
        ):
            self._fases.append(self._fase_agrupamento_gerado())

    # ------------------------------------------------------------------
    # Contrato BaseEtlService
    # ------------------------------------------------------------------

    def _iter_chunks(self, consulta: str) -> Iterator[list[tuple]]:
        """Itera registros de origem em lotes.

        Args:
            consulta: Texto base usado na carga.

        Yields:
            Lotes de registros retornados pela origem.
        """
        if consulta in _API_EOL_SQLS:
            yield from self.api_eol.iter_query(consulta)
            return
        if "?" in consulta:
            for ano in self._anos_letivos():
                yield from self.eol.iter_query(consulta.replace("?", str(ano)))
        else:
            yield from self.eol.iter_query(consulta)

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
            "atribuicao_territorio_saber": (
                self._transform_atribuicao_territorio_saber
            ),
            "grade_componente_curricular": (
                self._transform_grade_componente_curricular
            ),
            "turma": self._transform_componente_curricular,
            "turma_atribuida_dre_ue": self._transform_turma_atribuida_dre_ue,
            "etapa_ensino": self._transform_componente_curricular,
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

    def _transform_atribuicao_territorio_saber(
        self,
        dto_in: Any,
        model_class: Any,
        agora: Any,
        hash_fields: list[str],
    ) -> Callable[[tuple[Any, ...]], TransformResult]:
        def transform(row: tuple[Any, ...]) -> TransformResult:
            dto = dto_in(*row)
            if (
                dto.codigo_turma is None
                or dto.codigo_componente_curricular is None
                or dto.rf_professor is None
            ):
                return None
            obj = model_class(**dto.to_domain(agora))
            pk = (
                f"{obj.turma_codigo}"
                f"-{obj.componente_codigo}"
                f"-{obj.professor}"
                f"-{obj.codigo_territorio_saber}"
                f"-{obj.codigo_experiencia_pedagogica or ''}"
                f"-{obj.dt_atribuicao or ''}"
                f"-{obj.dt_disponibilizacao or ''}"
            )
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

    def _transform_turma_atribuida_dre_ue(
        self,
        dto_in: Any,
        model_class: Any,
        agora: Any,
        hash_fields: list[str],
    ) -> Callable[[tuple[Any, ...]], TransformResult]:
        def transform(row: tuple[Any, ...]) -> TransformResult:
            dto = dto_in(*row)
            if dto.codigo_escola is None or dto.codigo_turma is None:
                return None
            obj = model_class(**dto.to_domain(agora))
            pk = f"{obj.codigo_escola}-{obj.codigo_turma}-{obj.ano_letivo}"
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
    # Território do Saber
    # ------------------------------------------------------------------

    def _bulk_create_em_lotes(self, model_class: Any, objs: list[Any]) -> int:
        total = 0
        manager = model_class.objects.using(self.db_alias)
        for i in range(0, len(objs), 500):
            lote = objs[i : i + 500]
            manager.bulk_create(lote, batch_size=500)
            total += len(lote)
        return total

    def _executar_atribuicoes_territorio(
        self,
        config: PhaseConfig,
    ) -> PipelineMetrics:
        """Atualiza atribuições individuais de território por ano letivo.

        Args:
            config: Configuração da fase de atribuições de território.

        Returns:
            Métricas de leitura e escrita da fase.
        """
        agora = self._agora
        anos = self._anos_letivos()
        objs_por_chave: dict[tuple[Any, ...], AtribuicaoTerritorioSaber] = {}
        total_lidos = 0

        for chunk in self._iter_chunks(config.sql):
            total_lidos += len(chunk)
            for row in chunk:
                dto = AtribuicaoTerritorioSaberIn(*row)
                if (
                    dto.codigo_turma is None
                    or dto.codigo_componente_curricular is None
                    or dto.rf_professor is None
                ):
                    continue
                obj = AtribuicaoTerritorioSaber(**dto.to_domain(agora))
                chave = (
                    obj.turma_codigo,
                    obj.componente_codigo,
                    obj.professor,
                    obj.codigo_territorio_saber,
                    obj.codigo_experiencia_pedagogica,
                    obj.dt_atribuicao,
                    obj.dt_disponibilizacao,
                )
                objs_por_chave.setdefault(chave, obj)

        AtribuicaoTerritorioSaber.objects.using(self.db_alias).filter(
            ano_letivo__in=anos
        ).delete()
        total = self._bulk_create_em_lotes(
            AtribuicaoTerritorioSaber,
            list(objs_por_chave.values()),
        )
        logger.info(
            "AtribuicaoTerritorioSaber: %d registros.",
            total,
        )
        return PipelineMetrics(total_lidos=total_lidos, total_escritos=total)

    def _executar_agrupamentos(self, config: PhaseConfig) -> PipelineMetrics:
        """Gera agrupamentos locais de território e seus itens.

        Args:
            config: Configuração da fase de geração de agrupamentos.

        Returns:
            Métricas de leitura e escrita da fase.
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

        anos = self._anos_letivos()
        ComponenteCurricularAgrupamento.objects.using(self.db_alias).filter(
            ano_letivo__in=anos
        ).delete()
        AgrupamentoAtribuicaoTerritorioSaber.objects.using(
            self.db_alias
        ).filter(ano_letivo__in=anos).delete()

        total_agrup = self._bulk_create_em_lotes(
            AgrupamentoAtribuicaoTerritorioSaber,
            agrupamentos,
        )
        total_itens = self._bulk_create_em_lotes(
            ComponenteCurricularAgrupamento,
            itens,
        )

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
        if config.nome == "atribuicao_territorio_saber":
            return self._executar_atribuicoes_territorio(config)
        if config.nome == _AGRUPAMENTO_GERADO_BACKUP:
            return self._executar_agrupamentos(config)
        return super()._executar_fase(config, numero_fase=numero_fase)

    # ------------------------------------------------------------------
    # Definição das fases
    # ------------------------------------------------------------------

    def _fase_agrupamento_gerado(self) -> PhaseConfig:
        return PhaseConfig(
            nome=_AGRUPAMENTO_GERADO_BACKUP,
            sql=SQL_ATRIBUICOES_TERRITORIO_SABER,
            table_name="agrupamento_atribuicao_territorio_saber",
            source_table="atribuicao_territorio_saber",
            model_class=AgrupamentoAtribuicaoTerritorioSaber,
            dto_in=AtribuicaoTerritorioSaberIn,
            pk_field="cod_agrupamento",
            update_fields=_UPDATE_AGRUP,
            unique_fields=_UNIQUE_AGRUP,
        )

    def _init_fases(self) -> list[PhaseConfig]:
        fases = [
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
                    "desc_territorio_saber",
                    "desc_experiencia_pedagogica",
                    "tipo_escola",
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
                nome="atribuicao_territorio_saber",
                sql=SQL_ATRIBUICOES_TERRITORIO_SABER,
                table_name="atribuicao_territorio_saber",
                source_table="atribuicao_territorio_saber",
                model_class=AtribuicaoTerritorioSaber,
                dto_in=AtribuicaoTerritorioSaberIn,
                pk_field=[
                    "turma_codigo",
                    "componente_codigo",
                    "professor",
                    "codigo_territorio_saber",
                    "codigo_experiencia_pedagogica",
                    "dt_atribuicao",
                    "dt_disponibilizacao",
                ],
                update_fields=(
                    "desc_territorio_saber",
                    "desc_experiencia_pedagogica",
                    "atribuicao_externa",
                    "ano_letivo",
                    "cd_motivo_disponibilizacao",
                    "dt_fim_turma",
                    "transferido_em",
                ),
                unique_fields=(
                    "turma_codigo",
                    "componente_codigo",
                    "professor",
                    "codigo_territorio_saber",
                    "codigo_experiencia_pedagogica",
                    "dt_atribuicao",
                    "dt_disponibilizacao",
                ),
            ),
            PhaseConfig(
                nome="componente_curricular_api_eol",
                sql=SQL_API_EOL_COMPONENTE_CURRICULAR,
                table_name="componente_curricular_api_eol",
                source_table=("componentecurricular, componentecurricularpai"),
                model_class=ComponenteCurricularApiEol,
                dto_in=ApiEolComponenteCurricularIn,
                pk_field=[
                    "id_relacao_origem",
                    "id_componente_curricular",
                ],
                update_fields=(
                    "eh_regencia",
                    "eh_territorio",
                    "descricao",
                    "id_componente_curricular_pai",
                    "vigencia",
                    "transferido_em",
                ),
                unique_fields=(
                    "id_relacao_origem",
                    "id_componente_curricular",
                ),
                modo_escrita="full_refresh",
                truncate_on_full_sync=True,
            ),
            PhaseConfig(
                nome="componentecurricularhierarquia",
                sql=SQL_API_EOL_COMPONENTE_CURRICULAR_HIERARQUIA,
                table_name="componente_curricular_hierarquia",
                source_table="componentecurricularpai",
                model_class=ComponenteCurricularHierarquia,
                dto_in=ApiEolComponenteCurricularHierarquiaIn,
                pk_field="id",
                update_fields=(
                    "id_componente_curricular_pai",
                    "id_componente_curricular",
                    "vigencia",
                    "transferido_em",
                ),
                unique_fields=("id",),
                modo_escrita="full_refresh",
                truncate_on_full_sync=True,
            ),
            PhaseConfig(
                nome="componentecurricularpap",
                sql=SQL_API_EOL_COMPONENTE_CURRICULAR_PAP,
                table_name="componente_curricular_pap",
                source_table="componentecurricularpap",
                model_class=ComponenteCurricularPAP,
                dto_in=ApiEolComponenteCurricularPAPIn,
                pk_field="id",
                update_fields=("id_componente_curricular", "transferido_em"),
                unique_fields=("id",),
                modo_escrita="full_refresh",
                truncate_on_full_sync=True,
            ),
            PhaseConfig(
                nome="componentecurricularplanejamentoregencia",
                sql=SQL_API_EOL_COMPONENTE_CURRICULAR_PLANEJAMENTO_REGENCIA,
                table_name="componente_curricular_planejamento_regencia",
                source_table="regenciacomponentecurricular",
                model_class=ComponenteCurricularPlanejamentoRegencia,
                dto_in=ApiEolComponenteCurricularPlanejamentoRegenciaIn,
                pk_field=["id_componente_curricular", "turno", "ano"],
                update_fields=(
                    "id_componente_curricular",
                    "turno",
                    "ano",
                    "transferido_em",
                ),
                unique_fields=("id_componente_curricular", "turno", "ano"),
                modo_escrita="full_refresh",
                truncate_on_full_sync=True,
            ),
            PhaseConfig(
                nome="turmaitinerarioensinomedio",
                sql=SQL_API_EOL_TURMA_ITINERARIO_ENSINO_MEDIO,
                table_name="turma_itinerario_ensino_medio",
                source_table="turma_tipo_itinerario",
                model_class=TurmaItinerarioEnsinoMedio,
                dto_in=ApiEolTurmaItinerarioEnsinoMedioIn,
                pk_field="id",
                update_fields=("nome", "serie", "transferido_em"),
                unique_fields=("id",),
                modo_escrita="full_refresh",
                truncate_on_full_sync=True,
            ),
            PhaseConfig(
                nome="agrupamento_atribuicao_territorio_saber",
                sql=SQL_API_EOL_AGRUPAMENTO_ATRIBUICAO_TERRITORIO_SABER,
                table_name="agrupamento_atribuicao_territorio_saber",
                source_table="agrupamentoatribuicaoterritoriosaber",
                model_class=AgrupamentoAtribuicaoTerritorioSaber,
                dto_in=ApiEolAgrupamentoAtribuicaoTerritorioSaberIn,
                pk_field="id_linha_api_eol",
                update_fields=_UPDATE_AGRUP,
                unique_fields=_UNIQUE_AGRUP,
                modo_escrita="full_refresh",
                truncate_on_full_sync=True,
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
                    "data_fim_turma",
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
                    "codigo_tipo_periodicidade",
                    "transferido_em",
                ),
                unique_fields=("codigo",),
            ),
            PhaseConfig(
                nome="turma_atribuida_dre_ue",
                sql=SQL_TURMAS_ATRIBUIDAS_DRE_UE,
                table_name="turma_atribuida_dre_ue",
                source_table="turmas_atribuidas_dre_ue",
                model_class=TurmaAtribuidaDreUe,
                dto_in=TurmaAtribuidaDreUeIn,
                pk_field=["codigo_escola", "codigo_turma", "ano_letivo"],
                update_fields=(
                    "modalidade",
                    "semestre",
                    "codigo_modalidade",
                    "codigo_dre",
                    "dre",
                    "dre_abreviacao",
                    "ue",
                    "ue_abreviacao",
                    "nome_turma",
                    "ano",
                    "tipo_ue",
                    "codigo_tipo_ue",
                    "codigo_tipo_escola",
                    "tipo_escola",
                    "duracao_turno",
                    "tipo_turno",
                    "transferido_em",
                ),
                unique_fields=("codigo_escola", "codigo_turma", "ano_letivo"),
                modo_escrita="full_refresh",
                truncate_on_full_sync=True,
            ),
            PhaseConfig(
                nome="etapa_ensino",
                sql=SQL_ETAPA_ENSINO,
                table_name="etapa_ensino",
                source_table="etapa_ensino",
                model_class=EtapaEnsino,
                dto_in=EtapaEnsinoIn,
                pk_field="codigo",
                update_fields=("descricao", "transferido_em"),
                unique_fields=("codigo",),
                modo_escrita="full_refresh",
                truncate_on_full_sync=True,
            ),
        ]
        return fases

    # ------------------------------------------------------------------
    # Execução completa
    # ------------------------------------------------------------------

    def executar(self, fase_inicial: int = 1) -> dict[str, int]:
        """Executa ETL do domínio PEDAGOGICO_DB a partir de ``fase_inicial``.

        Fases:
            1 — componente_curricular
            2 — componente_turma             (por ano letivo)
            3 — atribuicao_componente        (por ano letivo)
            4 — atribuicao_territorio_saber  (por ano letivo)
            5 — componente_curricular_api_eol        (API EOL Postgres)
            6 — componentecurricularhierarquia       (API EOL Postgres)
            7 — componentecurricularpap              (API EOL Postgres)
            8 — componentecurricularplanejamentoregencia (API EOL Postgres)
            9 — turmaitinerarioensinomedio           (API EOL Postgres)
            10 — agrupamento_atribuicao_territorio_saber (API EOL Postgres)
            11 — grade_componente_curricular (por ano letivo)
            12 — turma                       (por ano letivo)
            13 — turma_atribuida_dre_ue      (por ano letivo)
            14 — etapa_ensino                (catálogo)
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

            if config.nome == _AGRUPAMENTO_GERADO_BACKUP:
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
