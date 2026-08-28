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
    volume: int,
    offset: int,
    continuar: bool,
    fases: list[str] | None,
    anos_letivos: list[int] | None,
    parametros_disparo: dict[str, object] | None,
) -> list[str]:
    """Monta a lista de argumentos para o comando executar_dominio."""
    args = [
        "--dominio",
        dominio,
        "--volume",
        str(volume),
        "--offset",
        str(offset),
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
    volume: int = 100,
    offset: int = 0,
    continuar: bool = False,
    ano_letivo: int | None = None,
    fases: list[str] | None = None,
    anos_letivos: list[int] | None = None,
    parametros_disparo: dict[str, object] | None = None,
) -> str:
    """Executa domínio ETL via fila Celery com retomada por checkpoint."""
    erro_parametros = validar_parametros_dominio(
        dominio,
        ano_letivo=ano_letivo,
        fases=fases,
        anos_letivos=anos_letivos,
    )
    if erro_parametros:
        return f"erro:{erro_parametros}"

    repositorio = RepositorioAuditoriaPostgres()
    continuar_execucao: bool = continuar
    total_linhas_processadas: int = 0

    try:
        while True:
            cp_antes = repositorio.obter_checkpoint_dominio(dominio) or {}
            token_antes = int(cast(int | str, cp_antes.get("token_parada", 0)))

            argumentos = _montar_argumentos(
                dominio,
                volume,
                offset,
                continuar_execucao,
                fases,
                anos_letivos,
                parametros_disparo,
            )
            call_command("executar_dominio", *argumentos)

            checkpoint_depois = repositorio.obter_checkpoint_dominio(dominio)
            situacao = str(
                (checkpoint_depois or {}).get("ultima_situacao", "")
            )
            token_depois = int(
                cast(
                    int | str, (checkpoint_depois or {}).get("token_parada", 0)
                )
            )

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
            "fases": fases,
            "anos_letivos": anos_letivos,
            "parametros_disparo": parametros_disparo,
        }

        raise self.retry(
            exc=erro,
            countdown=60,
            kwargs=kwargs_retry,
        ) from erro
