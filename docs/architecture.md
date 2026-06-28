# Architecture

## Overview

Terra Backend is a FastAPI application providing a memory-backed conversational AI assistant for migrants and newcomers in Germany. It follows a layered architecture: HTTP → Services → Abstractions → External APIs.

```
HTTP (FastAPI)
    ↓
Services (ChatbotService, AuthService, DocumentService)
    ↓
Abstractions (MemoryStore, LLMService, Tool, Agent)
    ↓
Implementations (DatabaseMemoryStore, LiteLLM, ToolRegistry, AgentRunner)
    ↓
External (OpenAI, Tavily, BA API, Integreat, MCP servers)
```

---

## Component Map

```mermaid
graph TB
    Client[Client]

    subgraph HTTP Layer
        Router[FastAPI Router]
        AuthEP[/auth endpoints/]
        ChatEP[/chat endpoint/]
        DocEP[/documents endpoints/]
        AgentEP[/agents + tools endpoints/]
        MCPEP[/mcp endpoints/]
        Deps[deps: get_db, get_current_user]
    end

    subgraph Services
        AuthSvc[AuthService]
        ChatSvc[ChatbotService]
        DocSvc[DocumentService]
        BAClient[BAJobsClient]
        KBSvc[StaticKBService]
        SearchSvc[SearchProvider / TavilySearchProvider]
    end

    subgraph Core Abstractions
        LLM[LLMService / LiteLLM]
        Mem[MemoryStore / DatabaseMemoryStore]
        TR[ToolRegistry]
        AR[AgentRegistry]
        Runner[AgentRunner]
        Hooks[ExecutionHooks]
    end

    subgraph MCP Subsystem
        MCPReg[MCPRegistry]
        MCPClient[MCPClient]
        MCPSvc[MCPService]
        Adapter[MCPToolAdapter]
    end

    subgraph Storage
        DB[(SQLite)]
        KBFile[pages.json]
    end

    subgraph External
        LLMAPI[OpenAI / Anthropic / Azure]
        Tavily[Tavily API]
        BAAPI[BA Jobsuche API]
        TerraMig[terra-mig MCP Server]
    end

    Client --> Router
    Router --> AuthEP & ChatEP & DocEP & AgentEP & MCPEP
    AuthEP --> AuthSvc --> DB
    ChatEP --> ChatSvc
    ChatSvc --> Mem --> DB
    ChatSvc --> LLM --> LLMAPI
    ChatSvc --> TR
    DocEP --> DocSvc --> DB
    DocSvc --> Mem
    AgentEP --> AR --> Runner --> TR
    Runner --> Hooks
    TR --> SearchSvc --> Tavily
    TR --> BAClient --> BAAPI
    TR --> KBSvc --> KBFile
    MCPEP --> MCPSvc --> MCPReg --> MCPClient --> TerraMig
    MCPSvc --> Adapter --> TR
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    participant UV as uvicorn
    participant App as create_app()
    participant Setup as setup.register_all()
    participant DB as SQLite
    participant MCP as MCPService

    UV->>App: import terra.main:app
    App->>Setup: register_all()
    Setup->>Setup: _register_tools() — 10 tools into tool_registry
    Setup->>Setup: _register_agents() — 3 agents into agent_registry
    Setup->>Setup: _register_mcp_servers() — terra-mig into mcp_registry
    App->>App: add CORS middleware
    App->>App: attach lifespan handler
    UV->>App: startup event
    App->>DB: create_all() — ensure tables exist
    App->>MCP: discover_mcp_tools() — non-fatal
    MCP->>MCP: initialize MCP session
    MCP->>MCP: list_tools() from terra-mig
    MCP->>MCP: register MCPToolAdapters into tool_registry
    App-->>UV: ready
```

---

## Request Lifecycle (Chat)

```mermaid
sequenceDiagram
    participant C as Client
    participant FastAPI
    participant Deps as get_current_user
    participant ChatSvc as ChatbotService
    participant Mem as MemoryStore
    participant LLM as LiteLLM
    participant TR as ToolRegistry
    participant Tool as (any Tool)

    C->>FastAPI: POST /api/v1/chat\nAuthorization: Bearer <token>
    FastAPI->>Deps: validate token
    Deps->>Deps: SELECT session WHERE token=... AND expires > now
    Deps-->>FastAPI: User object
    FastAPI->>ChatSvc: chat(user_id=1, message="...")
    ChatSvc->>Mem: retrieve(user_id=1, limit=20)
    Mem-->>ChatSvc: [MemoryEntry(role, content, timestamp), ...]
    ChatSvc->>ChatSvc: build_messages:\n  [system_prompt, ...history, user_message]
    ChatSvc->>ChatSvc: get_openai_schemas() from tool_registry

    loop up to max_tool_rounds=5
        ChatSvc->>LLM: acompletion(messages, tools)
        LLM-->>ChatSvc: LLMResponse
        alt response has tool_calls
            loop each tool call
                ChatSvc->>TR: execute(tool_name, **kwargs)
                TR->>Tool: execute(**kwargs)
                Tool-->>TR: ToolResult
                TR-->>ChatSvc: ToolResult
                ChatSvc->>ChatSvc: append tool result message
            end
        else no tool_calls
            ChatSvc->>ChatSvc: break
        end
    end

    ChatSvc->>Mem: add(user_id, "user", message)
    ChatSvc->>Mem: add(user_id, "assistant", response)
    ChatSvc-->>FastAPI: ChatResponse(response, used_tools)
    FastAPI-->>C: JSON response
```

---

## Tool Registration Flow

Tools are registered once at startup in `setup.py`. The global `tool_registry` singleton is used everywhere.

```mermaid
flowchart TD
    setup["setup.register_all()"]
    setup --> rt["_register_tools()"]
    setup --> ra["_register_agents()"]
    setup --> rm["_register_mcp_servers()"]

    rt --> |register| TR[tool_registry]

    rm --> |register config| MR[mcp_registry]
    MR --> |startup discover| Adapter[MCPToolAdapter per tool]
    Adapter --> |register| TR

    TR --> |get_openai_schemas()| LLM[Chatbot / AgentRunner]
    TR --> |execute(name, **kwargs)| Tools
```

---

## Memory Flow

```mermaid
flowchart LR
    ChatTurn[Chat turn] --> Retrieve[retrieve recent N entries]
    Retrieve --> BuildCtx[Build message context]
    BuildCtx --> LLM[LLM call]
    LLM --> Store[store user + assistant messages]

    DocUpload[Document upload] --> Chunk[Chunk 1000 chars / 100 overlap]
    Chunk --> Store2[store as memory entries\ntagged source=document]

    Store --> DB[(chat_memory table)]
    Store2 --> DB
    DB --> Retrieve
```

The `MemoryStore` interface decouples the chatbot from the storage backend:

```python
class MemoryStore(ABC):
    async def add(self, user_id, role, content, metadata=None): ...
    async def retrieve(self, user_id, query=None, limit=20): ...
    async def clear(self, user_id): ...
    async def count(self, user_id): ...
```

Current implementation: `DatabaseMemoryStore` (recency-based SQLite).
Future: swap for a vector store by implementing the same interface.

---

## MCP Integration

```mermaid
sequenceDiagram
    participant Startup
    participant MCPSvc as MCPService
    participant Client as MCPClient
    participant Server as terra-mig

    Startup->>MCPSvc: discover_and_register_tools("terra-mig")
    MCPSvc->>Client: initialize()
    Client->>Server: POST /mcp\n{"method":"initialize","params":{...}}
    Server-->>Client: SSE: {"result": {...}}\nheader: mcp-session-id: abc123
    Client->>Server: POST /mcp\n{"method":"notifications/initialized"}
    Server-->>Client: 202 Accepted
    MCPSvc->>Client: list_tools()
    Client->>Server: POST /mcp\n{"method":"tools/list"}\nheader: mcp-session-id: abc123
    Server-->>Client: SSE: {"result": {"tools": [...]}}
    loop each tool schema
        MCPSvc->>MCPSvc: create MCPToolAdapter(client, schema, "terra-mig")
        MCPSvc->>TR: register(adapter)
    end

    Note over Client,Server: Later — tool call
    TR->>Client: call_tool("salary_info", {profession:"..."})
    Client->>Server: POST /mcp\n{"method":"tools/call","params":{...}}
    Server-->>Client: SSE: {"result": {"content": [...]}}
    Client-->>TR: MCPToolCallResult
```

---

## Agent Orchestration

```mermaid
flowchart TD
    API["POST /agents/run"] --> AR[AgentRegistry.create]
    AR --> Agent[Agent instance]
    Agent --> Runner[AgentRunner.run]
    Runner --> Hooks[hook.on_start]

    Runner --> Loop{iteration < max_iterations}
    Loop --> Step[agent.step - one LLM call]
    Step --> Hooks2[hook.on_step]
    Step --> TC{tool_calls?}
    TC -->|yes| ExecLoop[for each tool_call]
    ExecLoop --> HookTC[hook.on_tool_call]
    ExecLoop --> TR[ToolRegistry.execute]
    TR --> HookTR[hook.on_tool_result]
    TR --> Append[append to messages]
    Append --> Loop
    TC -->|no| Final[extract final content]
    Final --> HookC[hook.on_complete]
    Final --> Result[AgentResult]
```

---

## Database

```mermaid
erDiagram
    users {
        int id PK
        str username UK
        str password_hash
        datetime created_at
        datetime updated_at
    }
    sessions {
        int id PK
        str token UK
        int user_id FK
        datetime expires_at
        datetime created_at
    }
    chat_memory {
        int id PK
        int user_id FK
        str role
        text content
        datetime created_at
    }
    documents {
        int id PK
        int user_id FK
        str title
        text content
        str content_hash
        datetime created_at
        datetime updated_at
    }

    users ||--o{ sessions : "has"
    users ||--o{ chat_memory : "has"
    users ||--o{ documents : "owns"
```

---

## Dependency Injection

FastAPI dependencies flow through each request:

```mermaid
graph TD
    Request --> get_db
    get_db -->|AsyncSession| get_current_user
    get_current_user -->|User| Endpoint
    get_db -->|AsyncSession| Endpoint
```

`get_db` yields a new `AsyncSession` per request from `async_session_factory`.
`get_current_user` resolves the Bearer token to a `User` object, raising `401` if invalid.

Both are shared across all endpoints via `Depends()`.
