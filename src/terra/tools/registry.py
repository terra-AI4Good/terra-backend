"""Tool registry — central catalog of available tools."""

from __future__ import annotations

from typing import Any

from terra.tools.base import Tool, ToolResult


class ToolRegistry:
    """Registry that holds tool instances by name.

    Provides lookup, listing, and execution dispatch.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            msg = f"Tool '{tool.name}' is already registered"
            raise ValueError(msg)
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        """Look up a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        """Return names of all registered tools."""
        return list(self._tools.keys())

    def get_openai_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible tool schemas for all registered tools."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """Execute a tool by name.

        Args:
            name: Registered tool name.
            **kwargs: Arguments to pass to the tool.

        Returns:
            ToolResult from the tool execution.

        Raises:
            KeyError: If the tool is not found.
        """
        tool = self._tools.get(name)
        if tool is None:
            msg = f"Tool '{name}' not found in registry"
            raise KeyError(msg)
        return await tool.execute(**kwargs)

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# Global default registry — tools auto-register here
tool_registry = ToolRegistry()
