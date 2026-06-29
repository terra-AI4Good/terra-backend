# Testing

Terra uses **pytest** with **pytest-asyncio** for testing. All tests run against an in-memory SQLite database — no external services are called.

---

## Quick Reference

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/terra --cov-report=term-missing

# Run a specific file
uv run pytest tests/test_auth.py -v

# Run by name pattern
uv run pytest -k "test_login or test_register"

# Run and stop on first failure
uv run pytest -x
```

Coverage minimum is **80%** (enforced by `[tool.coverage.report] fail_under = 80` in `pyproject.toml`).

---

## Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── test_auth.py         # Authentication endpoints
├── test_chatbot.py      # /chat endpoint, ChatbotService
├── test_documents.py    # Document CRUD endpoints
├── test_ba_jobs.py      # BAJobsClient, SearchBAJobsTool, GetBAJobDetailsTool
├── test_static_kb.py    # StaticKBService, KB tools
├── test_tools.py        # Tool base class, ToolRegistry
├── test_agents.py       # Agent implementations, AgentRegistry
├── test_agents_api.py   # /agents and /tools endpoints
├── test_mcp.py          # MCP client, registry, service, tool adapter
├── test_llm.py          # LLMService, LLMResponse parsing
├── test_web_search.py   # WebSearchTool, TavilySearchProvider
└── test_health.py       # Health check endpoints
```

One test file per domain module. This keeps related tests together and makes it easy to run a specific domain's tests in isolation.

---

## Fixtures (`conftest.py`)

### `db`

An in-memory SQLite session with fresh tables for each test. All tables are created before the test and dropped after.

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

### `app`

A FastAPI application instance with the `get_db` dependency overridden to use the test session:

```python
@pytest.fixture
def app(db: AsyncSession):
    application = create_app()

    async def _override_get_db():
        yield db

    application.dependency_overrides[get_db] = _override_get_db
    return application
```

### `client`

An `httpx.AsyncClient` bound to the test app via `ASGITransport`. No real network calls are made.

```python
@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

---

## Mocking Strategy

### LLM calls

LLM calls (`LLMService.completion`) are mocked with `unittest.mock.AsyncMock` or `pytest-mock`:

```python
from unittest.mock import AsyncMock, patch
from terra.llm.types import LLMResponse, TokenUsage

mock_response = LLMResponse(
    content="Here is some information about healthcare...",
    tool_calls=[],
    usage=TokenUsage(prompt_tokens=50, completion_tokens=100, total_tokens=150),
    model="gpt-4o-mini",
    finish_reason="stop",
)

with patch("terra.llm.service.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
    mock_llm.return_value = build_litellm_response(mock_response)
    result = await chatbot.chat(user_id=1, message="What is healthcare like?")
```

### External API calls

BA Jobsuche and Tavily calls are mocked at the `httpx.AsyncClient` level or by injecting a fake provider:

```python
# Inject a mock search provider
from terra.services.search.base import SearchProvider, SearchResponse, SearchResult

class FakeSearchProvider(SearchProvider):
    async def search(self, query, **kwargs):
        return SearchResponse(
            query=query,
            results=[SearchResult(title="Test", url="https://example.com", snippet="...", domain="example.com")]
        )

tool = WebSearchTool(provider=FakeSearchProvider())
result = await tool.execute(query="healthcare Germany")
```

### MCP client

MCPClient is mocked to return pre-defined tool schemas and call results:

```python
from unittest.mock import AsyncMock
from terra.mcp.schemas import MCPToolSchema, MCPToolCallResult

mock_client = AsyncMock()
mock_client.list_tools.return_value = [
    MCPToolSchema(name="salary_info", description="Get salary info", input_schema={})
]
mock_client.call_tool.return_value = MCPToolCallResult(
    success=True,
    content=[{"type": "text", "text": '{"median": 60000}'}]
)
```

### Static KB

Tests inject a custom `StaticKBService` with controlled data:

```python
from terra.services.static_kb import StaticKBService

sample_pages = [
    {"id": "1", "title": "Healthcare", "category": "gesundheit",
     "content_text": "Information about health insurance...", "url": "https://..."}
]

class FakeKBService(StaticKBService):
    def _load_pages(self):
        return sample_pages
```

---

## Async Configuration

All tests that use `async/await` must be marked or the entire suite configured for async. `asyncio_mode = "auto"` in `pyproject.toml` means pytest-asyncio automatically handles async test functions:

```python
# No need to explicitly mark — all async test functions run automatically
async def test_something():
    result = await some_async_function()
    assert result is not None
```

---

## Example Test Patterns

### Testing an authenticated endpoint

```python
async def test_get_documents_authenticated(client):
    # Register and get token
    reg = await client.post("/api/v1/auth/register",
                            json={"username": "alice", "password": "password123"})
    token = reg.json()["token"]

    # Use token in subsequent requests
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/documents", headers=headers)
    assert response.status_code == 200
    assert response.json() == []
```

### Testing a tool directly

```python
async def test_search_static_kb_tool():
    # Use a fake service to avoid file I/O
    from terra.tools.static_kb import SearchStaticKBTool
    tool = SearchStaticKBTool(service=FakeKBService())
    result = await tool.execute(query="healthcare")
    assert result.success
    assert len(result.data["results"]) > 0
```

### Testing database isolation

Each test gets a fresh database. No state leaks between tests:

```python
async def test_user_isolation(db):
    # Create user in this test
    user = await create_user(db, "alice", "password123")
    assert user.id is not None

    # No other users exist
    from sqlalchemy import select
    from terra.models.user import User
    result = await db.execute(select(User))
    users = result.scalars().all()
    assert len(users) == 1
```

---

## Coverage

Coverage is configured to exclude migration files:

```toml
[tool.coverage.run]
source = ["src/terra"]
omit = ["src/terra/db/migrations/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

```bash
# Generate HTML report
uv run pytest --cov=src/terra --cov-report=html
open htmlcov/index.html
```

---

## CI Integration

Tests are intended to run in CI with no external dependencies:

```bash
# Minimal CI setup
uv sync
uv run pytest --cov=src/terra
```

The `MCP_ENABLED=false` env var can be set in CI to skip MCP discovery, which would otherwise make real network calls during startup. However, MCP discovery is already non-fatal (wrapped in `suppress(Exception)`), so this is optional.
