"""Base para orquestradores assíncronos de pipeline ETL via Celery."""

import logging
from typing import Any
from uuid import UUID

from celery import chord, group

from apps.eol_connection.libs.servico_eol import EOLService

from .base_etl_chunck import BaseEtlChunk
from .base_etl_fase import BaseEtlFase
from ..tasks import processar_chunk, finalizar_fase

logger = logging.getLogger(__name__)


class BaseEtlOrquestrador:
    """Base para orquestradores de Chords Celery."""

    def __init__(
        self,
        dominio: str,
        service: Any,
        task_processamento: Any = None,
        task_callback: Any = None,
        db_alias: str = "default",
        id_execucao: UUID | None = None,
        primeiro_run: bool = False,
        eol: EOLService | None = None,
    ) -> None:
        self._dominio = dominio
        self._service = service
        self._processar_task = task_processamento or processar_chunk
        self._callback_task = task_callback or finalizar_fase
        self._db_alias = db_alias
        self._id_execucao = id_execucao
        self._primeiro_run = primeiro_run
        self._eol = eol or EOLService()

    @property
    def id_execucao(self) -> UUID | None:
        """ID único desta execução do pipeline."""
        return self._id_execucao

    @property
    def service(self) -> Any:
        """Instância do serviço de domínio orquestrado."""
        return self._service

    def _fase_meta_from_config(
        self,
        config: Any,
        numero_fase: int,
        total_fases: int,
    ) -> BaseEtlFase:
        """Constrói BaseEtlFase a partir de um PhaseConfig do service."""
        proc_mod = getattr(self._processar_task, "__module__", "mock")
        proc_name = getattr(self._processar_task, "__name__", "task")
        call_mod = getattr(self._callback_task, "__module__", "mock")
        call_name = getattr(self._callback_task, "__name__", "callback")

        options = {
            "primeiro_run": self._primeiro_run,
            "task_processamento_path": f"{proc_mod}.{proc_name}",
            "task_callback_path": f"{call_mod}.{call_name}",
        }
        return config.to_meta(
            dominio=self._dominio,
            db_alias=self._db_alias,
            id_execucao=str(self._id_execucao) if self._id_execucao else None,
            numero_fase=numero_fase,
            total_fases=total_fases,
            options=options,
        )

    def lancar(self, fase_inicial: int = 1) -> None:
        """Publica o chord da fase inicial."""
        fases = self._service._fases
        total = len(fases)

        todas_fases = [
            self._fase_meta_from_config(config, i, total)
            for i, config in enumerate(fases, 1)
        ]
        todas_fases_dict = [fm.to_dict() for fm in todas_fases]

        fase_inicial_meta = todas_fases[fase_inicial - 1]
        leitor = BaseEtlChunk(
            task_processamento=self._processar_task,
            eol=self._eol,
        )
        tasks = leitor.criar_grupo(fase_inicial_meta)

        if not tasks:
            logger.warning(
                "[%s] Fase %d sem chunks — avançando via callback.",
                self._dominio,
                fase_inicial,
            )
            self._callback_task.apply_async(
                args=[[], fase_inicial_meta.to_dict(), todas_fases_dict]
            )
            return

        callback = self._callback_task.s(
            fase_inicial_meta.to_dict(), todas_fases_dict
        )
        chord(group(tasks))(callback)
        logger.info(
            "[%s] Chord da fase %d/%d lançado (%d tasks).",
            self._dominio,
            fase_inicial,
            total,
            len(tasks),
        )


class GenericEtlOrquestrador(BaseEtlOrquestrador):
    """Orquestrador genérico que utiliza as tasks padrões do Core."""

    def __init__(self, service_class: Any = None, **kwargs: Any) -> None:
        service_class = service_class or kwargs.pop("service_class", None)
        dominio = kwargs.pop("dominio", "ETL")
        db_alias = kwargs.pop("db_alias", f"{dominio}_db")
        
        # Instancia o service se for uma classe, senão usa a instância
        if isinstance(service_class, type):
            service = service_class(db_alias=db_alias, **kwargs)
        else:
            service = service_class
            
        super().__init__(
            dominio=dominio,
            service=service,
            db_alias=db_alias,
            **kwargs
        )
