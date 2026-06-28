# Hook: New Tool Checklist

## Trigger

When a new file is created under `src/terra/tools/` (excluding `__init__.py`, `base.py`, `registry.py`).

## Actions

Verify the following automatically and report any gaps:

1. **Subclasses Tool**: Check `class Foo(Tool):` is present
2. **Implements definition**: `def definition(self) -> ToolDefinition:` exists
3. **Implements execute**: `async def execute(self, **kwargs) -> ToolResult:` exists
4. **Registered in setup.py**: The class name appears in `src/terra/setup.py`
5. **Has test coverage**: A test file references the tool name (grep `tests/` for the tool name or class name)

## Report format

```
✓ Subclasses Tool
✓ definition property implemented
✗ execute is not async — add `async` keyword
✗ Not registered in setup.py — add to _register_tools()
✗ No tests found — create tests/test_tools.py entries
```

Flag gaps but don't block — remind the developer to address them before committing.
