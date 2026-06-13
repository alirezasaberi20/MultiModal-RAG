#!/usr/bin/env bash
# Run the Multimodal RAG API server inside ml-env
set -euo pipefail

cd "$(dirname "$0")/.."

eval "$(mamba shell hook --shell bash)"
mamba activate ml-env

if [ ! -f .env ]; then
  echo "No .env file found. Copying .env.example — set OPENAI_API_KEY before querying."
  cp .env.example .env
fi

mkdir -p data storage/users data/chroma

uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" --reload
