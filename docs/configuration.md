# Configuration

All configuration is loaded from environment variables via [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). A `.env` file in the project root is automatically read.

Copy the example file to get started:

```bash
cp .env.example .env
```

## Environment Variables

### Application

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `APP_NAME` | Application display name | `Terra` | No |
| `APP_VERSION` | Application version string | `0.1.0` | No |
| `DEBUG` | Enable debug mode (exposes memory context in chat responses) | `false` | No |

### Server

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `HOST` | Bind address for uvicorn | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |

### Database

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `DATABASE_URL` | SQLAlchemy async database URL | `sqlite+aiosqlite:///terra.db` | No |

The default SQLite database is created in the project root. For Docker, override to `/app/data/terra.db` via compose.

### Security

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `SECRET_KEY` | Application secret (used for internal signing) | `change-me-in-production` | **Yes** (production) |
| `ALLOWED_ORIGINS` | CORS allowed origins (JSON array) | `["http://localhost:3000"]` | No |

### LLM Configuration

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `LLM_DEFAULT_MODEL` | Default LiteLLM model identifier | `gpt-4o-mini` | No |
| `LLM_DEFAULT_TEMPERATURE` | Default sampling temperature | `0.7` | No |
| `LLM_DEFAULT_MAX_TOKENS` | Default max response tokens | `4096` | No |
| `LLM_DEFAULT_TIMEOUT` | LLM request timeout (seconds) | `60.0` | No |

### LLM Provider API Keys

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | None | **Yes** (if using OpenAI models) |
| `ANTHROPIC_API_KEY` | Anthropic API key | None | Only if using Anthropic models |
| `AZURE_API_KEY` | Azure OpenAI API key | None | Only if using Azure |
| `AZURE_API_BASE` | Azure OpenAI endpoint URL | None | Only if using Azure |
| `AZURE_API_VERSION` | Azure OpenAI API version | None | Only if using Azure |

At least one LLM provider key is required for the chatbot and agents to function.

### Search / Tools

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `SEARCH_API_KEY` | Generic search API key (legacy) | None | No |
| `SEARCH_API_PROVIDER` | Search provider name | `tavily` | No |

### Tavily Web Search

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `TAVILY_API_KEY` | Tavily API key for web search tool | None | Only if using web_search tool |
| `TAVILY_SEARCH_DEPTH` | Search depth (`basic` or `advanced`) | `basic` | No |
| `TAVILY_DEFAULT_MAX_RESULTS` | Default number of search results | `5` | No |
| `TAVILY_TIMEOUT_SECONDS` | Tavily request timeout | `20` | No |

### BA Jobsuche API

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `BA_JOBS_BASE_URL` | BA Jobsuche REST API base URL | `https://rest.arbeitsagentur.de/jobboerse/jobsuche-service` | No |
| `BA_JOBS_API_KEY` | BA Jobsuche X-API-Key | `jobboerse-jobsuche` | No |
| `BA_JOBS_DEFAULT_RADIUS_KM` | Default search radius in km | `50` | No |
| `BA_JOBS_DEFAULT_SIZE` | Default number of results per search | `10` | No |
| `BA_JOBS_FETCH_DETAILS_LIMIT` | Max jobs to fetch full details for | `5` | No |

### Static Knowledge Base (Integreat CMS)

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `STATIC_KB_API_URL` | Integreat CMS pages API URL | `https://cms.integreat-app.de/testumgebung-frag-integreat/de/wp-json/extensions/v3/pages/` | No |
| `STATIC_KB_API_KEY` | Integreat API key (if required) | None | No |
| `STATIC_KB_RAW_PATH` | Path to store raw API payload | `data/static_kb/raw/payload.json` | No |
| `STATIC_KB_PROCESSED_PATH` | Path to store processed pages | `data/static_kb/processed/pages.json` | No |
| `STATIC_KB_FETCH_TIMEOUT_SECONDS` | Fetch timeout for KB download | `60` | No |

### Memory

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `MEMORY_PROVIDER` | Memory store implementation | `database` | No |
| `MEMORY_CONTEXT_LIMIT` | Max memory entries to retrieve per chat turn | `20` | No |

### MCP Servers

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `MCP_ENABLED` | Enable MCP server integration | `true` | No |
| `MCP_TERRA_MIG_NAME` | MCP server name identifier | `terra-mig` | No |
| `MCP_TERRA_MIG_HEALTH_URL` | Health check URL for terra-mig | `https://te-8423728b85714970bb70e62ee24f6cf4.ecs.us-west-2.on.aws/health` | No |
| `MCP_TERRA_MIG_ENDPOINT_URL` | MCP endpoint URL for terra-mig | `https://te-8423728b85714970bb70e62ee24f6cf4.ecs.us-west-2.on.aws/mcp` | No |
| `MCP_REQUEST_TIMEOUT_SECONDS` | MCP request timeout | `30` | No |

## Minimal Configuration

For local development with OpenAI:

```env
OPENAI_API_KEY=sk-your-key-here
```

Everything else uses sensible defaults.

## Production Configuration

```env
# Security
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">
ALLOWED_ORIGINS=["https://your-domain.com"]

# Database (consider volume-mounted path for Docker)
DATABASE_URL=sqlite+aiosqlite:///data/terra.db

# LLM
OPENAI_API_KEY=sk-prod-key
LLM_DEFAULT_MODEL=gpt-4o

# Tools
TAVILY_API_KEY=tvly-prod-key

# Disable debug
DEBUG=false
```

## Configuration Loading

Configuration is managed via `src/terra/config.py` using pydantic-settings:

```python
from terra.config import get_settings

settings = get_settings()  # Cached singleton
print(settings.llm_default_model)
```

The `get_settings()` function is decorated with `@lru_cache`, so the settings object is created once and reused throughout the application lifecycle.
