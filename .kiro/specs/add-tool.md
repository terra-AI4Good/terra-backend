# Spec: Add a New Tool

## Goal

Add a new tool that agents and the chatbot can call. Tools are the units of capability — web search, job search, KB lookup, etc.

## Steps

1. Create `src/terra/tools/<tool_name>.py`
2. Subclass `terra.tools.base.Tool`
3. Implement `definition` property returning a `ToolDefinition` with name, description, and parameters
4. Implement `async execute(self, **kwargs) -> ToolResult`
   - Return `ToolResult(success=True, data=...)` on success
   - Return `ToolResult(success=False, error="...")` on failure — never raise from execute
5. Register the tool in `src/terra/setup.py → _register_tools()`
6. Write tests in `tests/test_tools.py` — mock any external HTTP calls with `respx` or `unittest.mock`

## Template

```python
from terra.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult

class MyTool(Tool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="my_tool",
            description="Does something useful",
            parameters=[
                ToolParameter(name="query", type="string", description="The query"),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        try:
            result = await _do_something(query)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

## Checklist

- [ ] Tool name is snake_case and unique across all registered tools
- [ ] `execute` is async
- [ ] `execute` never raises — all errors go into `ToolResult.error`
- [ ] Tool registered in `setup.py`
- [ ] Tests written with mocked external calls
- [ ] `uv run pytest` passes
- [ ] `uv run ruff check . && mypy src/` passes
