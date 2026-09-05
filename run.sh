#!/usr/bin/env bash
# One-command launcher for RecoverAI (backend + frontend).
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "== RecoverAI =="

# --- Backend ---
cd "$ROOT/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
echo "Starting backend on http://localhost:8000 ..."
uvicorn app.main:app --reload --port 8000 &
BACK_PID=$!

# --- Frontend ---
cd "$ROOT/frontend"
if [ -d node_modules ]; then
  echo "Starting frontend on http://localhost:5173 ..."
  npm run dev
else
  echo ""
  echo "Frontend deps not installed. Either:"
  echo "  cd frontend && npm install && npm run dev   (full React UI)"
  echo "  or just open demo.html in a browser         (zero-install UI)"
  echo ""
  echo "Backend is running at http://localhost:8000 (Ctrl-C to stop)."
  wait $BACK_PID
fi
