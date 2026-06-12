#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_URL="${API_URL:-http://localhost:8000}"
PASS=0
FAIL=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
ok() { log "OK: $*"; PASS=$((PASS + 1)); }
fail() { log "FAIL: $*"; FAIL=$((FAIL + 1)); }

log "=== Task Platform Verify ==="

# Health checks
if curl -sf "$API_URL/health" | grep -q '"status":"ok"'; then
  ok "API health"
else
  fail "API health"
fi

if curl -sf "http://localhost:8100/health" 2>/dev/null | grep -q '"status":"ok"'; then
  ok "Simulator health"
else
  fail "Simulator health (optional if not running)"
fi

# Adapters
ADAPTERS=$(curl -sf "$API_URL/v1/adapters" 2>/dev/null || echo "[]")
if echo "$ADAPTERS" | grep -q "OpenClaw"; then
  ok "OpenClaw adapter seeded"
else
  fail "OpenClaw adapter missing - run seed_demo_data.py"
fi

# E2E: create + submit + wait for success
ADAPTER_ID=$(echo "$ADAPTERS" | python3 -c "import sys,json; data=json.load(sys.stdin); print(next(a['id'] for a in data if a['name']=='OpenClaw'))" 2>/dev/null || echo "")

if [ -n "$ADAPTER_ID" ]; then
  TASK_RESP=$(curl -sf -X POST "$API_URL/v1/tasks" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"Verify Task\",\"objective\":\"E2E verification task\",\"agent_adapter_id\":\"$ADAPTER_ID\",\"sla_seconds\":60,\"loop_config\":{\"max_iterations\":3,\"max_duration_seconds\":300}}")

  TASK_ID=$(echo "$TASK_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

  if [ -n "$TASK_ID" ]; then
    ok "Task created id=$TASK_ID"
    RUN_RESP=$(curl -sf -X POST "$API_URL/v1/tasks/$TASK_ID/submit")
    RUN_ID=$(echo "$RUN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

    if [ -n "$RUN_ID" ]; then
      ok "Task submitted run_id=$RUN_ID"
      FINAL_STATUS=""
      for i in $(seq 1 30); do
        RUN_STATUS=$(curl -sf "$API_URL/v1/runs/$RUN_ID" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "")
        if [ "$RUN_STATUS" = "Success" ] || [ "$RUN_STATUS" = "Failed" ]; then
          FINAL_STATUS="$RUN_STATUS"
          break
        fi
        sleep 2
      done
      if [ "$FINAL_STATUS" = "Success" ]; then
        ok "E2E run completed with Success"
      else
        fail "E2E run did not reach Success (status=$FINAL_STATUS)"
      fi
    else
      fail "Task submit failed"
    fi
  else
    fail "Task creation failed"
  fi
else
  fail "Could not get OpenClaw adapter id"
fi

# Metrics
if curl -sf "$API_URL/v1/metrics/dashboard" | grep -q "total_tasks"; then
  ok "Dashboard metrics"
else
  fail "Dashboard metrics"
fi

log "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
