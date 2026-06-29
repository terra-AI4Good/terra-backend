#!/bin/bash
set -e

# Activate the uv-managed virtual environment
export PATH="/app/.venv/bin:$PATH"

# Run database migrations (create tables)
echo "==> Running database setup..."
python -c "
import asyncio
from terra.db.base import Base
from terra.db.session import engine
import terra.models  # noqa: F401 — register all models

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(init_db())
print('Database tables created.')
"

# Fetch static knowledge base in the background (non-blocking)
# Server starts immediately; KB will be available once fetch completes.
if [ ! -f "data/static_kb/processed/pages.json" ]; then
    echo "==> Fetching static knowledge base (background)..."
    python -m terra.scripts.fetch_static_kb &
else
    echo "==> Static KB already present, skipping fetch."
fi

# Dispatch command
case "${1}" in
    serve)
        echo "==> Starting Terra backend on port ${PORT:-8000}..."
        exec uvicorn terra.main:app \
            --host "${HOST:-0.0.0.0}" \
            --port "${PORT:-8000}" \
            --workers "${WORKERS:-1}" \
            --log-level "${LOG_LEVEL:-info}"
        ;;
    fetch-kb)
        echo "==> Refreshing static knowledge base..."
        exec python -m terra.scripts.fetch_static_kb
        ;;
    shell)
        exec /bin/bash
        ;;
    *)
        exec "$@"
        ;;
esac
