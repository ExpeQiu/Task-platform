#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_SUPERUSER="${PG_SUPERUSER:-${USER:-postgres}}"
DB_USER="${DB_USER:-taskplatform}"
DB_PASS="${DB_PASS:-taskplatform}"
DB_NAME="${DB_NAME:-taskplatform}"
PG_SERVICE="${PG_SERVICE:-}"
PG_BIN="${PG_BIN:-}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [infra] $*"; }

stop_docker_infra() {
  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    return 0
  fi
  log "Stopping Docker postgres/redis (use local brew services instead)..."
  docker compose -f "$ROOT/docker-compose.yml" --profile docker-infra stop postgres redis 2>/dev/null || true
  docker compose -f "$ROOT/docker-compose.yml" --profile docker-infra rm -f postgres redis 2>/dev/null || true
}

detect_postgres() {
  if [ -n "$PG_BIN" ] && [ -x "$PG_BIN/psql" ]; then
    return 0
  fi
  local prefix="/opt/homebrew/opt"
  [ -d "/usr/local/opt" ] && prefix="/usr/local/opt"

  # 优先使用已在运行的 brew 服务
  local running
  running="$(brew services list 2>/dev/null | awk '/^postgresql@[0-9]+/ && $2 == "started" { print $1; exit }')"
  if [ -n "$running" ] && [ -x "${prefix}/${running}/bin/psql" ]; then
    PG_BIN="${prefix}/${running}/bin"
    PG_SERVICE="$running"
    return 0
  fi

  local v
  for v in 17 18 16 15; do
    if [ -x "${prefix}/postgresql@${v}/bin/psql" ]; then
      PG_BIN="${prefix}/postgresql@${v}/bin"
      PG_SERVICE="postgresql@${v}"
      return 0
    fi
  done
  return 1
}

if ! detect_postgres; then
  log "ERROR: PostgreSQL not found. Install: brew install postgresql@17 && brew services start postgresql@17"
  exit 1
fi

if ! command -v redis-cli >/dev/null 2>&1; then
  log "ERROR: redis-cli not found. Install: brew install redis && brew services start redis"
  exit 1
fi

ensure_brew_service() {
  local service="$1"
  if brew services list 2>/dev/null | awk -v s="$service" '$1 == s && $2 == "started" { found=1 } END { exit !found }'; then
    log "$service already running"
  else
    log "Starting $service..."
    brew services start "$service"
    sleep 2
  fi
}

stop_docker_infra
ensure_brew_service "${PG_SERVICE:-postgresql@17}"
ensure_brew_service redis

log "Using PostgreSQL: $PG_BIN (service: ${PG_SERVICE:-postgresql@17})"

log "Waiting for postgres at $PG_HOST:$PG_PORT..."
for i in $(seq 1 30); do
  if "$PG_BIN/pg_isready" -h "$PG_HOST" -p "$PG_PORT" >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    log "ERROR: postgres not ready after 30s"
    exit 1
  fi
  sleep 1
done

log "Waiting for redis..."
for i in $(seq 1 30); do
  if redis-cli ping >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    log "ERROR: redis not ready after 30s"
    exit 1
  fi
  sleep 1
done

if ! "$PG_BIN/psql" -h "$PG_HOST" -p "$PG_PORT" -U "$PG_SUPERUSER" -d postgres -tAc \
  "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
  log "Creating role ${DB_USER}..."
  "$PG_BIN/psql" -h "$PG_HOST" -p "$PG_PORT" -U "$PG_SUPERUSER" -d postgres -v ON_ERROR_STOP=1 \
    -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}' CREATEDB;"
fi

if ! "$PG_BIN/psql" -h "$PG_HOST" -p "$PG_PORT" -U "$PG_SUPERUSER" -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  log "Creating database ${DB_NAME}..."
  "$PG_BIN/psql" -h "$PG_HOST" -p "$PG_PORT" -U "$PG_SUPERUSER" -d postgres -v ON_ERROR_STOP=1 \
    -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
fi

log "Local infra ready"
log "  Postgres: postgresql://${DB_USER}:***@${PG_HOST}:${PG_PORT}/${DB_NAME}"
log "  Redis:    redis://localhost:6379"
