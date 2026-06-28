# API Reference

Base URL: `http://localhost:8000`

All endpoints return JSON. Authentication uses Bearer tokens obtained from `/api/v1/auth/login` or `/api/v1/auth/register`.

## Authentication

All authenticated endpoints require the header:

```
Authorization: Bearer <session_token>
```

Tokens are 64-character hex strings with a 24-hour expiry.

---

## Health

### GET /health

Root-level health check (designed for ALB/ECS health probes).

**Auth:** None

```bash
curl http://localhost:8000/health
```

**Response 200:**

```json
{"status": "healthy"}
```

### GET /api/v1/health

API-level health check.

**Auth:** None

```bash
curl http://localhost:8000/api/v1/health
```

**Response 200:**

```json
{"status": "healthy"}
```

---

## Auth

### POST /api/v1/auth/register

Register a new user account and receive a session token.

**Auth:** None

**Request:**

```json
{
  "username": "string (3-150 chars)",
  "password": "string (8-128 chars)"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "johndoe", "password": "securepass123"}'
```

**Response 201:**

```json
{
  "token": "a3f8c9...64-char-hex-string",
  "expires_at": "2025-01-16T12:00:00"
}
```

**Response 409:**

```json
{"detail": "Username 'johndoe' is already taken"}
```

### POST /api/v1/auth/login

Authenticate with credentials and receive a session token.

**Auth:** None

**Request:**

```json
{
  "username": "string",
  "password": "string"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "johndoe", "password": "securepass123"}'
```

**Response 200:**

```json
{
  "token": "a3f8c9...64-char-hex-string",
  "expires_at": "2025-01-16T12:00:00"
}
```

**Response 401:**

```json
{"detail": "Invalid username or password"}
```

### POST /api/v1/auth/logout

Invalidate the current session.

**Auth:** Required

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <token>"
```

**Response 204:** No content

### GET /api/v1/auth/me

Get the current authenticated user's information.

**Auth:** Required

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <token>"
```

**Response 200:**

```json
{
  "id": 1,
  "username": "johndoe",
  "created_at": "2025-01-15T10:30:00"
}
```

**Response 401:**

```json
{"detail": "Invalid or expired session"}
```

---

## Chat

### POST /api/v1/chat

Send a message to the AI chatbot. The backend maintains conversation memory automatically — no history needs to be sent by the client.

**Auth:** Required

**Request:**

```json
{
  "message": "string (1-10000 chars)"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "What jobs are available for software engineers in Berlin?"}'
```

**Response 200:**

```json
{
  "response": "I found several software engineering positions in Berlin...",
  "used_tools": ["search_ba_jobs"],
  "memory_context": null
}
```

When `DEBUG=true`, `memory_context` includes the retrieved conversation history:

```json
{
  "response": "...",
  "used_tools": [],
  "memory_context": [
    {"role": "user", "content": "previous message"},
    {"role": "assistant", "content": "previous response"}
  ]
}
```

---

## Documents

### POST /api/v1/documents

Upload a plain-text document. The content is chunked and stored in memory, making it automatically available to the chatbot.

**Auth:** Required

**Request:**

```json
{
  "title": "string (1-500 chars)",
  "content": "string (1-500000 chars)"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"title": "My Resume", "content": "Software engineer with 5 years..."}'
```

**Response 201:**

```json
{
  "id": 1,
  "title": "My Resume",
  "content_hash": "abc123...",
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00"
}
```

### GET /api/v1/documents

List all documents for the authenticated user.

**Auth:** Required

```bash
curl http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer <token>"
```

**Response 200:**

```json
[
  {
    "id": 1,
    "title": "My Resume",
    "content_hash": "abc123...",
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
  }
]
```

### GET /api/v1/documents/{document_id}

Get a specific document including full content.

**Auth:** Required

```bash
curl http://localhost:8000/api/v1/documents/1 \
  -H "Authorization: Bearer <token>"
```

**Response 200:**

```json
{
  "id": 1,
  "title": "My Resume",
  "content": "Software engineer with 5 years...",
  "content_hash": "abc123...",
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00"
}
```

**Response 404:**

```json
{"detail": "Document not found"}
```

### DELETE /api/v1/documents/{document_id}

Delete a document.

**Auth:** Required

```bash
curl -X DELETE http://localhost:8000/api/v1/documents/1 \
  -H "Authorization: Bearer <token>"
```

**Response 204:** No content

**Response 404:**

```json
{"detail": "Document not found"}
```

---

## Agents

### GET /api/v1/agents

List all registered agents.

**Auth:** None

```bash
curl http://localhost:8000/api/v1/agents
```

**Response 200:**

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

### GET /api/v1/tools

List all registered tools.

**Auth:** None

```bash
curl http://localhost:8000/api/v1/tools
```

**Response 200:**

```json
[
  {"name": "web_search", "description": "Search the web using Tavily"},
  {"name": "search_ba_jobs", "description": "Search job listings from BA Jobsuche"},
  {"name": "get_ba_job_details", "description": "Get full details of a BA job listing"},
  {"name": "search_static_kb", "description": "Search the static knowledge base"},
  {"name": "get_static_kb_item", "description": "Get a specific knowledge base page"},
  {"name": "list_static_kb_categories", "description": "List knowledge base categories"},
  {"name": "web_browse", "description": "Browse a web page (stub)"},
  {"name": "custom_data_lookup", "description": "Custom data lookup (stub)"},
  {"name": "database_query", "description": "Database query (stub)"},
  {"name": "knowledge_retrieval", "description": "Knowledge retrieval (stub)"}
]
```

### POST /api/v1/agents/run

Execute a registered agent with an input message.

**Auth:** None

**Request:**

```json
{
  "agent_name": "string",
  "input_message": "string",
  "context": {}
}
```

```bash
curl -X POST http://localhost:8000/api/v1/agents/run \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "job_listings", "input_message": "Find Python developer jobs in Munich"}'
```

**Response 200:**

```json
{
  "success": true,
  "output": "I found 5 Python developer positions in Munich...",
  "tool_calls_made": 2,
  "iterations": 3,
  "error": null
}
```

**Response 200 (agent not found):**

```json
{
  "success": false,
  "output": "",
  "tool_calls_made": 0,
  "iterations": 0,
  "error": "Agent 'invalid_name' not found"
}
```

---

## MCP (Model Context Protocol)

All MCP endpoints require authentication.

### GET /api/v1/mcp/servers

List all configured MCP servers.

**Auth:** Required

```bash
curl http://localhost:8000/api/v1/mcp/servers \
  -H "Authorization: Bearer <token>"
```

**Response 200:**

```json
[
  {
    "name": "terra-mig",
    "description": "Make-it-in-Germany / migration-related MCP server",
    "health_url": "https://te-8423728b85714970bb70e62ee24f6cf4.ecs.us-west-2.on.aws/health",
    "endpoint_url": "https://te-8423728b85714970bb70e62ee24f6cf4.ecs.us-west-2.on.aws/mcp",
    "enabled": true
  }
]
```

### GET /api/v1/mcp/servers/{server_name}

Get configuration for a specific MCP server.

**Auth:** Required

```bash
curl http://localhost:8000/api/v1/mcp/servers/terra-mig \
  -H "Authorization: Bearer <token>"
```

**Response 200:**

```json
{
  "name": "terra-mig",
  "description": "Make-it-in-Germany / migration-related MCP server",
  "health_url": "https://...",
  "endpoint_url": "https://...",
  "enabled": true
}
```

**Response 404:**

```json
{"detail": "MCP server 'unknown' not found"}
```

### GET /api/v1/mcp/servers/{server_name}/health

Check if an MCP server is healthy.

**Auth:** Required

```bash
curl http://localhost:8000/api/v1/mcp/servers/terra-mig/health \
  -H "Authorization: Bearer <token>"
```

**Response 200:**

```json
{"name": "terra-mig", "healthy": true}
```

### GET /api/v1/mcp/servers/{server_name}/tools

List tools available on an MCP server.

**Auth:** Required

```bash
curl http://localhost:8000/api/v1/mcp/servers/terra-mig/tools \
  -H "Authorization: Bearer <token>"
```

**Response 200:**

```json
[
  {
    "name": "search_jobs",
    "description": "Search live job postings from the Bundesagentur fuer Arbeit",
    "input_schema": {
      "type": "object",
      "properties": {
        "was": {"type": "string", "description": "Job search keyword"},
        "wo": {"type": "string", "description": "Location"},
        "umkreis": {"type": "integer", "description": "Radius in km"}
      }
    }
  }
]
```

### POST /api/v1/mcp/servers/{server_name}/call

Call a tool on an MCP server.

**Auth:** Required

**Request:**

```json
{
  "tool_name": "string",
  "arguments": {}
}
```

```bash
curl -X POST http://localhost:8000/api/v1/mcp/servers/terra-mig/call \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"tool_name": "search_jobs", "arguments": {"was": "Software Engineer", "wo": "Berlin"}}'
```

**Response 200:**

```json
{
  "success": true,
  "content": [
    {"type": "text", "text": "Found 15 results..."}
  ],
  "error": null
}
```

**Response 200 (error):**

```json
{
  "success": false,
  "content": [],
  "error": "Tool 'unknown_tool' not found"
}
```

---

## Error Responses

All error responses follow the standard FastAPI format:

```json
{"detail": "Error message description"}
```

Common HTTP status codes:

| Code | Meaning |
|------|---------|
| 400 | Bad Request — validation error |
| 401 | Unauthorized — missing or invalid token |
| 404 | Not Found — resource doesn't exist |
| 409 | Conflict — resource already exists (e.g., duplicate username) |
| 422 | Unprocessable Entity — request body validation failed |
| 500 | Internal Server Error |

Validation errors (422) include field-level details:

```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "String should have at least 8 characters",
      "type": "string_too_short"
    }
  ]
}
```
