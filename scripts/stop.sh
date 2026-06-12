#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "Stopping Task Platform app services..."
docker compose stop api worker beat simulator web 2>/dev/null || true
docker compose rm -f api worker beat simulator web 2>/dev/null || true
log "Stopped. (Postgres/Redis 使用本地 brew 服务，未被停止)"
