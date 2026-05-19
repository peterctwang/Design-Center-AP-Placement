#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../backend"
source venv/bin/activate
( sleep 2 && (xdg-open http://localhost:8000 || open http://localhost:8000) ) &
uvicorn app.main:app --port 8000
