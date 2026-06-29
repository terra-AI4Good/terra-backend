# MCP Servers for Terra Backend

## Active

**postman** — manually configured (already set up). Use for API testing against the live ECS endpoint or local dev server.

## Available to add

### filesystem

Gives Kiro direct read/write access to project files. Useful when you want to ask "show me all tool implementations" or "what endpoints does this router expose" without manually navigating files.

To enable: add `filesystem` from `servers.json` to your Kiro MCP settings.

### sqlite

Lets Kiro query `terra.db` directly with SQL. Useful for:
- Checking what's stored in the memory table after a chat session
- Inspecting user/session records during auth debugging
- Verifying document uploads wrote correctly

```sql
-- Example queries
SELECT * FROM memory WHERE user_id = 1 ORDER BY created_at DESC LIMIT 10;
SELECT username, created_at FROM user ORDER BY created_at DESC;
SELECT title, content_hash FROM document WHERE user_id = 1;
```

To enable: add `sqlite` from `servers.json` to your Kiro MCP settings.

### github

For PR workflows, issue linking, and branch management directly from Kiro chat. Requires `GITHUB_TOKEN` env var.

To enable: set `GITHUB_TOKEN` and add `github` from `servers.json`.

## Live service

Base URL: `https://te-a73b2850f57649d68b871f55469b5c69.ecs.us-west-2.on.aws`

Postman collection should target this URL. Auth: `POST /api/v1/auth/login` → Bearer token for subsequent requests.
