#!/bin/bash
# 停止 Celery 进程
cd "$(dirname "$0")"
LOG_DIR="./logs"

for svc in celery_worker celery_beat; do
  PID_FILE="$LOG_DIR/$svc.pid"
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill "$PID" 2>/dev/null; then
      echo "[INFO] 已停止 $svc (PID $PID)"
    fi
    rm -f "$PID_FILE"
  fi
done

echo "[INFO] Django 请在运行的终端按 Ctrl+C 停止"
