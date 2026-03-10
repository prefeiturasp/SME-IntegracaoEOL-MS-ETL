"""Tasks assincronas do ETL."""

from django.core.management import call_command

from apps.controle_auditoria.libs.celery_app import aplicacao_celery


@aplicacao_celery.task(name="etl.verificacao_saude")
def verificar_saude() -> str:
    """Task minima para validar worker e broker."""
    return "ok"


@aplicacao_celery.task(name="etl.executar_dominio")
def executar_dominio_task(
    dominio: str,
    volume: int = 100,
    offset: int = 0,
    continuar: bool = False,
) -> str:
    """Executa dominio ETL via fila Celery."""
    argumentos = [
        "--dominio",
        dominio,
        "--volume",
        str(volume),
        "--offset",
        str(offset),
    ]
    if continuar:
        argumentos.append("--continuar")

    call_command("executar_dominio", *argumentos)
    return "ok"
