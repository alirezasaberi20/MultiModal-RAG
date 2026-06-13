#!/usr/bin/env bash
# Run backend (ml-env) + React frontend together
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

eval "$(mamba shell hook --shell bash)"
mamba activate ml-env

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env — set OPENAI_API_KEY before querying documents."
fi

mkdir -p data storage/users data/chroma

if [ ! -d frontend/node_modules ]; then
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
fi

echo "Starting backend on http://127.0.0.1:8000"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 2

echo "Starting frontend on http://127.0.0.1:5173"
cd frontend
npm run dev
