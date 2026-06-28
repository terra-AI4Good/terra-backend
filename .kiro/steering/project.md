# Terra Backend — Project Steering

## What this project is

Terra is a FastAPI backend for an AI assistant aimed at helping immigrants navigate life in Germany. It combines:
- Conversational memory (per-user, database-backed)
- A tool-equipped chatbot (POST /api/v1/chat)
- Pluggable agents (web_search, job_listings, static_knowledge_base)
- Document upload with memory integration
- Static knowledge base from the Integreat CMS (cms.integreat-app.de)

## Language and runtime

Python 3.12+. Package manager: `uv`. Always use `uv run` or activate `.venv` before running anything.

## Architecture in one sentence

HTTP layer (FastAPI) → service layer → LLMService (LiteLLM) + ToolRegistry + MemoryStore → SQLite (dev) / PostgreSQL (prod).

## Module map

| Path | Responsibility |
|------|---------------|
| `src/terra/api/v1/endpoints/` | HTTP handlers — thin, delegate to services |
| `src/terra/services/` | Business logic (chatbot, auth, documents, search) |
| `src/terra/agents/` | Agent classes + AgentRegistry |
| `src/terra/tools/` | Tool classes + ToolRegistry |
| `src/terra/orchestration/` | AgentRunner (tool-call loop) + ExecutionHooks |
| `src/terra/llm/` | LLMService wrapping LiteLLM |
| `src/terra/memory/` | MemoryStore interface + DatabaseMemoryStore |
| `src/terra/models/` | SQLAlchemy ORM models |
| `src/terra/schemas/` | Pydantic request/response schemas |
| `src/terra/evals/` | EvalSuite base for agent evaluation |
| `src/terra/config.py` | Settings via pydantic-settings, env vars |
| `src/terra/setup.py` | One-time registration of all tools + agents |

## Extending the system

**New tool:** Subclass `terra.tools.base.Tool`, implement `definition` and `execute`, register in `setup.py → _register_tools()`.

**New agent:** Subclass `terra.agents.base.Agent`, implement `run` and `step`, register in `setup.py → _register_agents()` with an `AgentConfig` listing which tools it uses.

**New endpoint:** Add a router in `src/terra/api/v1/endpoints/`, include it in `src/terra/api/v1/router.py`.

## Code conventions

- Ruff for lint + format (`ruff check . && ruff format .`)
- mypy strict mode (`mypy src/`)
- Async everywhere — all DB calls, LLM calls, and tool `execute()` methods are `async`
- No bare `litellm.*` calls outside `terra.llm.service` — always go through `LLMService`
- No bare `print()` — use the `LoggingHook` or Python `logging`
- Settings only from `get_settings()` — never hardcode values
- Test with in-memory SQLite (`sqlite+aiosqlite://`) — never use the real `terra.db` in tests

## Key env vars

```
OPENAI_API_KEY        # required for LLM calls
LLM_DEFAULT_MODEL     # default: gpt-4o-mini
TAVILY_API_KEY        # required for web_search tool
DATABASE_URL          # default: sqlite+aiosqlite:///terra.db
SECRET_KEY            # session signing
DEBUG                 # set true to expose memory_context in chat responses
```

## Testing

```bash
uv run pytest              # run all tests
uv run pytest --cov        # with coverage (must hit 80%)
uv run pytest tests/test_chatbot.py -v   # single file
```

LLM calls are always mocked in tests with `unittest.mock.AsyncMock`. Never make real API calls in unit/integration tests.

## Deployment

Docker + ECS Fargate (us-west-2). The container listens on port 80 (env `PORT=80`). `OPENAI_API_KEY` is injected from AWS Secrets Manager at `terra-backend/OPENAI_API_KEY`. Push flow:

```bash
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 959317755669.dkr.ecr.us-west-2.amazonaws.com
docker build -t ai4good/terra-backend .
docker tag ai4good/terra-backend:latest 959317755669.dkr.ecr.us-west-2.amazonaws.com/ai4good/terra-backend:latest
docker push 959317755669.dkr.ecr.us-west-2.amazonaws.com/ai4good/terra-backend:latest
aws ecs update-service --cluster default --service terra-backend-28b2 --force-new-deployment
```
