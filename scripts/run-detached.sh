#!/usr/bin/env bash
# 以独立会话启动进程，避免父 shell 退出时子进程被回收
set -euo pipefail

PID_FILE="$1"
LOG_FILE="$2"
shift 2

python3 - "$PID_FILE" "$LOG_FILE" "$@" <<'PY'
import subprocess
import sys

pid_file, log_file = sys.argv[1], sys.argv[2]
cmd = sys.argv[3:]

with open(log_file, "a") as log:
    proc = subprocess.Popen(
        cmd,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

with open(pid_file, "w") as f:
    f.write(str(proc.pid))

print(proc.pid)
PY
