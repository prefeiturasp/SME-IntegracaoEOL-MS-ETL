#!/usr/bin/env bash

docker compose -f docker-compose-dev.yml run --rm etl_auditoria pre-commit run --all-files