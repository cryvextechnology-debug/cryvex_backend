#!/bin/bash
set -e

echo "[STARTUP] Starting Redis server on localhost..."
if [ -n "$REDIS_PASSWORD" ]; then
    redis-server --requirepass "$REDIS_PASSWORD" --bind 127.0.0.1 --port 6379 &
else
    redis-server --bind 127.0.0.1 --port 6379 &
fi

# Give Redis a moment to start
sleep 2

echo "[STARTUP] Redis started. Launching FastAPI application..."

# Start Gunicorn
exec gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    -w 4 \
    --bind 0.0.0.0:${PORT:-8000} \
    --access-logfile - \
    --error-logfile -
