"""Tasks assincronas do ETL."""

import json
from typing import Any, cast

from celery import Task
from django.core.management import call_command

from apps.controle_auditoria.libs.celery_app import aplicacao_celery
from apps.controle_auditoria.libs.dominios import validar_parametros_dominio
from apps.controle_auditoria.libs.repositorio_auditoria import (
    RepositorioAuditoriaPostgres,
)


@aplicacao_celery.task(name="etl.verificacao_saude")
def verificar_saude() -> str:
    """Task mínima para validar worker e broker."""
    return "ok"


def _montar_argumentos(
    dominio: str,
    continuar: bool,
    fases: list[str] | None,
    anos_letivos: list[int] | None,
    parametros_disparo: dict[str, object] | None,
) -> list[str]:
    """Monta a lista de argumentos para o comando executar_dominio."""
    args = [
        "--dominio",
        dominio,
    ]
    if continuar:
        args.append("--continuar")
    if fases:
        args += ["--fases", *fases]
    if anos_letivos:
        args += ["--anos-letivos", *[str(ano) for ano in anos_letivos]]
    if parametros_disparo:
        args += [
            "--parametros-disparo",
            json.dumps(parametros_disparo, default=str),
        ]
    return args


@aplicacao_celery.task(name="etl.executar_dominio", bind=True, max_retries=5)
def executar_dominio_task(
    self: Task,
    dominio: str,
    continuar: bool = False,
    ano_letivo: int | None = None,
    fases: list[str] | None = None,
    anos_letivos: list[int] | None = None,
    parametros_disparo: dict[str, object] | None = None,
) -> str:
    """Executa domínio ETL via fila Celery com retomada por checkpoint."""
    parametros_disparo_task = dict(parametros_disparo or {})
    parametros_disparo_task.update(
        {
            "celery_task_id": self.request.id,
            "celery_worker": self.request.hostname,
            "celery_retries": self.request.retries,
        }
    )
    erro_parametros = validar_parametros_dominio(
        dominio,
        ano_letivo=ano_letivo,
        fases=fases,
        anos_letivos=anos_letivos,
    )
    if erro_parametros:
        return f"erro:{erro_parametros}"

    repositorio = RepositorioAuditoriaPostgres()

    try:
        cp_antes = repositorio.obter_checkpoint_dominio(dominio) or {}
        token_antes = int(cast(int | str, cp_antes.get("token_parada", 0)))
        argumentos = _montar_argumentos(
            dominio,
            continuar,
            fases,
            anos_letivos,
            parametros_disparo_task,
        )
        call_command("executar_dominio", *argumentos)
        checkpoint_depois = repositorio.obter_checkpoint_dominio(dominio) or {}
        token_depois = int(
            cast(int | str, checkpoint_depois.get("token_parada", 0))
        )
        total_linhas_processadas = max(token_depois - token_antes, 0)
        return f"ok:{total_linhas_processadas}"

    except Exception as erro:
        kwargs_retry: dict[str, Any] = {
            "dominio": dominio,
            "continuar": True,
            "fases": fases,
            "anos_letivos": anos_letivos,
            "parametros_disparo": parametros_disparo_task,
        }

        raise self.retry(
            exc=erro,
            countdown=60,
            kwargs=kwargs_retry,
        ) from erro
