# Spec: End-to-End Cycle Test

## Goal

Verify the full request lifecycle works correctly: register → login → chat → agents → documents. This is a smoke test for the entire system using only the test client (no real LLM, no real server).

## Steps

### Phase 1: Auth cycle
1. `POST /api/v1/auth/register` → get token
2. `GET /api/v1/auth/me` with token → verify user info returned
3. `POST /api/v1/auth/login` with same credentials → get new token
4. `POST /api/v1/auth/logout` → 204
5. Verify the old token is invalidated: `GET /api/v1/auth/me` → 401

### Phase 2: Chatbot cycle (mock LLM)
1. Register fresh user, get token
2. Mock `LLMService.completion` to return `LLMResponse(content="Hello!", tool_calls=[])`
3. `POST /api/v1/chat` with message → verify 200 + response field present
4. Send second message → verify LLM receives memory context (≥ 4 messages in call args)

### Phase 3: Document cycle
1. `POST /api/v1/documents` with title + content → 201, get doc id
2. `GET /api/v1/documents` → list contains the document
3. `GET /api/v1/documents/{id}` → full content returned
4. `DELETE /api/v1/documents/{id}` → 204
5. `GET /api/v1/documents/{id}` → 404

### Phase 4: Agents cycle
1. `GET /api/v1/agents` → list contains `web_search`, `job_listings`, `static_knowledge_base`
2. `GET /api/v1/tools` → list contains all registered tools
3. `GET /api/v1/agents/health` → 200
4. `POST /api/v1/agents/run` with unknown agent → `success: false`, error message

### Phase 5: Health checks
1. `GET /health` → `{"status": "healthy"}`
2. `GET /api/v1/health` → 200

## Pass criteria

- All phases complete without assertion errors
- No real LLM/API calls made
- Runs under 10 seconds

## Running

```bash
uv run pytest tests/ -k "e2e" -v
```

(Once implemented as `tests/test_e2e.py`)
