#!/usr/bin/env bash
# scripts/railway-bootstrap.sh
#
# Заполняет «ручной слой» переменных Railway для kkr-hotel-assist после первого
# `railway config apply` — то, что IaC-DSL не может выразить (композиция DSN,
# секреты). См. .railway/README.md.
#
# Что делает:
#   1. Протягивает секреты приложения из локального .env в сервис `app`.
#   2. Выводит KKR_POSTGRES_DSN (вставляет +asyncpg) из DATABASE_URL managed-Postgres.
#   3. Копирует KKR_LANGFUSE_PUBLIC_KEY / SECRET_KEY из .env (облачный Langfuse), если заданы.
#
# Требования: railway (в PATH), jq. Запускать из корня репо после `railway link`.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT}/.env"
APP_SVC="app"
PG_SVC="postgres"

log() { printf '\033[1;34m▸ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m⚠ %s\033[0m\n' "$*" >&2; }
die() { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

command -v railway >/dev/null || die "railway CLI не найден в PATH — выполни source ~/.railway/env"
command -v jq      >/dev/null || die "нужен jq"
railway status --json >/dev/null 2>&1 || die "проект не привязан — сначала `railway link`"

# Загрузить .env (не перезаписывает уже экспортированные переменные окружения).
if [[ -f "$ENV_FILE" ]]; then
  log "читаю $ENV_FILE"
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
else
  die ".env не найден ($ENV_FILE) — не откуда брать секреты"
fi

# .env может содержать устаревший RAILWAY_TOKEN — он перебивает OAuth-сессию CLI.
unset RAILWAY_TOKEN RAILWAY_API_TOKEN

# ─── helpers ──────────────────────────────────────────────────────────────
svc_var() {
  railway variable list --service "$1" --json 2>/dev/null | jq -r --arg k "$2" '.[$k] // empty'
}
set_var() {
  log "$APP_SVC: ${1%%=*}"   # печатаем только имя ключа — без значения секрета
  railway variable set "$1" --service "$APP_SVC" >/dev/null
}

# ─── 1. Секреты приложения (.env → сервис app) ────────────────────────────
APP_SECRET_KEYS=(
  KKR_TELEGRAM_BOT_TOKEN
  KKR_LLM_MODEL
  KKR_ZAI_API_KEY KKR_ZAI_API_BASE
  KKR_OPENROUTER_API_KEY KKR_OPENROUTER_API_BASE KKR_OPENROUTER_REASONING_EFFORT
  KKR_TAVILY_API_KEY
  KKR_MAILTRAP_API_KEY KKR_MAILTRAP_SIGNING_SECRET KKR_MAILTRAP_BASE_URL
  KKR_MAILTRAP_INBOX_ID KKR_MAILTRAP_FROM_EMAIL
  KKR_LANGFUSE_PUBLIC_KEY KKR_LANGFUSE_SECRET_KEY
)
log "секреты приложения → $APP_SVC"
for k in "${APP_SECRET_KEYS[@]}"; do
  v="${!k:-}"
  [[ -n "$v" ]] || { warn "$k не задан — пропускаю"; continue; }
  set_var "$k=$v"
done

# ─── 2. KKR_POSTGRES_DSN (+asyncpg) ────────────────────────────────────────
PG_URL="$(svc_var "$PG_SVC" "DATABASE_URL")"
[[ -n "$PG_URL" ]] || die "не получил DATABASE_URL из сервиса $PG_SVC (он провижен?)"
PG_ASYNCPG="$(printf '%s' "$PG_URL" | sed 's|^postgresql://|postgresql+asyncpg://|')"
log "DB: общий сервер получен"
set_var "KKR_POSTGRES_DSN=$PG_ASYNCPG"
# KKR_LANGGRAPH_DSN уже связан в railway.ts (db.env.DATABASE_URL).

log "готово."
warn "проверь:  railway deployment list --service app --json   (ждать status: SUCCESS)"
warn "не забудь: webhook Mailtrap → https://<app-domain>.up.railway.app/send_test_email"
