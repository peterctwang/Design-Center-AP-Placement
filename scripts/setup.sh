#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

echo "=== 1/3 Backend venv + pip install ==="
cd backend
if [ ! -d venv ]; then python3 -m venv venv; fi
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "=== 2/3 Frontend npm install + build ==="
cd ../frontend
npm install
npm run build

echo "=== 3/3 Done! ==="
echo
echo "Start the server with:"
echo "  ./scripts/run.sh"
echo
echo "Or manually:"
echo "  cd backend && source venv/bin/activate && uvicorn app.main:app --port 8000"
