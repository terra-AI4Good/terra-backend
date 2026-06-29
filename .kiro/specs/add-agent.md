# Spec: Add a New Agent

## Goal

Add a new agent that can be invoked via `POST /api/v1/agents/run` or used internally by the chatbot.

## Steps

1. Create `src/terra/agents/<agent_name>.py`
2. Subclass `terra.agents.base.Agent`
3. Implement `async run(self, input_message, context) -> AgentResult`
4. Implement `async step(self, messages) -> ChatMessage` — this is the LLM call
   - Use `LLMService` with the tool schemas from the agent's configured tools
5. Register in `src/terra/setup.py → _register_agents()` with an `AgentConfig` specifying:
   - `name`: unique snake_case identifier
   - `description`: one sentence shown in `GET /api/v1/agents`
   - `tools`: list of tool names the agent can call
   - `system_prompt`: task-specific instructions (optional but recommended)
6. Write tests in `tests/test_agents.py` or `tests/test_agents_api.py`

## AgentConfig fields

```python
AgentConfig(
    name="my_agent",
    description="One-line description for the API listing",
    system_prompt="You are a specialist in...",
    tools=["tool_a", "tool_b"],
    max_iterations=10,  # tool-call loops before giving up
)
```

## Checklist

- [ ] Agent name is unique in the registry
- [ ] `step()` calls `LLMService.completion()` with tool schemas
- [ ] All tools listed in `AgentConfig.tools` are registered in `tool_registry`
- [ ] Agent registered in `setup.py`
- [ ] Tests mock `LLMService.completion`
- [ ] `uv run pytest` passes
