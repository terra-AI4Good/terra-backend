FROM python:3.13-slim AS base

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies only (not the project itself yet)
RUN uv sync --no-dev --frozen --no-install-project

# Copy application source
COPY src/ src/
COPY alembic.ini ./
COPY data/ data/

# Now install the project (fast — deps are cached)
RUN uv sync --no-dev --frozen

# Copy entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Create data directories
RUN mkdir -p data/static_kb/raw data/static_kb/processed data/static_kb/index

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["serve"]
