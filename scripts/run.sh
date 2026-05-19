#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../backend"

if [ ! -d venv ]; then
    echo "[ERR] 找不到 backend/venv,請先執行 ./scripts/setup.sh"
    exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate

PORT="${PORT:-8000}"
URL="http://localhost:${PORT}"

# 背景開瀏覽器 (macOS 用 open, Linux 用 xdg-open, 都失敗就略過)
(
    sleep 2
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$URL" >/dev/null 2>&1 || true
    elif command -v open >/dev/null 2>&1; then
        open "$URL" >/dev/null 2>&1 || true
    fi
) &

echo "==> Serving on $URL  (Ctrl+C 停止)"
exec uvicorn app.main:app --port "$PORT"
