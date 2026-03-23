"""Configuracoes Django do SME-SGP-MS-ETL."""

import os
import urllib.parse
from pathlib import Path


def _parse_db_url(url: str) -> dict:
    """Faz o parse de uma URL PostgreSQL para dict de configuração Django."""
    parsed = urllib.parse.urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "postgres",
        "PASSWORD": parsed.password or "postgres",
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 5432),
    }


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-inseguro-apenas-desenvolvimento",
)
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.controle_auditoria",
    "apps.escolas",
    "apps.eol_connection",
    "apps.institucional",
    "apps.professores",
    "apps.alunos",
    "apps.pedagogico",
    "apps.programas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

URL_BANCO_INSTITUCIONAL = os.getenv(
    "URL_BANCO_INSTITUCIONAL",
    "postgresql://postgres:postgres@localhost:5432/institucional_db",
)
URL_BANCO_PROFESSORES = os.getenv(
    "URL_BANCO_PROFESSORES",
    "postgresql://postgres:postgres@localhost:5432/professores_db",
)
URL_BANCO_ALUNOS = os.getenv(
    "URL_BANCO_ALUNOS",
    "postgresql://postgres:postgres@localhost:5432/alunos_db",
)
URL_BANCO_PEDAGOGICO = os.getenv(
    "URL_BANCO_PEDAGOGICO",
    "postgresql://postgres:postgres@localhost:5432/pedagogico_db",
)
URL_BANCO_PROGRAMAS = os.getenv(
    "URL_BANCO_PROGRAMAS",
    "postgresql://postgres:postgres@localhost:5432/programas_db",
)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "postgres"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    },
    "institucional_db": _parse_db_url(URL_BANCO_INSTITUCIONAL),
    "professores_db": _parse_db_url(URL_BANCO_PROFESSORES),
    "alunos_db": _parse_db_url(URL_BANCO_ALUNOS),
    "pedagogico_db": _parse_db_url(URL_BANCO_PEDAGOGICO),
    "programas_db": _parse_db_url(URL_BANCO_PROGRAMAS),
}

DATABASE_ROUTERS = ["config.db_router.DominioRouter"]

AUTH_PASSWORD_VALIDATORS: list[dict[str, object]] = []

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

NOME_APLICACAO = os.getenv("NOME_APLICACAO", "SME-SGP-MS-ETL")
AMBIENTE_APLICACAO = os.getenv("AMBIENTE_APLICACAO", "local")
NIVEL_LOG = os.getenv("NIVEL_LOG", "INFO")
URL_BANCO_AUDITORIA = os.getenv(
    "URL_BANCO_AUDITORIA",
    "postgresql://postgres:postgres@localhost:5432/sinc_rec_db",
)
URL_KEYDB = os.getenv("URL_KEYDB", "redis://localhost:6379/0")
EOL_DB = os.getenv("EOL_DB", "")
INTERVALO_EXECUCAO_ETL_SEGUNDOS = int(
    os.getenv("INTERVALO_EXECUCAO_ETL_SEGUNDOS", "60")
)
API_KEY = os.getenv("API_KEY", "")
API_KEY_HEADER = os.getenv("API_KEY_HEADER", "X-API-Key")

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.controle_auditoria.api.authentication.ApiKeyAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SME-SGP-MS-ETL API",
    "DESCRIPTION": "API de controle e auditoria do ETL",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": API_KEY_HEADER,
            }
        }
    },
    "SECURITY": [{"ApiKeyAuth": []}],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "padrao": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "padrao",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": NIVEL_LOG,
    },
}
