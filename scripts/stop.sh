#!/usr/bin/env bash
# Design Center - AP Placement / Linux & macOS stop script
# 殺掉占用指定 port 的 uvicorn process (預設 8000)
set -e

PORT="${1:-${PORT:-8000}}"

if [ -t 1 ]; then
    C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'; C_RED='\033[0;31m'; C_RESET='\033[0m'
else
    C_GREEN=''; C_YELLOW=''; C_RED=''; C_RESET=''
fi

echo "=== Stopping server on port ${PORT} ==="

# 找占用 port 的 PID (依序嘗試 lsof / fuser / ss)
find_pids() {
    if command -v lsof >/dev/null 2>&1; then
        lsof -ti tcp:"$PORT" -sTCP:LISTEN 2>/dev/null
    elif command -v fuser >/dev/null 2>&1; then
        fuser "${PORT}/tcp" 2>/dev/null | tr -s ' ' '\n' | grep -E '^[0-9]+$'
    elif command -v ss >/dev/null 2>&1; then
        ss -ltnp "sport = :${PORT}" 2>/dev/null \
            | grep -oP 'pid=\K[0-9]+' | sort -u
    else
        return 1
    fi
}

PIDS="$(find_pids || true)"

if [ -z "$PIDS" ]; then
    printf "${C_YELLOW}No process listening on port ${PORT}.${C_RESET}\n"
    exit 0
fi

for pid in $PIDS; do
    if kill "$pid" 2>/dev/null; then
        printf "${C_GREEN}[OK]${C_RESET} sent SIGTERM to PID %s\n" "$pid"
    fi
done

# 等 2 秒,再強殺殘留的
sleep 2
for pid in $PIDS; do
    if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
        printf "${C_RED}[KILL]${C_RESET} SIGKILL PID %s\n" "$pid"
    fi
done

echo "=== Done ==="
