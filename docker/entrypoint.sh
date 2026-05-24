#!/bin/sh
set -e

exec /app/.venv/bin/uvicorn app.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8080}"
