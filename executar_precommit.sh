#!/usr/bin/env bash

docker compose -f docker-compose-dev.yml run --rm web_debug pre-commit run --all-files