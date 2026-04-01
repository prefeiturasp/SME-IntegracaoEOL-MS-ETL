FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    apt-transport-https \
    ca-certificates \
    unixodbc \
    unixodbc-dev \
    postgresql-client \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor > /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md manage.py /app/
COPY config /app/config
COPY apps /app/apps
COPY requirements /app/requirements
COPY scripts /scripts

RUN pip install --upgrade pip \
    && pip install -r /app/requirements/base.txt

RUN echo "openssl_conf = default_conf" > /etc/ssl/openssl_custom.cnf \
    && echo "[default_conf]" >> /etc/ssl/openssl_custom.cnf \
    && echo "ssl_conf = ssl_sect" >> /etc/ssl/openssl_custom.cnf \
    && echo "[ssl_sect]" >> /etc/ssl/openssl_custom.cnf \
    && echo "system_default = system_default_sect" >> /etc/ssl/openssl_custom.cnf \
    && echo "[system_default_sect]" >> /etc/ssl/openssl_custom.cnf \
    && echo "MinProtocol = TLSv1.0" >> /etc/ssl/openssl_custom.cnf \
    && echo "CipherString = DEFAULT@SECLEVEL=0" >> /etc/ssl/openssl_custom.cnf \
    && echo "Options = UnsafeLegacyServerConnect" >> /etc/ssl/openssl_custom.cnf

ENV OPENSSL_CONF=/etc/ssl/openssl_custom.cnf

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]