# API Reference

Base URL: `http://localhost:8000`
All versioned endpoints are under `/api/v1`.
Protected endpoints require `Authorization: Bearer <token>`.
Interactive Swagger UI: `http://localhost:8000/docs`

---

## Health

### `GET /health`

Root health check. Used by load balancers (ALB/ECS health checks).

**Auth:** None

**Response `200`:**
```json
{"status": "healthy"}
```

---

### `GET /api/v1/health`

v1 health check.

**Auth:** None

**Response `200`:**
```json
{"status": "healthy"}
```

---

## Authentication

### `POST /api/v1/auth/register`

Register a new user account and return a session token.

**Auth:** None

**Request:**
```json
{
  "username": "alice",
  "password": "mysecurepassword"
}
```

| Field | Type | Constraints |
|---|---|---|
| `username` | string | 3–150 characters |
| `password` | string | 8–128 characters |

**Response `201`:**
```json
{
  "token": "a3f82b9c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
  "expires_at": "2026-06-29T12:00:00+00:00"
}
```

**Error `409 Conflict`:**
```json
{"detail": "Username 'alice' is already taken"}
```

---

### `POST /api/v1/auth/login`

Authenticate and return a session token.

**Auth:** None

**Request:**
```json
{
  "username": "alice",
  "password": "mysecurepassword"
}
```

**Response `200`:**
```json
{
  "token": "a3f82b...",
  "expires_at": "2026-06-29T12:00:00+00:00"
}
```

**Error `401 Unauthorized`:**
```json
{"detail": "Invalid username or password"}
```

---

### `POST /api/v1/auth/logout`

Invalidate the current session token.

**Auth:** Bearer

**Response `204`:** No content.

---

### `GET /api/v1/auth/me`

Return the currently authenticated user's public information.

**Auth:** Bearer

**Response `200`:**
```json
{
  "id": 1,
  "username": "alice",
  "created_at": "2026-06-28T10:00:00"
}
```

**Error `401 Unauthorized`:**
```json
{"detail": "Invalid or expired session"}
```

---

## Chat

### `POST /api/v1/chat`

Send a message to the AI assistant and receive a response.

The backend automatically manages conversation memory — no history needs to be included in the request. Memory is scoped per user and persists across sessions. The model may invoke tools automatically to answer the question.

**Auth:** Bearer

**Request:**
```json
{
  "message": "What healthcare options are available for newcomers in Germany?"
}
```

| Field | Type | Constraints |
|---|---|---|
| `message` | string | 1–10,000 characters |

**Response `200`:**
```json
{
  "response": "Newcomers in Germany have access to statutory health insurance (gesetzliche Krankenversicherung). As a new resident...",
  "used_tools": ["search_static_kb"],
  "memory_context": null
}
```

| Field | Type | Notes |
|---|---|---|
| `response` | string | Final assistant message |
| `used_tools` | string[] | Names of tools called during this turn |
| `memory_context` | array or null | Only populated when `DEBUG=true`; shows the retrieved memory entries |

**Example with job search:**
```json
{
  "response": "I found 23 software engineering positions in Munich. Here are the top matches:\n\n1. **Senior Softwareentwickler**...",
  "used_tools": ["search_ba_jobs", "get_ba_job_details"],
  "memory_context": null
}
```

---

## Documents

### `POST /api/v1/documents`

Upload a plain-text document. The document is chunked and indexed into the user's memory, making it available to the chatbot for retrieval.

**Auth:** Bearer

**Request:**
```json
{
  "title": "My Visa Approval Letter",
  "content": "Your application for a Blue Card has been approved. The card is valid until..."
}
```

| Field | Type | Constraints |
|---|---|---|
| `title` | string | 1–500 characters |
| `content` | string | 1–500,000 characters |

**Response `201`:**
```json
{
  "id": 42,
  "title": "My Visa Approval Letter",
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "created_at": "2026-06-28T10:30:00",
  "updated_at": "2026-06-28T10:30:00"
}
```

---

### `GET /api/v1/documents`

List all documents for the authenticated user. Returns metadata only (no content).

**Auth:** Bearer

**Response `200`:**
```json
[
  {
    "id": 42,
    "title": "My Visa Approval Letter",
    "content_hash": "e3b0c44...",
    "created_at": "2026-06-28T10:30:00",
    "updated_at": "2026-06-28T10:30:00"
  }
]
```

---

### `GET /api/v1/documents/{document_id}`

Fetch a specific document including full content.

**Auth:** Bearer

**Path parameter:** `document_id` — integer document ID.

**Response `200`:**
```json
{
  "id": 42,
  "title": "My Visa Approval Letter",
  "content": "Your application for a Blue Card has been approved...",
  "content_hash": "e3b0c44...",
  "created_at": "2026-06-28T10:30:00",
  "updated_at": "2026-06-28T10:30:00"
}
```

**Error `404`:**
```json
{"detail": "Document not found"}
```

---

### `DELETE /api/v1/documents/{document_id}`

Delete a document. Does not remove memory chunks already indexed from this document.

**Auth:** Bearer

**Response `204`:** No content.

**Error `404`:**
```json
{"detail": "Document not found"}
```

---

## Agents & Tools

### `GET /api/v1/agents`

List all registered agents.

**Auth:** None

**Response `200`:**
```json
[
  {
    "name": "web_search",
    "description": "Search the web for current information",
    "tools": ["web_search"]
  },
  {
    "name": "job_listings",
    "description": "Search and rank German job listings from BA Jobsuche",
    "tools": ["search_ba_jobs", "get_ba_job_details"]
  },
  {
    "name": "static_knowledge_base",
    "description": "Answer questions about living in Germany using the Integreat integration knowledge base",
    "tools": ["search_static_kb", "get_static_kb_item", "list_static_kb_categories"]
  }
]
```

---

### `GET /api/v1/tools`

List all registered tools (including dynamically-registered MCP tools).

**Auth:** None

**Response `200`:**
```json
[
  {"name": "web_search", "description": "Search the web for current information..."},
  {"name": "search_ba_jobs", "description": "Search German job listings..."},
  {"name": "search_static_kb", "description": "Search the Integreat integration knowledge base..."},
  {"name": "mcp_terra-mig_salary_info", "description": "Look up salary ranges for professions in Germany"}
]
```

---

### `POST /api/v1/agents/run`

Execute a registered agent directly, bypassing the chatbot.

**Auth:** None

**Request:**
```json
{
  "agent_name": "job_listings",
  "input_message": "software engineer jobs in Munich",
  "context": {
    "location": "München",
    "work_time": "vz"
  }
}
```

| Field | Type | Description |
|---|---|---|
| `agent_name` | string | Agent name from `GET /api/v1/agents` |
| `input_message` | string | User's request or task description |
| `context` | object | Optional agent-specific context (see per-agent notes below) |

**Context fields per agent:**

`job_listings`:
- `location` (string) — city/region filter
- `work_time` (string) — `vz`, `tz`, `ho`, `mj`
- `job_type` (int) — 1=job, 2=self-employment, 4=Ausbildung

`static_knowledge_base`:
- `limit` (int) — max results (default 5)
- `category` (string) — filter by category slug

`web_search`:
- `max_results` (int)
- `search_depth` (string) — `basic` or `advanced`
- `include_answer` (bool)

**Response `200` (success):**
```json
{
  "success": true,
  "output": "Found 47 total results. Here are the top matches:\n\n1. **Softwareentwickler (m/w/d)**\n   Employer: TechCorp GmbH\n   Location: München, Bayern\n   Work time: vz\n   Published: 2026-06-25\n   Why: Title matches 'software'\n   Link: https://www.arbeitsagentur.de/...\n   Source: BA Jobsuche (Bundesagentur für Arbeit)\n",
  "tool_calls_made": 1,
  "iterations": 1,
  "error": null
}
```

**Response `200` (agent not found):**
```json
{
  "success": false,
  "output": "",
  "tool_calls_made": 0,
  "iterations": 0,
  "error": "Agent 'unknown_agent' not found"
}
```

---

## MCP

### `GET /api/v1/mcp/servers`

List all configured MCP servers.

**Auth:** Bearer

**Response `200`:**
```json
[
  {
    "name": "terra-mig",
    "description": "Make-it-in-Germany / migration-related MCP server",
    "health_url": "https://te-....ecs.us-west-2.on.aws/health",
    "endpoint_url": "https://te-....ecs.us-west-2.on.aws/mcp",
    "enabled": true
  }
]
```

---

### `GET /api/v1/mcp/servers/{server_name}`

Get configuration for a specific MCP server.

**Auth:** Bearer

**Response `200`:** Single server object as above.

**Error `404`:**
```json
{"detail": "MCP server 'unknown' not found"}
```

---

### `GET /api/v1/mcp/servers/{server_name}/health`

Check if an MCP server is reachable.

**Auth:** Bearer

**Response `200`:**
```json
{"name": "terra-mig", "healthy": true}
```

---

### `GET /api/v1/mcp/servers/{server_name}/tools`

Discover tools available on an MCP server.

**Auth:** Bearer

**Response `200`:**
```json
[
  {
    "name": "salary_info",
    "description": "Look up salary ranges for professions in Germany",
    "input_schema": {
      "type": "object",
      "properties": {
        "profession": {"type": "string", "description": "Job title or profession"}
      },
      "required": ["profession"]
    }
  }
]
```

---

### `POST /api/v1/mcp/servers/{server_name}/call`

Call a tool on a specific MCP server directly.

**Auth:** Bearer

**Request:**
```json
{
  "tool_name": "salary_info",
  "arguments": {
    "profession": "software engineer"
  }
}
```

**Response `200` (success):**
```json
{
  "success": true,
  "content": [
    {
      "type": "text",
      "text": "{\"median_salary\": 65000, \"currency\": \"EUR\", \"range\": [48000, 95000]}"
    }
  ],
  "error": null
}
```

**Response `200` (tool error):**
```json
{
  "success": false,
  "content": [],
  "error": "Tool execution failed: profession not recognized"
}
```

---

## Error Reference

| Status | Meaning |
|---|---|
| `400 Bad Request` | Request body fails JSON parsing |
| `401 Unauthorized` | Missing, invalid, or expired Bearer token |
| `404 Not Found` | Resource does not exist or is not owned by the authenticated user |
| `409 Conflict` | Duplicate resource (username already taken) |
| `422 Unprocessable Entity` | Pydantic validation error |
| `500 Internal Server Error` | Unexpected server error |

Validation error format (422):
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "username"],
      "msg": "String should have at least 3 characters",
      "input": "ab"
    }
  ]
}
```
