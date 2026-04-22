"""Metadados serializáveis de uma fase do pipeline ETL Celery."""

import importlib
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from apps.core.libs.thread_processor import calcular_hash


@dataclass
class BaseEtlFase:
    """Metadados de uma fase do ETL, transmissíveis via broker Celery.

    Substitui ``PhaseConfig`` na fronteira com o Celery: não carrega
    referências a classes Python (model_class, dto_in) — usa caminhos
    de importação resolvidos pelo worker via ``importlib``.
    """

    nome: str
    sql: str
    table_name: str
    source_table: str
    model_path: str
    dto_in_path: str
    pk_field: str | list[str]
    update_fields: list[str]
    unique_fields: list[str]
    db_alias: str
    primeiro_run: bool
    suporta_bulk_insert: bool
    id_execucao: str | None
    numero_fase: int
    total_fases: int
    dominio: str = "ETL"
    task_processamento_path: str = field(default="")
    task_callback_path: str = field(default="")

    def to_dict(self) -> dict:
        """Serializa para dict JSON-safe."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BaseEtlFase":
        """Desserializa de dict."""
        return cls(**data)

    def resolver_model(self) -> Any:
        """Resolve model_path para a classe Django Model via importlib."""
        module_path, class_name = self.model_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    def resolver_dto_in(self) -> Any:
        """Resolve dto_in_path para a classe DTO de entrada via importlib."""
        module_path, class_name = self.dto_in_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    def resolver_task_processamento(self) -> Any:
        """Resolve a task de processamento via importlib."""
        if not self.task_processamento_path:
            return None
        module_path, func_name = self.task_processamento_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)

    def resolver_task_callback(self) -> Any:
        """Resolve a task de callback via importlib."""
        if not self.task_callback_path:
            return None
        module_path, func_name = self.task_callback_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)

    def get_transformer(self) -> Callable[[tuple], tuple[str, str, Any]]:
        """Cria função de transformação Row -> (pk, hash, obj) para o chunk."""
        model_class = self.resolver_model()
        dto_in = self.resolver_dto_in()
        hash_fields = sorted(self.update_fields)
        pk_field = self.pk_field

        if isinstance(pk_field, list):
            def _extrair_pk(dto: Any) -> str:
                return "-".join(str(getattr(dto, f)) for f in pk_field)
        else:
            def _extrair_pk(dto: Any) -> str:
                return str(getattr(dto, pk_field))

        def transform(row: tuple) -> tuple[str, str, Any]:
            dto = dto_in(*row)
            obj = model_class(**dto.to_domain())
            return _extrair_pk(dto), calcular_hash(obj, hash_fields), obj

        return transform
