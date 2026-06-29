# Extending Terra

This document provides step-by-step guides for adding new capabilities to the Terra backend.

---

## Adding a New Tool

Tools are the primary way to give the AI access to external data or actions. Every tool is a Python class that implements the `Tool` abstract base class.

### Step 1 — Create the tool class

Create a new file in `src/terra/tools/`:

```python
# src/terra/tools/my_tool.py
from __future__ import annotations

from typing import Any

from terra.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class MyTool(Tool):
    """One-line description of what this tool does."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="my_tool",  # must be unique across the registry
            description=(
                "Describe what the tool does and when the LLM should use it. "
                "Be specific — the LLM uses this to decide whether to call it."
            ),
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search query or input.",
                    required=True,
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Max results to return.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        if not query:
            return ToolResult(success=False, error="query is required")

        # Your implementation here
        result = await some_async_operation(query)

        return ToolResult(
            success=True,
            data={"results": result},
        )
```

**ToolParameter types:** Use JSON Schema type names: `"string"`, `"integer"`, `"number"`, `"boolean"`, `"array"`, `"object"`.

**ToolResult fields:**
- `success` — `True` on success, `False` on failure
- `data` — any JSON-serialisable value returned to the LLM
- `error` — human-readable error string (only when `success=False`)

### Step 2 — Register the tool

In `src/terra/setup.py`, add your tool to `_register_tools()`:

```python
from terra.tools.my_tool import MyTool

def _register_tools() -> None:
    tools = [
        ...
        MyTool(),  # add here
    ]
    for tool in tools:
        if tool.name not in tool_registry:
            tool_registry.register(tool)
```

### Step 3 — Write tests

Create `tests/test_my_tool.py`:

```python
import pytest
from terra.tools.my_tool import MyTool


@pytest.mark.asyncio
async def test_my_tool_basic():
    tool = MyTool()
    result = await tool.execute(query="test")
    assert result.success
    assert "results" in result.data


@pytest.mark.asyncio
async def test_my_tool_missing_query():
    tool = MyTool()
    result = await tool.execute()
    assert not result.success
    assert result.error
```

That is all. The tool is automatically available to the chatbot and all agents on the next startup.

---

## Adding a New Agent

Agents wrap a system prompt and tool access in a reusable, named component. They can be called directly via `POST /api/v1/agents/run` or used internally by the orchestrator.

### Step 1 — Create the agent class

Create a new file in `src/terra/agents/`:

```python
# src/terra/agents/my_agent.py
from __future__ import annotations

from typing import Any

from terra.agents.base import Agent, AgentConfig, AgentResult
from terra.config import get_settings
from terra.llm.config import LLMSettings
from terra.llm.service import LLMService
from terra.llm.types import ChatMessage

MY_AGENT_SYSTEM_PROMPT = (
    "You are a specialised assistant for X. "
    "When asked about X, use the my_tool tool. "
    "Always cite your sources."
)


class MyAgent(Agent):
    """Agent that does X."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        if config is None:
            config = AgentConfig(
                name="my_agent",
                description="Does X using my_tool",
                system_prompt=MY_AGENT_SYSTEM_PROMPT,
                tools=["my_tool"],
                max_iterations=5,
            )
        super().__init__(config)

    async def run(
        self,
        input_message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute the agent. Override for custom logic."""
        from terra.tools.my_tool import MyTool

        tool = MyTool()
        result = await tool.execute(query=input_message)

        if not result.success:
            return AgentResult(
                success=False,
                output=f"Tool failed: {result.error}",
                error=result.error,
            )

        output = self._format_output(result.data)
        return AgentResult(
            success=True,
            output=output,
            tool_calls_made=1,
            iterations=1,
        )

    async def step(self, messages: list[ChatMessage]) -> ChatMessage:
        """Single LLM step — for AgentRunner integration."""
        settings = get_settings()
        from terra.tools.my_tool import MyTool

        llm = LLMService(
            settings=LLMSettings(
                default_model=settings.llm_default_model,
                openai_api_key=settings.openai_api_key,
            )
        )
        tool = MyTool()
        response = await llm.completion(
            messages=messages,
            tools=[tool.to_openai_schema()],
        )
        return ChatMessage(
            role="assistant",
            content=response.content,
            tool_calls=response.tool_calls or None,
        )

    def _format_output(self, data: dict) -> str:
        return str(data)
```

### Step 2 — Register the agent

In `src/terra/setup.py`, add to `_register_agents()`:

```python
from terra.agents.my_agent import MyAgent

def _register_agents() -> None:
    agents = [
        ...
        (
            MyAgent,
            AgentConfig(
                name="my_agent",
                description="Does X using my_tool",
                tools=["my_tool"],
            ),
        ),
    ]
```

### Step 3 — Verify

```bash
uv run uvicorn terra.main:app --reload
curl http://localhost:8000/api/v1/agents
# should include {"name": "my_agent", ...}
```

---

## Adding a New MCP Server

MCP servers expose tools over HTTP using the Model Context Protocol. Adding one makes all its tools available to the chatbot and all agents.

### Step 1 — Add environment variables

In `src/terra/config.py`, add settings for the new server:

```python
# New MCP server
mcp_my_server_name: str = "my-server"
mcp_my_server_health_url: str = "https://my-server.example.com/health"
mcp_my_server_endpoint_url: str = "https://my-server.example.com/mcp"
```

In `.env.example` and your `.env`:
```bash
MCP_MY_SERVER_NAME=my-server
MCP_MY_SERVER_HEALTH_URL=https://my-server.example.com/health
MCP_MY_SERVER_ENDPOINT_URL=https://my-server.example.com/mcp
```

### Step 2 — Register the server

In `src/terra/setup.py`, add to `_register_mcp_servers()`:

```python
def _register_mcp_servers() -> None:
    settings = get_settings()
    if not settings.mcp_enabled:
        return

    # Existing terra-mig server
    terra_mig = MCPServerConfig(...)
    if terra_mig.name not in mcp_registry:
        mcp_registry.register(terra_mig)

    # New server
    my_server = MCPServerConfig(
        name=settings.mcp_my_server_name,
        description="Description of what this server provides",
        health_url=settings.mcp_my_server_health_url,
        endpoint_url=settings.mcp_my_server_endpoint_url,
        enabled=True,
        auth_headers={"X-API-Key": "your-key"},  # optional auth
    )
    if my_server.name not in mcp_registry:
        mcp_registry.register(my_server)
```

### Step 3 — Restart

On the next startup, `discover_mcp_tools()` will connect to the new server, discover its tools, and register them as `mcp_my-server_<tool_name>` in the tool registry.

Tools are available immediately to the chatbot — no further changes needed.

---

## Adding a New LLM Provider

LiteLLM supports 100+ providers. To use a different model:

1. Set `LLM_DEFAULT_MODEL` to the [LiteLLM identifier](https://docs.litellm.ai/docs/providers) for the model.
2. Set the corresponding API key environment variable.

```bash
# Anthropic Claude
LLM_DEFAULT_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# Azure OpenAI
LLM_DEFAULT_MODEL=azure/my-gpt4-deployment
AZURE_API_KEY=...
AZURE_API_BASE=https://my-resource.openai.azure.com/
AZURE_API_VERSION=2024-02-01

# Ollama (local)
LLM_DEFAULT_MODEL=ollama/llama3
# No API key needed for local Ollama
```

No code changes are required.

---

## Replacing the Memory Backend

The `MemoryStore` abstract interface (`src/terra/memory/base.py`) is the only contract the chatbot depends on.

### Step 1 — Implement the interface

```python
# src/terra/memory/my_store.py
from terra.memory.base import MemoryEntry, MemoryStore

class MyVectorStore(MemoryStore):

    async def add(self, user_id, role, content, metadata=None):
        # Store in your vector DB with user_id as namespace
        ...

    async def retrieve(self, user_id, query=None, limit=20):
        # Semantic search by query if provided, else recency
        if query:
            results = await self._vector_search(user_id, query, limit)
        else:
            results = await self._recent(user_id, limit)
        return [
            MemoryEntry(role=r.role, content=r.content, timestamp=r.ts)
            for r in results
        ]

    async def clear(self, user_id):
        await self._delete_all(user_id)

    async def count(self, user_id):
        return await self._count(user_id)
```

### Step 2 — Swap in `chatbot.py` endpoint

In `src/terra/api/v1/endpoints/chatbot.py`, replace:

```python
from terra.memory.db_store import DatabaseMemoryStore

memory = DatabaseMemoryStore(db)
```

with:

```python
from terra.memory.my_store import MyVectorStore

memory = MyVectorStore(...)
```

---

## Adding a New Knowledge Source

### Option A — New static KB

1. Write a script (similar to `fetch_static_kb.py`) that fetches and processes your source into a JSON list of pages.
2. Create a new `StaticKBService`-like service pointing to your processed file.
3. Create tools (similar to `SearchStaticKBTool`) that use your service.
4. Register the tools in `setup.py`.

### Option B — Real-time API

1. Create a service (similar to `BAJobsClient`) that wraps your API.
2. Create tools that call the service.
3. Register the tools.

---

## Adding a Custom Execution Hook

Hooks let you instrument agent runs without modifying agent code.

```python
# src/terra/orchestration/my_hook.py
import time

from terra.agents.base import AgentResult
from terra.llm.types import ChatMessage
from terra.orchestration.hooks import ExecutionHook


class TimingHook(ExecutionHook):

    def __init__(self):
        self._start_time: float = 0

    async def on_start(self, agent_name: str, input_message: str) -> None:
        self._start_time = time.monotonic()

    async def on_step(self, agent_name: str, iteration: int, message: ChatMessage) -> None:
        pass

    async def on_tool_call(self, agent_name: str, tool_name: str, call_id: str) -> None:
        pass

    async def on_tool_result(self, agent_name: str, tool_name: str, result: str) -> None:
        pass

    async def on_complete(self, agent_name: str, result: AgentResult) -> None:
        elapsed = time.monotonic() - self._start_time
        print(f"[{agent_name}] completed in {elapsed:.2f}s, {result.tool_calls_made} tool calls")
```

Use the hook when constructing an `AgentRunner`:

```python
from terra.orchestration.runner import AgentRunner
from terra.orchestration.my_hook import TimingHook
from terra.tools.registry import tool_registry

runner = AgentRunner(
    agent=my_agent,
    tool_registry=tool_registry,
    hook=TimingHook(),
)
result = await runner.run("Find jobs in Berlin")
```

---

## Adding a New Prompt Template

Use `PromptTemplate` for reusable, variable-substituted prompts:

```python
from terra.prompts.base import PromptTemplate

JOB_SEARCH_PROMPT = PromptTemplate(
    name="job_search",
    description="System prompt for job search agent with city context",
    template=(
        "You are a job search assistant for newcomers in $city, Germany. "
        "Use the search_ba_jobs tool to find $job_type positions. "
        "Published within the last $days days."
    ),
    variables=["city", "job_type", "days"],
)

# Render
prompt = JOB_SEARCH_PROMPT.render(city="Berlin", job_type="engineering", days="30")
```
