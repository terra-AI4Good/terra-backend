# Terra Backend — Coding Conventions

## Python style

- Line length: 88 (ruff default)
- Target: Python 3.12 — use `type | None` not `Optional[type]`, use `list[str]` not `List[str]`
- Imports: stdlib → third-party → first-party (`terra.*`), sorted by isort
- All public functions and methods get type annotations (mypy strict)
- `from __future__ import annotations` at top of files that forward-reference types

## No comments rule

Only add a comment when the WHY is non-obvious. Never write docstrings explaining what the code does — the names should do that. One-line module docstrings are fine.

## Async patterns

- All database operations use `AsyncSession` — always `await`
- LLM calls: always `await llm.completion(...)`, never `litellm.*` directly
- Tool `execute()` methods: always `async def execute(self, **kwargs)`
- Never use `asyncio.run()` inside an async context

## Error handling

- Validate at the HTTP boundary (Pydantic schemas) — don't re-validate inside services
- Services raise `ValueError` for domain errors; endpoints catch and convert to `HTTPException`
- Tool `execute()` returns `ToolResult(success=False, error=...)` instead of raising
- Never swallow exceptions silently

## Registry pattern

Both `tool_registry` and `agent_registry` are global singletons (module-level in `tools/registry.py` and `agents/registry.py`). They are populated once at startup by `setup.register_all()`. Guard against double-registration with `if name not in registry`.

## Database

- ORM models in `src/terra/models/` — inherit `Base` from `terra.db.base`
- All models register themselves when imported; `setup.py` imports `terra.models` to trigger this
- Migrations via alembic: `uv run alembic revision --autogenerate -m "description"` then `uv run alembic upgrade head`
- Never call `Base.metadata.create_all` in production paths — only in startup lifespan and tests

## Testing conventions

- Use `AsyncClient` with `ASGITransport` — never spin up a real server in tests
- DB fixture uses in-memory SQLite, creates + drops tables per test
- Mock LLM with `@patch("terra.services.chatbot.LLMService.completion", new_callable=AsyncMock)`
- Test classes group related tests: `TestFooAuth`, `TestFooEndpoint`, `TestFooIntegration`
- Fixtures are in `tests/conftest.py` — don't duplicate them in test files
