# Deployment

## Docker

### Dockerfile Overview

The project uses a `python:3.13-slim` base image with `uv` for fast dependency management:

```dockerfile
FROM python:3.13-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# System deps + uv
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Dependencies (cached layer)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --frozen --no-install-project

# Application source
COPY src/ src/
COPY alembic.ini ./
COPY data/ data/
RUN uv sync --no-dev --frozen

# Entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
RUN mkdir -p data/static_kb/raw data/static_kb/processed data/static_kb/index

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["serve"]
```

### Build and Run

```bash
# Build
docker build -t terra-backend .

# Run
docker run -p 8000:8000 --env-file .env terra-backend
```

### Entrypoint Commands

The `docker-entrypoint.sh` supports multiple commands:

| Command | Description |
|---------|-------------|
| `serve` (default) | Start the uvicorn server |
| `fetch-kb` | Refresh the static knowledge base |
| `shell` | Open a bash shell in the container |

```bash
# Default: serve
docker run terra-backend

# Refresh KB manually
docker run terra-backend fetch-kb

# Debug shell
docker run -it terra-backend shell
```

### Startup Sequence (Docker)

1. Create database tables (SQLAlchemy `metadata.create_all`)
2. If KB data doesn't exist, fetch it in the background (non-blocking)
3. Start uvicorn on configured host/port

---

## Docker Compose

### Basic Setup

```yaml
services:
  terra-backend:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - DATABASE_URL=sqlite+aiosqlite:///data/terra.db
    volumes:
      - terra-data:/app/data
    restart: unless-stopped

volumes:
  terra-data:
```

```bash
# Start
docker compose up --build

# Start in background
docker compose up -d --build

# View logs
docker compose logs -f terra-backend

# Stop
docker compose down

# Stop and remove volumes
docker compose down -v
```

### Persistent Data

The `terra-data` volume persists:
- SQLite database (`data/terra.db`)
- Static KB files (`data/static_kb/`)

This ensures data survives container restarts.

### Production Compose Example

```yaml
services:
  terra-backend:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - DATABASE_URL=sqlite+aiosqlite:///data/terra.db
      - DEBUG=false
      - WORKERS=2
    volumes:
      - terra-data:/app/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1.0"

volumes:
  terra-data:
    driver: local
```

---

## ECS Deployment

### Task Definition

Key considerations for AWS ECS:

```json
{
  "family": "terra-backend",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "terra-backend",
      "image": "<ecr-repo>/terra-backend:latest",
      "portMappings": [
        {"containerPort": 8000, "protocol": "tcp"}
      ],
      "environment": [
        {"name": "HOST", "value": "0.0.0.0"},
        {"name": "PORT", "value": "8000"},
        {"name": "DATABASE_URL", "value": "sqlite+aiosqlite:///data/terra.db"}
      ],
      "secrets": [
        {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:ssm:region:account:parameter/terra/openai-key"},
        {"name": "SECRET_KEY", "valueFrom": "arn:aws:ssm:region:account:parameter/terra/secret-key"}
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 15
      },
      "mountPoints": [
        {"sourceVolume": "terra-data", "containerPath": "/app/data"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/terra-backend",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "volumes": [
    {"name": "terra-data", "efsVolumeConfiguration": {"fileSystemId": "fs-xxx"}}
  ]
}
```

### Load Balancer Configuration

- **Target group:** HTTP on port 8000
- **Health check path:** `/health`
- **Health check interval:** 30s
- **Healthy threshold:** 2
- **Unhealthy threshold:** 3

### Secrets Management

Store sensitive values in AWS SSM Parameter Store or Secrets Manager:

```bash
aws ssm put-parameter --name /terra/openai-key --value "sk-..." --type SecureString
aws ssm put-parameter --name /terra/secret-key --value "$(python -c 'import secrets; print(secrets.token_hex(32))')" --type SecureString
aws ssm put-parameter --name /terra/tavily-key --value "tvly-..." --type SecureString
```

### Storage

Since Terra uses SQLite, the database file needs persistent storage:

- **EFS** — Attach an EFS volume for persistence across task replacements
- **Alternative** — Migrate to RDS PostgreSQL for multi-instance deployments

---

## Environment Setup

### Development

```bash
# 1. Clone and install
git clone <repo> && cd terra-backend
uv sync

# 2. Configure
cp .env.example .env
# Set OPENAI_API_KEY at minimum

# 3. Install pre-commit hooks
uv run pre-commit install

# 4. Fetch KB data (optional)
uv run python -m terra.scripts.fetch_static_kb

# 5. Run
uv run uvicorn terra.main:app --reload
```

### Staging

```env
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/terra.db
OPENAI_API_KEY=sk-staging-key
SECRET_KEY=<generated>
ALLOWED_ORIGINS=["https://staging.example.com"]
LLM_DEFAULT_MODEL=gpt-4o-mini
MCP_ENABLED=true
```

### Production

```env
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/terra.db
OPENAI_API_KEY=sk-prod-key
TAVILY_API_KEY=tvly-prod-key
SECRET_KEY=<generated-32-byte-hex>
ALLOWED_ORIGINS=["https://app.example.com"]
LLM_DEFAULT_MODEL=gpt-4o
MCP_ENABLED=true
WORKERS=2
```

---

## Health Checks

Two health check endpoints are available:

| Endpoint | Purpose | Use For |
|----------|---------|---------|
| `GET /health` | Root-level, minimal | ALB/ECS health probes |
| `GET /api/v1/health` | API-level | Application monitoring |

Both return `{"status": "healthy"}` with HTTP 200.

### Docker Health Check

Built into the Dockerfile:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

- **Interval:** Check every 30 seconds
- **Timeout:** Fail if no response within 5 seconds
- **Start period:** Grace period of 15 seconds for startup
- **Retries:** Mark unhealthy after 3 consecutive failures

### MCP Server Health

The MCP server (`terra-mig`) has its own health endpoint checked via:

```bash
curl https://te-8423728b85714970bb70e62ee24f6cf4.ecs.us-west-2.on.aws/health
```

Or via the API:

```bash
curl http://localhost:8000/api/v1/mcp/servers/terra-mig/health \
  -H "Authorization: Bearer <token>"
```

---

## Scaling Considerations

### Current Limitations (SQLite)

- Single-writer — Only one process can write at a time
- File-based — Requires shared filesystem for multi-instance
- No connection pooling benefits

### When to Migrate to PostgreSQL

- Multiple backend instances (horizontal scaling)
- High write concurrency
- Need for advanced queries (full-text search, JSONB)

Migration path:
1. Change `DATABASE_URL` to a PostgreSQL connection string
2. Use Alembic migrations (already configured)
3. SQLAlchemy async works with `asyncpg` driver

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/terra
```

### Uvicorn Workers

For single-instance deployments, use multiple workers:

```env
WORKERS=4  # CPU cores
```

The entrypoint passes this to uvicorn:

```bash
uvicorn terra.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Note: With SQLite + multiple workers, each worker has its own DB connection. This works for read-heavy workloads but may cause write contention.
