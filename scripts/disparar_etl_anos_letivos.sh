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
VOLUME="${ETL_VOLUME:-500}"
PRIORIDADE="${ETL_PRIORIDADE:-5}"
CONTINUAR="${ETL_CONTINUAR:-true}"
DATA_REFERENCIA="${ETL_DATA_REFERENCIA:-$(date +%F)}"
DRY_RUN="${ETL_DRY_RUN:-false}"

DOMINIOS_SEM_ANOS_LETIVOS="${ETL_DOMINIOS_SEM_ANOS_LETIVOS:-institucional}"
DOMINIOS_COM_ANOS_LETIVOS="${ETL_DOMINIOS_COM_ANOS_LETIVOS:-professores pedagogico programas alunos}"

ANO_MINIMO_ANTERIORES="${ETL_ANO_MINIMO_ANTERIORES:-}"
INTERVALO_MESES_ANTERIORES="${ETL_INTERVALO_MESES_ANTERIORES:-0}"

if [[ -z "$API_KEY" ]]; then
  echo "API_KEY não informado. Defina no ambiente ou em $ENV_FILE." >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

read -r ANO_VIGENTE MES DIA < <(
  "$PYTHON_BIN" - "$DATA_REFERENCIA" <<'PY'
from datetime import date
import sys

try:
    hoje = date.fromisoformat(sys.argv[1])
except ValueError as erro:
    raise SystemExit(f"ETL_DATA_REFERENCIA inválida: {sys.argv[1]}") from erro

print(hoje.year, hoje.month, hoje.day)
PY
)

anos=("$ANO_VIGENTE")

case "$DIA" in
  8)
    anos+=("$((ANO_VIGENTE - 1))")
    ;;
  15)
    anos+=("$((ANO_VIGENTE - 2))")
    ;;
  22)
    anos+=("$((ANO_VIGENTE - 3))")
    ;;
  29)
    anos+=("$((ANO_VIGENTE - 4))")
    ;;
esac

if [[ -n "$ANO_MINIMO_ANTERIORES" && "$INTERVALO_MESES_ANTERIORES" -gt 0 ]]; then
  if [[ "$DIA" -eq 1 && $(((MES - 1) % INTERVALO_MESES_ANTERIORES)) -eq 0 ]]; then
    for ((ano = ANO_VIGENTE - 5; ano >= ANO_MINIMO_ANTERIORES; ano--)); do
      anos+=("$ano")
    done
  fi
fi

json_base() {
  printf '{"volume":%s,"continuar":%s,"prioridade":%s' \
    "$VOLUME" "$CONTINUAR" "$PRIORIDADE"
}

json_com_anos_letivos() {
  local lista="["
  local sep=""
  local ano

  for ano in "${anos[@]}"; do
    lista="${lista}${sep}${ano}"
    sep=","
  done
  lista="${lista}]"

  printf '%s,"anos_letivos":%s}' "$(json_base)" "$lista"
}

json_sem_ano() {
  printf '%s}' "$(json_base)"
}

post_dominio() {
  local dominio="$1"
  local payload="$2"

  echo "Enfileirando domínio '$dominio' com payload: $payload"
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "DRY_RUN ativo: chamada HTTP ignorada."
    return
  fi

  curl -fsS \
    --retry 3 \
    --retry-delay 5 \
    -X POST "$API_BASE_URL/dominios/$dominio/executar/" \
    -H "$API_KEY_HEADER: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload"
  echo
}

echo "Data de referência: $DATA_REFERENCIA"
echo "Anos letivos selecionados: ${anos[*]}"

for dominio in $DOMINIOS_SEM_ANOS_LETIVOS; do
  post_dominio "$dominio" "$(json_sem_ano)"
done

for dominio in $DOMINIOS_COM_ANOS_LETIVOS; do
  post_dominio "$dominio" "$(json_com_anos_letivos)"
done
