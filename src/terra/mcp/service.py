"""MCP service — high-level operations for managing MCP servers and tools."""

from __future__ import annotations

from typing import Any

from terra.mcp.registry import MCPRegistry, mcp_registry
from terra.mcp.schemas import MCPToolCallResult, MCPToolSchema
from terra.mcp.tool_adapter import MCPToolAdapter
from terra.tools.registry import ToolRegistry, tool_registry


class MCPService:
    """High-level MCP service for the application.

    Manages server discovery, tool registration, and execution.
    """

    def __init__(
        self,
        registry: MCPRegistry | None = None,
        tool_reg: ToolRegistry | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._registry = registry if registry is not None else mcp_registry
        self._tool_reg = tool_reg if tool_reg is not None else tool_registry
        self._timeout = timeout
        self._discovered_tools: dict[str, list[MCPToolSchema]] = {}

    async def discover_and_register_tools(self, server_name: str) -> int:
        """Connect to an MCP server, discover tools, and register them.

        Returns the number of tools registered.
        """
        client = self._registry.get_client(server_name, timeout=self._timeout)
        if client is None:
            return 0

        tools = await client.list_tools()
        self._discovered_tools[server_name] = tools

        registered = 0
        for tool_schema in tools:
            adapter = MCPToolAdapter(
                client=client,
                tool_schema=tool_schema,
                server_name=server_name,
            )
            # Only register if not already present
            if adapter.name not in self._tool_reg:
                self._tool_reg.register(adapter)
                registered += 1

        return registered

    async def health_check(self, server_name: str) -> bool:
        """Check health of a specific MCP server."""
        client = self._registry.get_client(server_name, timeout=self._timeout)
        if client is None:
            return False
        return await client.health_check()

    async def list_server_tools(self, server_name: str) -> list[MCPToolSchema]:
        """List tools for a specific server (from cache or discovery)."""
        if server_name in self._discovered_tools:
            return self._discovered_tools[server_name]

        client = self._registry.get_client(server_name, timeout=self._timeout)
        if client is None:
            return []

        tools = await client.list_tools()
        self._discovered_tools[server_name] = tools
        return tools

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> MCPToolCallResult:
        """Call a tool on a specific MCP server."""
        client = self._registry.get_client(server_name, timeout=self._timeout)
        if client is None:
            return MCPToolCallResult(
                success=False,
                error=f"Server '{server_name}' not found or disabled",
                is_error=True,
            )
        return await client.call_tool(tool_name, arguments)
