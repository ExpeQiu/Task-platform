#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ ! -f .env ]; then
  log "Creating .env from .env.example"
  cp .env.example .env
fi

log "Starting local infrastructure (postgres, redis)..."
"$ROOT/scripts/infra-local.sh"

log "Starting API, worker, beat, simulator (Docker -> host infra)..."
export DATABASE_URL="postgresql+asyncpg://taskplatform:taskplatform@host.docker.internal:5432/taskplatform"
export DATABASE_URL_SYNC="postgresql://taskplatform:taskplatform@host.docker.internal:5432/taskplatform"
export REDIS_URL="redis://host.docker.internal:6379/0"
export CELERY_BROKER_URL="redis://host.docker.internal:6379/1"
export CELERY_RESULT_BACKEND="redis://host.docker.internal:6379/2"
docker compose up -d api worker beat simulator

log "Waiting for API health..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

log "Seeding demo data..."
docker compose exec -T api python /app/scripts/seed_demo_data.py || true

if [ "${START_WEB:-1}" = "1" ]; then
  log "Starting web frontend..."
  docker compose up -d web
fi

log "Task Platform started."
log "  API:       http://localhost:8000"
log "  Web:       http://localhost:3000"
log "  Simulator: http://localhost:8100"
log "  Docs:      http://localhost:8000/docs"
