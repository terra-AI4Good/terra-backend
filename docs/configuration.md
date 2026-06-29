# Configuration

All configuration is loaded from environment variables via [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). A `.env` file in the project root is automatically read.

```bash
cp .env.example .env
# Edit .env with your values
```

Settings are cached as a singleton (`@lru_cache` on `get_settings()`), so the `.env` file is only read once per process.

---

## Application

| Variable | Default | Required | Description |
|---|---|---|---|
| `APP_NAME` | `Terra` | No | Application name (shown in OpenAPI docs) |
| `APP_VERSION` | `0.1.0` | No | Application version |
| `DEBUG` | `false` | No | Enable SQL query logging and expose memory context in `/chat` responses |

---

## Server

| Variable | Default | Required | Description |
|---|---|---|---|
| `HOST` | `0.0.0.0` | No | Bind address for uvicorn |
| `PORT` | `8000` | No | HTTP port |

---

## Database

| Variable | Default | Required | Description |
|---|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///<cwd>/terra.db` | No | SQLAlchemy async database URL. The default resolves to `terra.db` in the current working directory. |

**Examples:**
```bash
# Default: SQLite in project root
DATABASE_URL=sqlite+aiosqlite:///terra.db

# Absolute path
DATABASE_URL=sqlite+aiosqlite:////var/data/terra.db

# Docker volume path (used in docker-compose.yml)
DATABASE_URL=sqlite+aiosqlite:///data/terra.db
```

---

## Security

| Variable | Default | Required | Description |
|---|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | **Yes in prod** | Application secret. Not currently used for JWT signing (sessions use random tokens), but should be set to a random value before any deployment. |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | No | CORS allowed origins. Must be a valid JSON array string. |

```bash
# Generate a secure key:
python -c "import secrets; print(secrets.token_hex(32))"

# Multiple origins:
ALLOWED_ORIGINS=["https://app.example.com","https://staging.example.com"]
```

---

## LLM / LiteLLM

| Variable | Default | Required | Description |
|---|---|---|---|
| `LLM_DEFAULT_MODEL` | `gpt-4o-mini` | No | LiteLLM model identifier. See [LiteLLM provider docs](https://docs.litellm.ai/docs/providers). |
| `LLM_DEFAULT_TEMPERATURE` | `0.7` | No | Sampling temperature (0.0–2.0) |
| `LLM_DEFAULT_MAX_TOKENS` | `4096` | No | Maximum tokens per LLM response |
| `LLM_DEFAULT_TIMEOUT` | `60.0` | No | LLM request timeout in seconds |

### Provider API Keys

| Variable | Default | Required | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | — | Yes* | OpenAI API key. Required for GPT models. |
| `ANTHROPIC_API_KEY` | — | No | Anthropic API key. Required for Claude models. |
| `AZURE_API_KEY` | — | No | Azure OpenAI API key |
| `AZURE_API_BASE` | — | No | Azure OpenAI endpoint URL |
| `AZURE_API_VERSION` | — | No | Azure API version (e.g. `2024-02-01`) |

*Any provider key is required that matches the configured `LLM_DEFAULT_MODEL`.

**LiteLLM model identifier examples:**

| Provider | Example identifier |
|---|---|
| OpenAI | `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo` |
| Anthropic | `claude-3-5-sonnet-20241022`, `claude-3-haiku-20240307` |
| Azure OpenAI | `azure/my-deployment-name` |
| Google Vertex | `vertex_ai/gemini-pro` |
| Ollama (local) | `ollama/llama3` |

---

## Search (Tavily)

| Variable | Default | Required | Description |
|---|---|---|---|
| `SEARCH_API_KEY` | — | No | Generic search API key (alias for `TAVILY_API_KEY`) |
| `SEARCH_API_PROVIDER` | `tavily` | No | Search provider identifier (currently only `tavily` is implemented) |
| `TAVILY_API_KEY` | — | Yes for web search | Tavily API key |
| `TAVILY_SEARCH_DEPTH` | `basic` | No | Default search depth: `basic` or `advanced` |
| `TAVILY_DEFAULT_MAX_RESULTS` | `5` | No | Default number of search results (1–20) |
| `TAVILY_TIMEOUT_SECONDS` | `20.0` | No | Tavily request timeout |

If no Tavily key is configured, the `web_search` tool will fail with an error when called.

---

## BA Jobsuche (Bundesagentur für Arbeit)

| Variable | Default | Required | Description |
|---|---|---|---|
| `BA_JOBS_BASE_URL` | `https://rest.arbeitsagentur.de/jobboerse/jobsuche-service` | No | Base URL for BA API |
| `BA_JOBS_API_KEY` | `jobboerse-jobsuche` | No | API key sent as `X-API-Key` header. The default is the public key. |
| `BA_JOBS_DEFAULT_RADIUS_KM` | `50` | No | Default search radius in km |
| `BA_JOBS_DEFAULT_SIZE` | `10` | No | Default results per page |
| `BA_JOBS_FETCH_DETAILS_LIMIT` | `5` | No | Number of top results to enrich with full details (additional API calls) |

The BA Jobsuche API is publicly accessible with the default key. No registration needed.

---

## Static Knowledge Base

| Variable | Default | Required | Description |
|---|---|---|---|
| `STATIC_KB_API_URL` | Integreat CMS URL | No | URL to fetch pages from Integreat CMS |
| `STATIC_KB_API_KEY` | — | No | Bearer token for Integreat API (not required for public endpoint) |
| `STATIC_KB_RAW_PATH` | `data/static_kb/raw/payload.json` | No | Where to save the raw API response |
| `STATIC_KB_PROCESSED_PATH` | `data/static_kb/processed/pages.json` | No | Where to save the processed page data |
| `STATIC_KB_FETCH_TIMEOUT_SECONDS` | `60.0` | No | Timeout for the Integreat API fetch |

---

## Memory

| Variable | Default | Required | Description |
|---|---|---|---|
| `MEMORY_PROVIDER` | `database` | No | Memory backend identifier. Currently only `database` is implemented. |
| `MEMORY_CONTEXT_LIMIT` | `20` | No | Maximum number of memory entries retrieved per chat turn |

---

## MCP Integration

| Variable | Default | Required | Description |
|---|---|---|---|
| `MCP_ENABLED` | `true` | No | Enable or disable all MCP server integration |
| `MCP_TERRA_MIG_NAME` | `terra-mig` | No | Logical name for the terra-mig MCP server |
| `MCP_TERRA_MIG_HEALTH_URL` | AWS ECS URL | No | Health check endpoint for terra-mig |
| `MCP_TERRA_MIG_ENDPOINT_URL` | AWS ECS URL | No | MCP JSON-RPC endpoint for terra-mig |
| `MCP_REQUEST_TIMEOUT_SECONDS` | `30.0` | No | Timeout for MCP requests |

Set `MCP_ENABLED=false` to skip MCP discovery entirely (useful for offline development).

---

## Full `.env.example`

```bash
# Application
APP_NAME=Terra
APP_VERSION=0.1.0
DEBUG=false

# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite+aiosqlite:///terra.db

# Security
SECRET_KEY=change-me-in-production
ALLOWED_ORIGINS=["http://localhost:3000"]

# LLM Configuration (LiteLLM)
LLM_DEFAULT_MODEL=gpt-4o-mini
LLM_DEFAULT_TEMPERATURE=0.7
LLM_DEFAULT_MAX_TOKENS=4096
LLM_DEFAULT_TIMEOUT=60.0

# Provider API Keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
AZURE_API_KEY=
AZURE_API_BASE=
AZURE_API_VERSION=

# Web Search
SEARCH_API_KEY=
SEARCH_API_PROVIDER=tavily
TAVILY_API_KEY=
TAVILY_SEARCH_DEPTH=basic
TAVILY_DEFAULT_MAX_RESULTS=5
TAVILY_TIMEOUT_SECONDS=20

# BA Jobsuche API
BA_JOBS_BASE_URL=https://rest.arbeitsagentur.de/jobboerse/jobsuche-service
BA_JOBS_API_KEY=jobboerse-jobsuche
BA_JOBS_DEFAULT_RADIUS_KM=50
BA_JOBS_DEFAULT_SIZE=10
BA_JOBS_FETCH_DETAILS_LIMIT=5

# Static Knowledge Base
STATIC_KB_API_URL=https://cms.integreat-app.de/testumgebung-frag-integreat/de/wp-json/extensions/v3/pages/
STATIC_KB_API_KEY=
STATIC_KB_RAW_PATH=data/static_kb/raw/payload.json
STATIC_KB_PROCESSED_PATH=data/static_kb/processed/pages.json
STATIC_KB_FETCH_TIMEOUT_SECONDS=60

# Memory
MEMORY_PROVIDER=database
MEMORY_CONTEXT_LIMIT=20

# MCP Servers
MCP_ENABLED=true
MCP_TERRA_MIG_NAME=terra-mig
MCP_TERRA_MIG_HEALTH_URL=https://te-8423728b85714970bb70e62ee24f6cf4.ecs.us-west-2.on.aws/health
MCP_TERRA_MIG_ENDPOINT_URL=https://te-8423728b85714970bb70e62ee24f6cf4.ecs.us-west-2.on.aws/mcp
MCP_REQUEST_TIMEOUT_SECONDS=30
```
