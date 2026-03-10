FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc \
    unixodbc-dev \
    tdsodbc \
    freetds-bin \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md manage.py /app/
COPY config /app/config
COPY apps /app/apps

RUN pip install --upgrade pip \
    && pip install -e .

CMD ["python", "manage.py", "executar_dominios_loop", "--continuar"]
