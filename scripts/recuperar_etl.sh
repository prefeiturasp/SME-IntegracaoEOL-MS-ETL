#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ETL_ENV_FILE:-$ROOT_DIR/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

API_BASE_URL="${ETL_API_BASE_URL:-http://localhost:${PORT_WEB:-8068}/api/v1}"
API_KEY_HEADER="${API_KEY_HEADER:-X-API-Key}"
API_KEY="${API_KEY:-}"

if [[ -z "$API_KEY" ]]; then
  echo "API_KEY não informado. Defina no ambiente ou em $ENV_FILE." >&2
  exit 1
fi

post_json() {
  local path="$1"
  local payload="$2"

  echo "POST $path payload: $payload"
  curl -fsS \
    --connect-timeout 10 \
    --max-time 60 \
    --retry 3 \
    --retry-connrefused \
    --retry-delay 5 \
    -X POST "$API_BASE_URL$path" \
    -H "$API_KEY_HEADER: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload"
  echo
}

post_json "/execucoes/limpar-orfas/" "{}"
post_json "/execucoes/retomar/" '{"max_tentativas":3}'
