"""MCP tool adapter — wraps MCP tools as standard Terra tools."""

from __future__ import annotations

from typing import Any

from terra.mcp.client import MCPClient
from terra.mcp.schemas import MCPToolSchema
from terra.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class MCPToolAdapter(Tool):
    """Adapter that wraps an MCP server tool as a standard Terra Tool.

    This allows MCP tools to be registered in the tool registry and
    used by the chatbot/orchestrator like any other tool.
    """

    def __init__(
        self,
        client: MCPClient,
        tool_schema: MCPToolSchema,
        server_name: str,
    ) -> None:
        self._client = client
        self._tool_schema = tool_schema
        self._server_name = server_name

    @property
    def definition(self) -> ToolDefinition:
        """Convert MCP tool schema to Terra ToolDefinition."""
        params = self._extract_parameters()
        # Prefix tool name with server name to avoid collisions
        tool_name = f"mcp_{self._server_name}_{self._tool_schema.name}"
        return ToolDefinition(
            name=tool_name,
            description=self._tool_schema.description,
            parameters=params,
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Call the MCP tool via the client."""
        result = await self._client.call_tool(self._tool_schema.name, kwargs)
        if not result.success:
            return ToolResult(
                success=False,
                error=result.error or "MCP tool call failed",
            )

        # Extract text content from MCP response
        text_parts: list[str] = []
        data_parts: list[Any] = []
        for item in result.content:
            if item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            else:
                data_parts.append(item)

        # Try to parse text as JSON for structured data
        import json

        data: Any = None
        if text_parts:
            try:
                data = json.loads(text_parts[0])
            except (json.JSONDecodeError, IndexError):
                data = {"text": "\n".join(text_parts)}

        if data_parts and not data:
            data = data_parts

        return ToolResult(success=True, data=data)

    def _extract_parameters(self) -> list[ToolParameter]:
        """Convert JSON Schema properties to ToolParameters."""
        schema = self._tool_schema.input_schema
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        params: list[ToolParameter] = []
        for name, prop in properties.items():
            # Resolve type from anyOf or direct type
            param_type = self._resolve_type(prop)
            params.append(
                ToolParameter(
                    name=name,
                    type=param_type,
                    description=prop.get("description", prop.get("title", "")),
                    required=name in required,
                )
            )
        return params

    def _resolve_type(self, prop: dict[str, Any]) -> str:
        """Resolve the JSON Schema type for a property."""
        if "type" in prop:
            return str(prop["type"])
        # Handle anyOf (nullable types)
        any_of = prop.get("anyOf", [])
        for option in any_of:
            t = option.get("type", "")
            if t and t != "null":
                return str(t)
        return "string"
