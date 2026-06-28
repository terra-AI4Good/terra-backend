# Architecture

## Overview

Terra Backend is a FastAPI application that provides a memory-backed conversational AI assistant with pluggable tools, agents, and MCP (Model Context Protocol) integration. It is designed to help migrants and newcomers to Germany find jobs, understand visa requirements, and navigate integration resources.

## System Architecture

```mermaid
graph TB
    subgraph Clients
        Web[Web Frontend]
        Mobile[Mobile App]
        API_Client[API Client]
    end

    subgraph "Terra Backend (FastAPI)"
        subgraph "API Layer"
            Router[API Router /api/v1]
            AuthEP[Auth Endpoints]
            ChatEP[Chat Endpoint]
            DocsEP[Documents Endpoints]
            AgentsEP[Agents Endpoints]
            MCPEP[MCP Endpoints]
            HealthEP[Health Endpoints]
        end

        subgraph "Service Layer"
            AuthSvc[Auth Service]
            ChatSvc[Chatbot Service]
            DocSvc[Document Service]
            SearchSvc[Search Service]
            StaticKB[Static KB Service]
            BAClient[BA Jobs Client]
        end

        subgraph "Core Infrastructure"
            LLM[LLM Service - LiteLLM]
            Memory[Memory Store]
            ToolReg[Tool Registry]
            AgentReg[Agent Registry]
            MCPReg[MCP Registry]
            MCPClient[MCP Client]
            ORM[SQLAlchemy ORM]
        end
    end

    subgraph "External Services"
        OpenAI[OpenAI API]
        Anthropic[Anthropic API]
        Tavily[Tavily Search]
        BA_API[BA Jobsuche API]
        Integreat[Integreat CMS API]
        TerraMig[Terra-MIG MCP Server]
    end

    subgraph "Storage"
        SQLite[(SQLite Database)]
        KBFiles[Static KB JSON Files]
    end

    Web --> Router
    Mobile --> Router
    API_Client --> Router

    Router --> AuthEP
    Router --> ChatEP
    Router --> DocsEP
    Router --> AgentsEP
    Router --> MCPEP
    Router --> HealthEP

    AuthEP --> AuthSvc
    ChatEP --> ChatSvc
    DocsEP --> DocSvc
    AgentsEP --> AgentReg
    MCPEP --> MCPClient

    ChatSvc --> LLM
    ChatSvc --> Memory
    ChatSvc --> ToolReg
    DocSvc --> Memory

    AuthSvc --> ORM
    Memory --> ORM
    DocSvc --> ORM
    ORM --> SQLite

    LLM --> OpenAI
    LLM --> Anthropic
    ToolReg --> Tavily
    ToolReg --> BA_API
    StaticKB --> KBFiles
    MCPClient --> TerraMig
    StaticKB --> Integreat
```

## Request Lifecycle

```mermaid
sequenceDiagram
    participant C as Client
    participant MW as CORS Middleware
    participant R as Router
    participant D as Dependencies
    participant EP as Endpoint
    participant S as Service
    participant DB as Database

    C->>MW: HTTP Request
    MW->>R: Route to handler
    R->>D: Resolve dependencies (get_db, get_current_user)
    D->>DB: Validate session token
    DB-->>D: Session + User
    D->>EP: Inject dependencies
    EP->>S: Call service layer
    S-->>EP: Result
    EP-->>C: JSON Response
```

## Chatbot Orchestration Flow

The chatbot service is the core of Terra. It orchestrates memory retrieval, LLM calls, and tool execution in a loop.

```mermaid
sequenceDiagram
    participant U as User
    participant EP as /api/v1/chat
    participant CS as ChatbotService
    participant MS as MemoryStore
    participant LLM as LLMService
    participant TR as ToolRegistry
    participant T as Tool

    U->>EP: POST {message}
    EP->>CS: chat(user_id, message)

    CS->>MS: retrieve(user_id, limit=20)
    MS-->>CS: memory_entries[]

    Note over CS: Build messages:<br/>system + memory + user

    loop Max 5 rounds
        CS->>LLM: completion(messages, tool_schemas)
        LLM-->>CS: response (may include tool_calls)

        alt No tool calls
            Note over CS: Final response ready
        else Has tool calls
            loop For each tool_call
                CS->>TR: execute(tool_name, kwargs)
                TR->>T: execute(**kwargs)
                T-->>TR: ToolResult
                TR-->>CS: result
                Note over CS: Append tool result to messages
            end
        end
    end

    CS->>MS: add(user_id, "user", message)
    CS->>MS: add(user_id, "assistant", response)
    CS-->>EP: ChatResponse
    EP-->>U: JSON {response, used_tools}
```

## Memory Flow

```mermaid
flowchart LR
    subgraph "Memory Write"
        A[User Message] --> B[Store as user entry]
        C[Assistant Response] --> D[Store as assistant entry]
        E[Document Upload] --> F[Chunk 1000 chars / 100 overlap]
        F --> G[Store chunks as user entries with metadata]
    end

    subgraph "Memory Read"
        H[Chat Request] --> I[Retrieve last N entries]
        I --> J[Order by recency]
        J --> K[Include in LLM context]
    end

    subgraph "Database"
        L[(chat_memory table)]
    end

    B --> L
    D --> L
    G --> L
    L --> I
```

## Agent / Tool Orchestration

```mermaid
flowchart TB
    subgraph "Agent System"
        AR[Agent Registry]
        WS[web_search Agent]
        JL[job_listings Agent]
        SK[static_knowledge_base Agent]
    end

    subgraph "Tool System"
        TR[Tool Registry]
        T1[web_search]
        T2[search_ba_jobs]
        T3[get_ba_job_details]
        T4[search_static_kb]
        T5[get_static_kb_item]
        T6[list_static_kb_categories]
        T7[web_browse - stub]
        T8[custom_data_lookup - stub]
        T9[database_query - stub]
        T10[knowledge_retrieval - stub]
    end

    subgraph "Chatbot"
        CS[ChatbotService]
    end

    AR --> WS
    AR --> JL
    AR --> SK

    WS -.->|uses| T1
    JL -.->|uses| T2
    JL -.->|uses| T3
    SK -.->|uses| T4
    SK -.->|uses| T5
    SK -.->|uses| T6

    CS -->|all tools available| TR
    TR --> T1
    TR --> T2
    TR --> T3
    TR --> T4
    TR --> T5
    TR --> T6
    TR --> T7
    TR --> T8
    TR --> T9
    TR --> T10
```

## MCP Integration

```mermaid
sequenceDiagram
    participant C as Client
    participant EP as MCP Endpoints
    participant Svc as MCPService
    participant Reg as MCPRegistry
    participant Client as MCPClient
    participant Server as Terra-MIG Server

    Note over EP,Server: Startup: Tool Discovery
    EP->>Svc: discover_and_register_tools()
    Svc->>Reg: get_config("terra-mig")
    Reg-->>Svc: MCPServerConfig
    Svc->>Client: initialize()
    Client->>Server: JSON-RPC initialize
    Server-->>Client: session_id (SSE)
    Svc->>Client: list_tools()
    Client->>Server: JSON-RPC tools/list
    Server-->>Client: tool schemas (SSE)
    Svc->>Reg: register MCP tool adapters

    Note over EP,Server: Runtime: Tool Call
    C->>EP: POST /mcp/servers/terra-mig/call
    EP->>Svc: call_tool("terra-mig", tool_name, args)
    Svc->>Client: call_tool(tool_name, args)
    Client->>Server: JSON-RPC tools/call (SSE)
    Server-->>Client: result content
    Client-->>Svc: MCPToolCallResult
    Svc-->>EP: result
    EP-->>C: JSON response
```

### MCP Protocol Details

The MCP client uses **Streamable HTTP transport** (JSON-RPC over SSE):

1. **Initialize** — Establishes session, receives `Mcp-Session-Id` header
2. **Notification** — Sends `notifications/initialized` to confirm
3. **List Tools** — Discovers available tools and their schemas
4. **Call Tool** — Invokes a tool with arguments, receives structured content

The terra-mig MCP server provides 10 tools:
- `search_jobs` — Search BA job postings
- `get_job_detail` — Get full job detail by reference
- `map_profession_to_occupation` — Map free-text to KldB-2010 codes
- `get_salary_band` — Salary data for occupation codes
- `search_apprenticeships` — Vocational training offers
- `search_coaching` — AVGS coaching/activation offers
- `search_continuing_education` — Weiterbildung offers
- `query_recognition_stats` — Foreign qualification recognition stats
- `quickcheck_opportunity_card` — Chancenkarte points self-check
- `quickcheck_visa_route` — Candidate visa route suggestions

## Document Ingestion Pipeline

```mermaid
flowchart LR
    A[Client uploads<br/>plain text] --> B[POST /api/v1/documents]
    B --> C[Store in documents table]
    C --> D[Chunk content<br/>1000 chars / 100 overlap]
    D --> E[For each chunk]
    E --> F["Store in chat_memory<br/>[Document: title] chunk_text"]
    F --> G[Available to chatbot<br/>via memory retrieval]
```

### Chunking Strategy

- **Chunk size:** 1000 characters
- **Overlap:** 100 characters (ensures context continuity)
- **Format:** Each chunk is stored as a memory entry with the format `[Document: {title}] {chunk_text}`
- **Retrieval:** Chunks appear in the chatbot's memory context alongside conversation history

## Database Schema

```mermaid
erDiagram
    users {
        int id PK
        string username UK
        string password_hash
        datetime created_at
        datetime updated_at
    }

    sessions {
        int id PK
        string token UK
        int user_id FK
        datetime expires_at
        datetime created_at
    }

    chat_memory {
        int id PK
        int user_id FK
        string role
        text content
        json metadata
        datetime created_at
    }

    documents {
        int id PK
        int user_id FK
        string title
        text content
        string content_hash
        datetime created_at
        datetime updated_at
    }

    users ||--o{ sessions : "has"
    users ||--o{ chat_memory : "owns"
    users ||--o{ documents : "uploads"
```

## Startup Sequence

```mermaid
flowchart TD
    A[main.py — create_app] --> B[register_all]
    B --> C[Register 10 tools]
    B --> D[Register 3 agents]
    B --> E[Register MCP servers]

    A --> F[lifespan start]
    F --> G[Create DB tables]
    F --> H[Discover MCP tools]
    H --> I[Initialize MCP session]
    I --> J[List remote tools]
    J --> K[Register as tool adapters]

    A --> L[Include API router]
    L --> M[App ready — accepting requests]
```

## Key Design Decisions

1. **Async-first** — All I/O operations use async/await (SQLAlchemy async, httpx, aiosqlite)
2. **Registry pattern** — Tools, agents, and MCP servers use global registries with lazy initialization
3. **Memory as context** — Documents and conversations share the same memory system, making uploaded content automatically available to the chatbot
4. **Tool loop with cap** — The chatbot can call tools iteratively (max 5 rounds) to gather information before responding
5. **Non-fatal MCP** — MCP server discovery is best-effort; the app starts even if the MCP server is unreachable
6. **Session-based auth** — Simple Bearer tokens stored in DB; no JWT complexity needed for this use case
7. **SQLite for simplicity** — Single-file database appropriate for the current scale; easy to migrate to PostgreSQL via SQLAlchemy
