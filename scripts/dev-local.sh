#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOG_DIR="${LOG_DIR:-/tmp/task-platform-logs}"
VENV="${VENV:-/tmp/task-platform-api-venv}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ ! -d "$VENV" ]; then
  log "Creating Python venv at $VENV"
  python3.12 -m venv "$VENV"
  source "$VENV/bin/activate"
  pip install -q --upgrade pip setuptools wheel
  pip install -q -r "$ROOT/apps/api/requirements.txt"
  pip install -q -r "$ROOT/packages/agent-simulator/requirements.txt"
else
  source "$VENV/bin/activate"
fi

set -a
# shellcheck disable=SC1091
source "$ROOT/.env"
set +a

mkdir -p "$LOG_DIR"

log "Starting infrastructure (postgres, redis)..."
docker compose up -d postgres redis

log "Waiting for postgres..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U taskplatform >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

start_bg() {
  local name="$1"
  local pid_file="$LOG_DIR/${name}.pid"
  local log_file="$LOG_DIR/${name}.log"
  shift
  if [ -f "$pid_file" ]; then
    local old_pid
    old_pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
      kill "$old_pid" 2>/dev/null || true
      sleep 1
    fi
  fi
  nohup "$@" > "$log_file" 2>&1 &
  echo $! > "$pid_file"
  log "Started $name pid=$(cat "$pid_file") log=$log_file"
}

if ! curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
  start_bg api bash -lc "cd '$ROOT/apps/api' && source '$VENV/bin/activate' && set -a && source '$ROOT/.env' && set +a && uvicorn app.main:app --host 127.0.0.1 --port 8000"
  for i in $(seq 1 30); do
    curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && break
    sleep 1
  done
fi

python "$ROOT/scripts/seed_demo_data.py" >> "$LOG_DIR/seed.log" 2>&1 || true

start_bg worker bash -lc "cd '$ROOT/apps/api' && source '$VENV/bin/activate' && set -a && source '$ROOT/.env' && set +a && celery -A app.celery_app worker --loglevel=info --pool=solo"
start_bg simulator bash -lc "cd '$ROOT/packages/agent-simulator' && source '$VENV/bin/activate' && set -a && source '$ROOT/.env' && set +a && python -m simulator.main"

chmod +x "$ROOT/scripts/dev-web.sh"
"$ROOT/scripts/dev-web.sh"

log "Task Platform (local dev) started."
log "  Web:       http://127.0.0.1:3000"
log "  API:       http://127.0.0.1:8000/docs"
log "  Simulator: http://127.0.0.1:8100/health"
log "  Logs:      $LOG_DIR"
