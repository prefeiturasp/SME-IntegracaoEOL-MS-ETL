"""Metadados serializáveis de uma fase do pipeline ETL Celery."""

import importlib
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, fields
from typing import Any

from apps.core.libs.thread_processor import calcular_hash_linha


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

    def salt_hash(self) -> str:
        """Salt da versão da transformação, igual ao do caminho síncrono."""
        return f"{self.table_name}|{'|'.join(sorted(self.update_fields))}"

    def get_transformer(self) -> Callable[[tuple], tuple[str, str, Any]]:
        """Cria a transformação leve Row -> (pk, hash, linha crua).

        Espelha ``BaseEtlService._criar_transform``: os dois caminhos, o
        síncrono e o orquestrado por Celery, precisam gerar exatamente o
        mesmo hash para a mesma linha — caso contrário, alternar entre eles
        invalidaria todos os hashes e forçaria a regravação total.
        """
        dto_in = self.resolver_dto_in()
        pk_field = self.pk_field
        campos = pk_field if isinstance(pk_field, list) else [pk_field]
        salt = self.salt_hash()

        try:
            nomes = [f.name for f in fields(dto_in)]
            pk_idx: tuple[int, ...] | None = tuple(
                nomes.index(campo) for campo in campos
            )
        except (ValueError, TypeError):
            pk_idx = None

        def transform(row: tuple) -> tuple[str, str, Any]:
            if pk_idx is not None:
                pk = "-".join(str(row[i]) for i in pk_idx)
            else:
                dto = dto_in(*row)
                pk = "-".join(str(getattr(dto, f)) for f in campos)
            return pk, calcular_hash_linha(row, salt), row

        return transform

    def materializar(self, row: tuple) -> Any:
        """Constrói o objeto do model a partir da linha crua da origem.

        O construtor fica fora do dataclass de propósito: ``to_dict`` usa
        ``asdict`` para trafegar a fase pelo broker, e uma função aqui
        quebraria a serialização.
        """
        construtor = self.__dict__.get("_materializador")
        if construtor is None:
            model_class = self.resolver_model()
            dto_in = self.resolver_dto_in()

            def construtor(linha: tuple) -> Any:  # noqa: F811
                return model_class(**dto_in(*linha).to_domain())

            self.__dict__["_materializador"] = construtor
        return construtor(row)
