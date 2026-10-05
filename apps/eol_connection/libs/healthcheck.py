"""Healthcheck helpers para o servico EOL."""

from apps.eol_connection.libs.servico_eol import EOLService


def healthcheck_eol() -> dict:
    """Executa checagem de conectividade com o EOL e retorna status."""
    try:
        service = EOLService()

        if service.validar_conectividade():
            return {"status": "healthy"}

        return {"status": "unhealthy"}

    except Exception:
        return {"status": "unhealthy"}
