#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

docker compose -f docker-compose-dev.yml build web_debug
docker compose -f docker-compose-dev.yml up -d postgres keydb
docker compose -f docker-compose-dev.yml run --rm web_debug python manage.py migrate --noinput --fake-initial
docker compose -f docker-compose-dev.yml run --rm web_debug \
  python -m coverage run --source=apps manage.py test \
    apps.controle_auditoria.tests \
    apps.escolas.tests \
    "$@"
docker compose -f docker-compose-dev.yml run --rm web_debug \
  python -m coverage report --show-missing --fail-under=80
