# Testing

Terra uses **pytest** with **pytest-asyncio** for testing. All tests run against an in-memory SQLite database.

## Quick Reference

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run a specific test file
uv run pytest tests/test_auth.py

# Run a specific test
uv run pytest tests/test_auth.py::test_register_success

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures (db, app, client)
├── fixtures/
│   └── static_kb_sample.json  # Sample KB data for testing
├── test_auth.py             # Auth endpoints (register, login, logout, me)
├── test_chatbot.py          # Chat endpoint and tool integration
├── test_documents.py        # Document CRUD
├── test_agents.py           # Agent listing and execution
├── test_mcp.py              # MCP server endpoints
├── test_memory.py           # Memory store implementation
├── test_tools.py            # Tool registry and execution
├── test_static_kb.py        # Static knowledge base search
├── test_ba_jobs.py          # BA Jobsuche client
├── test_config.py           # Configuration loading
└── test_health.py           # Health check endpoints
```

**162 tests** across 11 test files.

## Fixtures

All fixtures are defined in `tests/conftest.py`:

### `db` — Database Session

Provides a fresh async SQLAlchemy session backed by in-memory SQLite. Tables are created before each test and dropped after.

```python
@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionFactory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

### `app` — FastAPI Application

Creates a fresh app instance with the DB dependency overridden to use the test database:

```python
@pytest.fixture
def app(db: AsyncSession):
    application = create_app()
    async def _override_get_db():
        yield db
    application.dependency_overrides[get_db] = _override_get_db
    return application
```

### `client` — HTTP Client

An `httpx.AsyncClient` bound to the test app via `ASGITransport`:

```python
@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

### Test Data Fixture

`tests/fixtures/static_kb_sample.json` contains a sample of Integreat CMS pages for testing the static knowledge base search without hitting the real API.

## Mocking Strategy

### External API Calls

External services (LLM, Tavily, BA Jobsuche, MCP) are mocked using `unittest.mock.patch` or `pytest-mock`:

```python
from unittest.mock import AsyncMock, patch

async def test_chat_with_mock_llm(client):
    # Mock the LLM completion to avoid real API calls
    with patch("terra.llm.service.LLMService.completion") as mock_llm:
        mock_llm.return_value = MockResponse(content="Hello!", tool_calls=None)
        resp = await client.post(
            "/api/v1/chat",
            json={"message": "Hi"},
            headers={"Authorization": "Bearer <token>"},
        )
    assert resp.status_code == 200
```

### Tool Execution

Tools that call external APIs are mocked at the tool level:

```python
with patch("terra.tools.search.TavilyClient") as mock_tavily:
    mock_tavily.return_value.search.return_value = {"results": [...]}
    result = await tool.execute(query="test")
```

### MCP Client

The MCP client is mocked to avoid requiring a live MCP server during tests:

```python
with patch("terra.mcp.client.MCPClient.call_tool") as mock_call:
    mock_call.return_value = MCPToolCallResult(
        success=True,
        content=[{"type": "text", "text": "result"}],
    )
```

### Database

No mocking needed — tests use a real in-memory SQLite database. This ensures ORM queries and models are exercised.

## Writing Tests

### Basic Pattern

```python
"""Tests for feature X."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_feature_happy_path(client: AsyncClient):
    """Test description."""
    response = await client.post("/api/v1/endpoint", json={"key": "value"})
    assert response.status_code == 200
    data = response.json()
    assert data["expected_field"] == "expected_value"


@pytest.mark.asyncio
async def test_feature_error_case(client: AsyncClient):
    """Test error handling."""
    response = await client.post("/api/v1/endpoint", json={})
    assert response.status_code == 422
```

### Testing Authenticated Endpoints

Create a user and login first, then use the token:

```python
@pytest.mark.asyncio
async def test_authenticated_endpoint(client: AsyncClient):
    # Register
    resp = await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "testpass123"},
    )
    token = resp.json()["token"]

    # Use authenticated endpoint
    resp = await client.post(
        "/api/v1/chat",
        json={"message": "Hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
```

### Testing Service Layer Directly

```python
from terra.services.auth import create_user, authenticate_user

@pytest.mark.asyncio
async def test_create_user(db):
    user = await create_user(db, "alice", "password123")
    assert user.username == "alice"
    assert user.password_hash != "password123"  # Hashed
```

## Configuration

Test configuration lives in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["src/terra"]
omit = ["src/terra/db/migrations/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

Key settings:
- `asyncio_mode = "auto"` — All async tests run without explicit `@pytest.mark.asyncio` (though it's still used for clarity)
- `fail_under = 80` — Coverage must be at least 80%
- Migrations are excluded from coverage

## CI Integration

Tests run as part of the pre-commit hooks and CI pipeline:

```bash
# Full check (lint + type check + tests)
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest --cov --cov-report=term-missing
```
