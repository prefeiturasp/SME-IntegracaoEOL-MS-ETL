"""Tasks assincronas do ETL."""

from typing import Any, cast

from celery import Task
from django.core.management import call_command

from apps.controle_auditoria.libs.celery_app import aplicacao_celery
from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)


@aplicacao_celery.task(name="etl.verificacao_saude")
def verificar_saude() -> str:
    """Task mínima para validar worker e broker."""
    return "ok"


@aplicacao_celery.task(name="etl.executar_dominio", bind=True, max_retries=5)
def executar_dominio_task(
    self: Task,
    dominio: str,
    volume: int = 100,
    offset: int = 0,
    continuar: bool = False,
    ano_letivo: int | None = None,
) -> str:
    """Executa domínio ETL via fila Celery com retomada por checkpoint."""
    repositorio = RepositorioAuditoriaPostgres()
    continuar_execucao: bool = continuar
    total_linhas_processadas: int = 0

    try:
        while True:
            checkpoint_antes = repositorio.obter_checkpoint_dominio(dominio)

            token_antes_valor = (checkpoint_antes or {}).get("token_parada", 0)
            token_antes = int(cast(int | str, token_antes_valor))

            argumentos: list[str] = [
                "--dominio",
                dominio,
                "--volume",
                str(volume),
                "--offset",
                str(offset),
            ]

            if continuar_execucao:
                argumentos.append("--continuar")
            if ano_letivo is not None:
                argumentos += ["--ano-letivo", str(ano_letivo)]

            call_command("executar_dominio", *argumentos)

            checkpoint_depois = repositorio.obter_checkpoint_dominio(dominio)

            situacao = str(
                (checkpoint_depois or {}).get("ultima_situacao", "")
            )
            token_depois_valor = (checkpoint_depois or {}).get(
                "token_parada", 0
            )
            token_depois = int(cast(int | str, token_depois_valor))

            linhas = max(token_depois - token_antes, 0)
            total_linhas_processadas += linhas

            if situacao == "concluido" or linhas < volume:
                break

            continuar_execucao = True

        return f"ok:{total_linhas_processadas}"

    except Exception as erro:
        kwargs_retry: dict[str, Any] = {
            "dominio": dominio,
            "volume": volume,
            "offset": offset,
            "continuar": True,
            "ano_letivo": ano_letivo,
        }

        raise self.retry(
            exc=erro,
            countdown=60,
            kwargs=kwargs_retry,
        ) from erro
