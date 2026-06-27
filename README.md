# Terra Backend

FastAPI backend for the Terra application.

## Quick Start

```bash
# Create virtual environment and install dependencies
uv sync --all-extras

# Copy environment file
cp .env.example .env

# Activate the virtual environment
source .venv/bin/activate

# Install pre-commit hooks
pre-commit install

# Run the development server
uvicorn terra.main:app --reload

# Run tests
pytest

# Run tests with coverage
pytest --cov
```

## Project Structure

```
src/terra/
├── api/              # HTTP layer (routers, endpoints, dependencies)
│   ├── v1/           # Versioned API
│   │   └── endpoints/
│   └── deps.py       # Shared dependency injection
├── db/               # Database layer
│   └── migrations/   # Alembic migrations
├── models/           # SQLAlchemy ORM models
├── schemas/          # Pydantic request/response schemas
├── services/         # Business logic
├── utils/            # Shared utilities
├── app.py            # Application factory
├── config.py         # Settings via pydantic-settings
└── main.py           # Entrypoint
```

## Development

```bash
# Lint and format
ruff check .
ruff format .

# Type check
mypy src/

# Create a migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Tech Stack

- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: SQLite (dev) — swap for PostgreSQL in production
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Tooling**: Ruff (lint + format), mypy (types), pytest (tests)
- **Package management**: uv
