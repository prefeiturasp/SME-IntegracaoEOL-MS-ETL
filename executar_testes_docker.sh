#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

docker compose -f docker-compose-dev.yml build etl_auditoria

docker compose -f docker-compose-dev.yml up -d postgres keydb

docker compose -f docker-compose-dev.yml run --rm etl_auditoria \
  python manage.py migrate --noinput --fake-initial

docker compose -f docker-compose-dev.yml run --rm etl_auditoria \
  python -m coverage run --source=apps manage.py test --no-input

docker compose -f docker-compose-dev.yml run --rm etl_auditoria \
  python -m coverage report --show-missing --fail-under=80