#!/bin/bash
# Mac 启动脚本（对应 Windows 的 start_all.bat）
# 使用方法：在 unisv/ 目录下执行 bash start_all.sh

set -e
cd "$(dirname "$0")"

VENV="./venv/bin/activate"
LOG_DIR="./logs"
mkdir -p "$LOG_DIR"

# ── 检查虚拟环境 ──────────────────────────────────────────────────────────────
if [ ! -f "$VENV" ]; then
  echo "[ERROR] 虚拟环境不存在，请先运行："
  echo "  /usr/local/bin/python3.12 -m venv venv"
  echo "  source venv/bin/activate"
  echo "  pip install -r requirements.txt"
  exit 1
fi

source "$VENV"

# ── Redis ─────────────────────────────────────────────────────────────────────
if ! pgrep -x redis-server > /dev/null; then
  echo "[INFO] 启动 Redis..."
  brew services start redis
  sleep 1
else
  echo "[INFO] Redis 已在运行"
fi

# ── Celery Worker ─────────────────────────────────────────────────────────────
echo "[INFO] 启动 Celery Worker..."
celery -A unisv worker -l INFO -P threads \
  >> "$LOG_DIR/celery_worker.log" 2>&1 &
echo $! > "$LOG_DIR/celery_worker.pid"

# ── Celery Beat ───────────────────────────────────────────────────────────────
echo "[INFO] 启动 Celery Beat..."
celery -A unisv beat -l INFO \
  >> "$LOG_DIR/celery_beat.log" 2>&1 &
echo $! > "$LOG_DIR/celery_beat.pid"

# ── Django ────────────────────────────────────────────────────────────────────
echo "[INFO] 启动 Django (0.0.0.0:8000)..."
echo "[INFO] 按 Ctrl+C 停止所有服务"
echo "--------------------------------------------"
python manage.py runserver 0.0.0.0:8000
