# Extending Terra

This guide covers how to add new capabilities to the Terra backend.

## Adding a New Tool

Tools are the primary way to give the chatbot new capabilities. Each tool has a definition (schema) and an execute method.

### 1. Create the tool file

Create `src/terra/tools/my_tool.py`:

```python
"""My custom tool implementation."""

from __future__ import annotations

from typing import Any

from terra.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class MyCustomTool(Tool):
    """A tool that does something useful."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="my_custom_tool",
            description="Does something useful with the given input",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The input query",
                    required=True,
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Maximum number of results",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool."""
        query = kwargs.get("query", "")
        limit = kwargs.get("limit", 10)

        try:
            # Your tool logic here
            results = await self._do_work(query, limit)
            return ToolResult(success=True, data=results)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _do_work(self, query: str, limit: int) -> dict[str, Any]:
        """Internal implementation."""
        return {"query": query, "results": [], "total": 0}
```

### 2. Register the tool

Add the tool to `src/terra/setup.py` in the `_register_tools()` function:

```python
from terra.tools.my_tool import MyCustomTool

def _register_tools() -> None:
    tools = [
        # ... existing tools ...
        MyCustomTool(),
    ]
    for tool in tools:
        if tool.name not in tool_registry:
            tool_registry.register(tool)
```

### 3. The tool is now available

Once registered, the tool is automatically:
- Listed at `GET /api/v1/tools`
- Available to the chatbot for function calling
- Available to any agent that includes it in its `tools` list

### Key interfaces

```python
class Tool(ABC):
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition: ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult: ...
```

```python
class ToolResult(BaseModel):
    success: bool = True
    data: Any = None
    error: str | None = None
```

---

## Adding a New Agent

Agents combine an LLM with tools and a system prompt to accomplish tasks through iterative reasoning.

### 1. Create the agent file

Create `src/terra/agents/my_agent.py`:

```python
"""My custom agent implementation."""

from __future__ import annotations

from typing import Any

from terra.agents.base import Agent, AgentConfig, AgentResult
from terra.config import get_settings
from terra.llm.config import LLMSettings
from terra.llm.service import LLMService
from terra.llm.types import ChatMessage
from terra.tools.registry import tool_registry


class MyAgent(Agent):
    """An agent that specializes in a specific task."""

    def __init__(self, config: AgentConfig) -> None:
        super().__init__(config)
        settings = get_settings()
        llm_settings = LLMSettings(
            default_model=settings.llm_default_model,
            default_temperature=settings.llm_default_temperature,
            default_max_tokens=settings.llm_default_max_tokens,
            default_timeout=settings.llm_default_timeout,
            openai_api_key=settings.openai_api_key,
        )
        self._llm = LLMService(settings=llm_settings)

    async def run(
        self,
        input_message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute the agent's task."""
        messages = [
            ChatMessage(role="system", content=self._config.system_prompt),
            ChatMessage(role="user", content=input_message),
        ]

        # Get tool schemas for this agent's tools
        tool_schemas = None
        if self._config.tools:
            tools = [
                tool_registry.get(name)
                for name in self._config.tools
                if name in tool_registry
            ]
            tool_schemas = [t.to_openai_schema() for t in tools]

        iterations = 0
        tool_calls_made = 0

        for _ in range(self._config.max_iterations):
            iterations += 1
            response = await self._llm.completion(
                messages=messages,
                tools=tool_schemas,
            )

            if not response.tool_calls:
                return AgentResult(
                    success=True,
                    output=response.content or "",
                    iterations=iterations,
                    tool_calls_made=tool_calls_made,
                )

            # Handle tool calls
            messages.append(ChatMessage(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls,
            ))

            for tool_call in response.tool_calls:
                import json
                tool_calls_made += 1
                kwargs = json.loads(tool_call.function.arguments)
                result = await tool_registry.execute(tool_call.function.name, **kwargs)
                messages.append(ChatMessage(
                    role="tool",
                    content=result.model_dump_json(),
                    tool_call_id=tool_call.id,
                ))

        return AgentResult(
            success=True,
            output="Max iterations reached",
            iterations=iterations,
            tool_calls_made=tool_calls_made,
        )

    async def step(self, messages: list[ChatMessage]) -> ChatMessage:
        """Execute a single reasoning step."""
        response = await self._llm.completion(messages=messages)
        return ChatMessage(role="assistant", content=response.content)
```

### 2. Register the agent

Add the agent to `src/terra/setup.py` in the `_register_agents()` function:

```python
from terra.agents.my_agent import MyAgent

def _register_agents() -> None:
    agents: list[tuple[type, AgentConfig]] = [
        # ... existing agents ...
        (
            MyAgent,
            AgentConfig(
                name="my_agent",
                description="Specializes in a specific task domain",
                system_prompt="You are an expert at...",
                tools=["my_custom_tool", "web_search"],
                max_iterations=10,
            ),
        ),
    ]
    for agent_cls, config in agents:
        if config.name not in agent_registry:
            agent_registry.register(agent_cls, config)
```

### 3. The agent is now available

- Listed at `GET /api/v1/agents`
- Executable via `POST /api/v1/agents/run` with `{"agent_name": "my_agent", ...}`

---

## Adding a New MCP Server

MCP servers are external services that expose tools via the Model Context Protocol.

### 1. Add configuration variables

In `src/terra/config.py`, add settings for your server:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # My MCP Server
    mcp_my_server_name: str = "my-server"
    mcp_my_server_health_url: str = "https://my-server.example.com/health"
    mcp_my_server_endpoint_url: str = "https://my-server.example.com/mcp"
```

### 2. Register the server

In `src/terra/setup.py`, add to `_register_mcp_servers()`:

```python
def _register_mcp_servers() -> None:
    settings = get_settings()
    if not settings.mcp_enabled:
        return

    # ... existing servers ...

    my_server = MCPServerConfig(
        name=settings.mcp_my_server_name,
        description="My custom MCP server for XYZ",
        health_url=settings.mcp_my_server_health_url,
        endpoint_url=settings.mcp_my_server_endpoint_url,
        enabled=True,
    )
    if my_server.name not in mcp_registry:
        mcp_registry.register(my_server)
```

### 3. Add environment variables

```env
MCP_MY_SERVER_NAME=my-server
MCP_MY_SERVER_HEALTH_URL=https://my-server.example.com/health
MCP_MY_SERVER_ENDPOINT_URL=https://my-server.example.com/mcp
```

### 4. Tools are auto-discovered

On startup, `discover_mcp_tools()` will connect to your MCP server, list its tools, and register them as tool adapters in the local tool registry.

---

## Adding a New Memory Backend

The memory system uses an abstract `MemoryStore` interface. You can implement alternative storage backends.

### 1. Create the implementation

Create `src/terra/memory/redis_store.py` (example):

```python
"""Redis-backed memory store."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from terra.memory.base import MemoryEntry, MemoryStore


class RedisMemoryStore(MemoryStore):
    """Memory store backed by Redis."""

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        # Initialize your Redis client here

    async def add(
        self,
        user_id: int,
        role: Literal["user", "assistant"],
        content: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Store a new memory entry."""
        # Push to a Redis list or sorted set keyed by user_id
        ...

    async def retrieve(
        self,
        user_id: int,
        query: str | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Retrieve recent memory entries."""
        # Fetch from Redis, optionally filter by query
        ...

    async def clear(self, user_id: int) -> None:
        """Clear all memory for a user."""
        ...

    async def count(self, user_id: int) -> int:
        """Return entry count for a user."""
        ...
```

### 2. Wire it up

Update the chatbot endpoint (`src/terra/api/v1/endpoints/chatbot.py`) to select the memory store based on config:

```python
settings = get_settings()
if settings.memory_provider == "redis":
    memory = RedisMemoryStore(settings.redis_url)
else:
    memory = DatabaseMemoryStore(db)
```

### Key interface

```python
class MemoryStore(ABC):
    async def add(self, user_id, role, content, metadata=None) -> None: ...
    async def retrieve(self, user_id, query=None, limit=20) -> list[MemoryEntry]: ...
    async def clear(self, user_id) -> None: ...
    async def count(self, user_id) -> int: ...
```

---

## Adding a New LLM Provider

Terra uses LiteLLM as an abstraction layer, so most providers work out of the box.

### Supported by LiteLLM (no code changes needed)

Set the appropriate environment variables:

```env
# OpenAI
OPENAI_API_KEY=sk-...
LLM_DEFAULT_MODEL=gpt-4o

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_DEFAULT_MODEL=anthropic/claude-3-5-sonnet-20241022

# Azure OpenAI
AZURE_API_KEY=...
AZURE_API_BASE=https://your-resource.openai.azure.com/
AZURE_API_VERSION=2024-02-15-preview
LLM_DEFAULT_MODEL=azure/your-deployment-name

# AWS Bedrock
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
LLM_DEFAULT_MODEL=bedrock/anthropic.claude-3-sonnet-20240229-v1:0
```

LiteLLM supports 100+ providers. See [LiteLLM docs](https://docs.litellm.ai/docs/providers) for the full list.

### Adding a custom provider

If you need to support a provider not covered by LiteLLM, extend `src/terra/llm/service.py`:

```python
class LLMService:
    async def completion(self, messages, tools=None):
        if self._settings.custom_provider:
            return await self._custom_completion(messages, tools)
        # Default LiteLLM path
        ...
```

---

## Adding a New Search Provider

The web search tool currently uses Tavily. To add an alternative:

### 1. Create the provider

Create `src/terra/tools/search_providers/brave.py`:

```python
"""Brave Search provider."""

from __future__ import annotations
from typing import Any
import httpx


class BraveSearchProvider:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max_results},
                headers={"X-Subscription-Token": self._api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {"title": r["title"], "url": r["url"], "content": r.get("description", "")}
                for r in data.get("web", {}).get("results", [])
            ]
```

### 2. Update the search tool

Modify `src/terra/tools/search.py` to select provider based on config:

```python
from terra.config import get_settings

class WebSearchTool(Tool):
    async def execute(self, **kwargs: Any) -> ToolResult:
        settings = get_settings()
        if settings.search_api_provider == "brave":
            provider = BraveSearchProvider(settings.brave_api_key)
        else:
            provider = TavilySearchProvider(settings.tavily_api_key)

        results = await provider.search(kwargs["query"])
        return ToolResult(success=True, data=results)
```

### 3. Add configuration

```python
# In config.py
brave_api_key: str | None = None
```

```env
SEARCH_API_PROVIDER=brave
BRAVE_API_KEY=BSA...
```
