"""Configuracoes Django do SME-IntegracaoEOL-MS-ETL."""

import os
import urllib.parse
from pathlib import Path
from typing import Any

from django.core.exceptions import ImproperlyConfigured

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
_POOL_OPTIONS = {
    "POOL_SIZE": DB_POOL_SIZE,
    "MAX_OVERFLOW": 0,
    "POOL_TIMEOUT": 30,
    "POOL_RECYCLE": 1800,
    "PRE_PING": True,
}

THREAD_POOL_MAX_WORKERS = int(os.getenv("THREAD_POOL_MAX_WORKERS", "4"))
THREAD_POOL_CHUNK_TIMEOUT = int(os.getenv("THREAD_POOL_CHUNK_TIMEOUT", "120"))

def _parse_db_url(url: Any) -> dict:
    """Faz o parse de uma URL PostgreSQL para dict de configuração Django."""
    if not url:
        # Fallback para evitar ImproperlyConfigured no CI/Testes
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }

    # Garante que a URL é uma string para evitar que urlparse retorne bytes
    if isinstance(url, bytes):
        url = url.decode("utf-8")

    parsed = urllib.parse.urlparse(str(url))
    return {
        "ENGINE": "dj_db_conn_pool.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "postgres",
        "PASSWORD": parsed.password or "postgres",
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 5432),
        "POOL_OPTIONS": _POOL_OPTIONS,
        "OPTIONS": {"options": "-c synchronous_commit=off"},
    }


SILENCED_SYSTEM_CHECKS = [
    "models.E030",  # index names duplicados entre models
    "models.W035",  # db_table duplicado entre apps (intencional por multi-db)
]


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("DJANGO_DEBUG", "1") == "0":  # Produção
        raise ImproperlyConfigured(
            "A variável DJANGO_SECRET_KEY é obrigatória em produção."
        )
    # Fallback para desenvolvimento baseado no ambiente para não deixar chave exposta
    SECRET_KEY = os.getenv("HOSTNAME")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")
]

INSTALLED_APPS = [
    "elasticapm.contrib.django",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.core",
    "apps.controle_auditoria",
    "apps.eol_connection",
    "apps.institucional",
    "apps.professores",
    "apps.alunos",
    "apps.pedagogico",
    "apps.programas",
]

MIDDLEWARE = [
    "elasticapm.contrib.django.middleware.TracingMiddleware",
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


def _parse_readonly_db(url: Any) -> dict[str, Any]:
    """Faz o parse de uma URL mssql+pyodbc para dict de configuração Django."""
    if not url:
        # Fallback para evitar ImproperlyConfigured no CI/Testes
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }

    # Garante que a URL é uma string para evitar que urlparse retorne bytes
    if isinstance(url, bytes):
        url = url.decode("utf-8")

    parsed = urllib.parse.urlparse(str(url))
    query = urllib.parse.parse_qs(parsed.query)

    def _get_param(name: str, default: str = "") -> str:
        return query.get(name, [default])[0]

    options: dict[str, Any] = {}
    driver = _get_param("driver")
    if driver:
        options["driver"] = driver.replace("+", " ")
    trust = _get_param("TrustServerCertificate")
    if trust:
        options["TrustServerCertificate"] = trust
    readonly = _get_param("ReadOnly")
    if readonly:
        options["ReadOnly"] = readonly
    encrypt_raw = _get_param("Encrypt", "no")
    options["Encrypt"] = False if encrypt_raw.lower() == "no" else encrypt_raw

    return {
        "ENGINE": "mssql",
        "NAME": parsed.path.lstrip("/"),
        "USER": urllib.parse.unquote_plus(parsed.username or ""),
        "PASSWORD": urllib.parse.unquote_plus(parsed.password or ""),
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 1433),
        "OPTIONS": options,
        "TEST": {"MIGRATE": False},
    }


URL_BANCO_INSTITUCIONAL = os.getenv("URL_BANCO_INSTITUCIONAL")
URL_BANCO_PROFESSORES = os.getenv("URL_BANCO_PROFESSORES")
URL_BANCO_ALUNOS = os.getenv("URL_BANCO_ALUNOS")
URL_BANCO_PEDAGOGICO = os.getenv("URL_BANCO_PEDAGOGICO")
URL_BANCO_PROGRAMAS = os.getenv("URL_BANCO_PROGRAMAS")

DATABASES = {
    "default": {
        "ENGINE": "dj_db_conn_pool.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "postgres"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "POOL_OPTIONS": _POOL_OPTIONS,
        "OPTIONS": {"options": "-c synchronous_commit=off"},
    },
    "eol_db": _parse_readonly_db(os.getenv("EOL_DB", "")),
    "core_sso_db": _parse_readonly_db(os.getenv("CORE_SSO_DB", "")),
    "institucional_db": _parse_db_url(URL_BANCO_INSTITUCIONAL),
    "professores_db": _parse_db_url(URL_BANCO_PROFESSORES),
    "alunos_db": _parse_db_url(URL_BANCO_ALUNOS),
    "pedagogico_db": _parse_db_url(URL_BANCO_PEDAGOGICO),
    "programas_db": _parse_db_url(URL_BANCO_PROGRAMAS),
}

DATABASE_ROUTERS = ["config.db_router.DominioRouter"]

# W035 já silenciado acima.

AUTH_PASSWORD_VALIDATORS: list[dict[str, object]] = []

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

NOME_APLICACAO = os.getenv("NOME_APLICACAO", "SME-IntegracaoEOL-MS-ETL")
AMBIENTE_APLICACAO = os.getenv("AMBIENTE_APLICACAO", "local")
NIVEL_LOG = os.getenv("NIVEL_LOG", "INFO")
LOG_ENVIRONMENT = os.getenv("LOG_ENVIRONMENT", AMBIENTE_APLICACAO)
ENABLE_RABBITMQ_LOGGING = os.getenv("ENABLE_RABBITMQ_LOGGING", "0") == "1"
URL_KEYDB = os.getenv("URL_KEYDB", "redis://localhost:6379/0")
EOL_DB = os.getenv("EOL_DB", "")
CORE_SSO_DB = os.getenv("CORE_SSO_DB", "")
INTERVALO_EXECUCAO_ETL_SEGUNDOS = int(
    os.getenv("INTERVALO_EXECUCAO_ETL_SEGUNDOS", "60")
)
API_KEY = os.getenv("API_KEY", "dev-key-default")
API_KEY_HEADER = os.getenv("API_KEY_HEADER", "X-API-Key")
CELERY_BROKER_URL = URL_KEYDB
CELERY_RESULT_BACKEND = URL_KEYDB
# Execução síncrona automática em testes/CI
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "1") == "1"

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
    "TITLE": "SME-IntegracaoEOL-MS-ETL API",
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

_logging_handlers: dict = {
    "console": {
        "class": "logging.StreamHandler",
        "formatter": "json",
    }
}

if ENABLE_RABBITMQ_LOGGING:
    _logging_handlers["rabbitmq"] = {
        "level": os.getenv("RABBITMQ_LOG_LEVEL", "INFO"),
        "class": "apps.core.libs.rabbitmq_handler.RabbitMQHandler",
        "host": os.getenv("RABBITMQ_HOST", ""),
        "virtual_host": os.getenv("RABBITMQ_VIRTUAL_HOST", "/"),
        "queue": os.getenv("RABBITMQ_LOG_QUEUE", ""),
        "username": os.getenv("RABBITMQ_USERNAME", ""),
        "password": os.getenv("RABBITMQ_PASSWORD", ""),
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "rename_fields": {
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        }
    },
    "handlers": _logging_handlers,
    "loggers": {
        "etl_apps": {
            "handlers": ["console"] + (["rabbitmq"] if ENABLE_RABBITMQ_LOGGING else []),
            "level": NIVEL_LOG,
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": NIVEL_LOG,
    },
}

ELASTIC_APM = {
    "SERVICE_NAME": os.getenv("ELASTIC_APM_SERVICE_NAME", NOME_APLICACAO),
    "SECRET_TOKEN": os.getenv("ELASTIC_APM_SECRET_TOKEN", ""),
    "SERVER_URL": os.getenv("ELASTIC_APM_SERVER_URL", "http://localhost:8200"),
    "ENVIRONMENT": os.getenv("ELASTIC_APM_ENVIRONMENT", AMBIENTE_APLICACAO),
    "ENABLED": os.getenv("ELASTIC_APM_ENABLED", "0") == "1",
    "CAPTURE_HEADERS": os.getenv("ELASTIC_APM_CAPTURE_HEADERS", "1") == "1",
    "TRANSACTION_SAMPLE_RATE": float(os.getenv("ELASTIC_APM_TRANSACTION_SAMPLE_RATE", "0.3")),
    "METRICS_INTERVAL": os.getenv("ELASTIC_APM_METRICS_INTERVAL", "10s"),
    "FLUSH_INTERVAL": os.getenv("ELASTIC_APM_FLUSH_INTERVAL", "10s"),
    "MAX_BATCH_EVENT_COUNT": int(os.getenv("ELASTIC_APM_MAX_BATCH_EVENT_COUNT", "1000")),
    "MAX_QUEUE_EVENT_COUNT": int(os.getenv("ELASTIC_APM_MAX_QUEUE_EVENT_COUNT", "1000")),
    "TRANSACTION_MAX_SPANS": int(os.getenv("ELASTIC_APM_TRANSACTION_MAX_SPANS", "500")),
    "LOG_LEVEL": os.getenv("ELASTIC_APM_LOG_LEVEL", "INFO"),
}
