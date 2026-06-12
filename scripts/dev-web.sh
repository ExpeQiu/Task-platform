#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${LOG_DIR:-/tmp/task-platform-logs}"
WEB_PORT="${WEB_PORT:-3000}"
PID_FILE="$LOG_DIR/web.pid"
LOG_FILE="$LOG_DIR/web.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    log "Stopping existing web process pid=$OLD_PID"
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
fi

log "Starting web on http://127.0.0.1:${WEB_PORT} (also http://localhost:${WEB_PORT})"
cd "$ROOT/apps/web"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
export WATCHPACK_POLLING=true
export CHOKIDAR_USEPOLLING=true

nohup npm run dev > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${WEB_PORT}" >/dev/null 2>&1; then
    log "Web ready pid=$(cat "$PID_FILE") log=$LOG_FILE"
    exit 0
  fi
  sleep 1
done

log "Web failed to start, see $LOG_FILE"
tail -20 "$LOG_FILE" || true
exit 1
