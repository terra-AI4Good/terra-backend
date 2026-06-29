# Deployment

---

## Docker

### Dockerfile Overview

The `Dockerfile` uses a single-stage build based on `python:3.13-slim`. `uv` is copied from the official image to keep the layer slim.

**Build steps:**
1. Install system dependencies (`curl` for health check).
2. Copy `uv` binary from `ghcr.io/astral-sh/uv:latest`.
3. Copy `pyproject.toml`, `uv.lock`, `README.md` (layer cache for deps).
4. `uv sync --no-dev --frozen --no-install-project` — install dependencies only.
5. Copy application source and data.
6. `uv sync --no-dev --frozen` — install the project itself (fast; deps cached).
7. Set up entrypoint.

```dockerfile
FROM python:3.13-slim AS base
...
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --frozen --no-install-project
COPY src/ src/
COPY alembic.ini ./
COPY data/ data/
RUN uv sync --no-dev --frozen
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["serve"]
```

### Entrypoint Commands

The `docker-entrypoint.sh` supports three commands:

| Command | Description |
|---|---|
| `serve` (default) | Run database setup and start uvicorn |
| `fetch-kb` | Refresh the static knowledge base from Integreat CMS |
| `shell` | Open a bash shell |

```bash
# Default: start the server
docker run terra-backend serve

# Refresh KB
docker run terra-backend fetch-kb

# Custom command
docker run terra-backend python -m some.module
```

**Startup sequence (`serve`):**
1. Run `create_all()` to ensure database tables exist.
2. If `data/static_kb/processed/pages.json` is missing, start `fetch_static_kb` in the background.
3. Start uvicorn.

The server starts immediately; the KB fetch (if needed) runs in the background. The server will operate without KB functionality until the fetch completes.

---

## Docker Compose

### `docker-compose.yml`

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

The `terra-data` named volume persists the database and static KB data across container restarts.

### Running

```bash
# Build and start
docker compose up --build

# Detached
docker compose up -d --build

# View logs
docker compose logs -f terra-backend

# Refresh the knowledge base
docker compose exec terra-backend fetch-kb

# Stop
docker compose down

# Stop and remove volume (destructive — deletes all data)
docker compose down -v
```

---

## Production Configuration

Minimum required environment variables for production:

```bash
# Required
OPENAI_API_KEY=sk-...          # or ANTHROPIC_API_KEY
SECRET_KEY=<random-64-hex>     # generate: python -c "import secrets; print(secrets.token_hex(32))"

# Strongly recommended
TAVILY_API_KEY=tvly-...        # enables web search
ALLOWED_ORIGINS=["https://your-frontend.com"]
DEBUG=false

# Production database (optional — SQLite works for single-instance)
DATABASE_URL=sqlite+aiosqlite:///data/terra.db
```

### Performance

For production, increase uvicorn workers when `DATABASE_URL` points to PostgreSQL. SQLite does not support multiple writers, so keep `WORKERS=1` with SQLite.

```bash
# In docker-entrypoint.sh or as env var
WORKERS=1   # with SQLite
WORKERS=4   # with PostgreSQL
```

---

## AWS ECS Deployment

The application is deployed on AWS ECS (Elastic Container Service). Key considerations:

### Health Check

The ALB (Application Load Balancer) health check should target `GET /health`. This endpoint has no auth requirement and responds immediately.

```
Path: /health
Port: 8000
Healthy threshold: 2
Unhealthy threshold: 3
Interval: 30s
Timeout: 5s
```

### ECS Task Definition (relevant settings)

```json
{
  "containerDefinitions": [
    {
      "name": "terra-backend",
      "image": "<ecr-repo>:latest",
      "portMappings": [{"containerPort": 8000}],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 15
      },
      "environment": [
        {"name": "HOST", "value": "0.0.0.0"},
        {"name": "PORT", "value": "8000"},
        {"name": "DATABASE_URL", "value": "sqlite+aiosqlite:///data/terra.db"}
      ],
      "secrets": [
        {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:..."},
        {"name": "SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
      ],
      "mountPoints": [
        {
          "containerPath": "/app/data",
          "sourceVolume": "terra-data"
        }
      ]
    }
  ]
}
```

### EFS Mount for Persistence

Use AWS EFS (Elastic File System) to persist the SQLite database and knowledge base across ECS task replacements:

1. Create an EFS file system in the same VPC.
2. Mount it at `/app/data` in the task definition.
3. Set `DATABASE_URL=sqlite+aiosqlite:///data/terra.db`.

For multi-AZ deployments or horizontal scaling, migrate to RDS PostgreSQL — SQLite on EFS has performance limitations under concurrent write load.

---

## Building for Production

```bash
# Build image
docker build -t terra-backend:latest .

# Tag and push to ECR
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin <account>.dkr.ecr.us-west-2.amazonaws.com

docker tag terra-backend:latest <account>.dkr.ecr.us-west-2.amazonaws.com/terra-backend:latest
docker push <account>.dkr.ecr.us-west-2.amazonaws.com/terra-backend:latest
```

---

## Non-Docker Local Production

```bash
uv sync --no-dev
uv run uvicorn terra.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  --log-level info
```
