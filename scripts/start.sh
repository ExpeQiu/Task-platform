#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ ! -f .env ]; then
  log "Creating .env from .env.example"
  cp .env.example .env
fi

log "Starting infrastructure (postgres, redis)..."
docker compose up -d postgres redis

log "Waiting for postgres..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U taskplatform >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

log "Starting API, worker, beat, simulator..."
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
