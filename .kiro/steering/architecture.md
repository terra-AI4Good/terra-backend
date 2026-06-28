# Terra Backend — Architecture Reference

## Request lifecycle (chatbot)

```
POST /api/v1/chat
  └─ chatbot.py endpoint
       └─ ChatbotService.chat(user_id, message)
            ├─ DatabaseMemoryStore.retrieve(user_id, query, limit=20)
            ├─ Build messages: [system] + [memory...] + [user]
            ├─ LLMService.completion(messages, tools=tool_schemas)
            │    └─ litellm.acompletion(...)
            ├─ Tool-call loop (max 5 rounds):
            │    └─ ToolRegistry.execute(tool_name, **kwargs)
            │         └─ Tool.execute(**kwargs) → ToolResult
            ├─ DatabaseMemoryStore.add(user, assistant messages)
            └─ ChatResponse(response, used_tools, memory_context)
```

## Request lifecycle (agents endpoint)

```
POST /api/v1/agents/run
  └─ agents.py endpoint
       └─ AgentRegistry.create(agent_name) → Agent instance
            └─ Agent.run(input_message, context)
                 └─ AgentRunner.run(input_message)
                      ├─ Tool-call loop (max 10 iterations):
                      │    └─ Agent.step(messages) → ChatMessage
                      │         └─ LLMService.completion(...)
                      │    └─ ToolRegistry.execute(tool_name, **kwargs)
                      └─ AgentResult(output, tool_calls_made, iterations)
```

## Tool-call loop comparison

| | ChatbotService | AgentRunner |
|--|--|--|
| Max rounds | 5 (`max_tool_rounds`) | 10 (`max_iterations`) |
| Hook support | No | Yes (ExecutionHook) |
| Memory | Yes | No |
| Used by | `/chat` endpoint | `/agents/run` endpoint |

## Data models

```
User
  ├─ id, username, password_hash, created_at
  └─ Sessions (one-to-many)
       └─ token, expires_at, user_id

Document
  └─ id, user_id, title, content, content_hash, created_at, updated_at

Memory
  └─ id, user_id, role, content, created_at
```

## Agent + Tool wiring

At startup, `setup.register_all()` is called from `app.py → create_app()`:

```
tool_registry ← [WebSearchTool, SearchBAJobsTool, GetBAJobDetailsTool,
                  SearchStaticKBTool, GetStaticKBItemTool, ListStaticKBCategoriesTool,
                  WebBrowserTool, CustomDataTool, DatabaseQueryTool, KnowledgeRetrievalTool]

agent_registry ← [
  web_search          uses: [web_search]
  job_listings        uses: [search_ba_jobs, get_ba_job_details]
  static_knowledge_base uses: [search_static_kb, get_static_kb_item, list_static_kb_categories]
]
```

## Static Knowledge Base

- Source: Integreat CMS REST API (`cms.integreat-app.de/testumgebung-frag-integreat/de/wp-json/extensions/v3/pages/`)
- Fetched by `scripts/fetch_static_kb.py` at container startup (non-blocking background task)
- Stored at `data/static_kb/processed/pages.json`
- Served by three tools: `search_static_kb`, `get_static_kb_item`, `list_static_kb_categories`

## LLM abstraction

All LLM calls go through `terra.llm.service.LLMService` which wraps LiteLLM. This means:
- Switch from OpenAI to Anthropic/Azure by changing `LLM_DEFAULT_MODEL` env var (e.g. `claude-3-5-sonnet-20241022`)
- Tool calling uses OpenAI function-calling format (LiteLLM normalises provider differences)
- No streaming currently — responses are buffered

## Evaluation framework

`terra.evals.base` defines `EvalSuite` / `EvalCase` / `EvalResult`. No concrete suites are implemented yet — this is a planned extension point for agent quality testing.
