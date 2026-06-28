"""MCP HTTP client — Streamable HTTP transport (SSE-based)."""

from __future__ import annotations

import json
from typing import Any

import httpx

from terra.mcp.schemas import MCPServerConfig, MCPToolCallResult, MCPToolSchema


class MCPClient:
    """Client for an MCP server using the Streamable HTTP transport.

    Handles session initialization, tool listing, and tool calling
    over the JSON-RPC + SSE protocol.
    """

    def __init__(
        self,
        config: MCPServerConfig,
        timeout: float = 30.0,
    ) -> None:
        self._config = config
        self._timeout = timeout
        self._session_id: str | None = None
        self._request_id = 0

    @property
    def server_name(self) -> str:
        return self._config.name

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        headers.update(self._config.auth_headers)
        return headers

    async def health_check(self) -> bool:
        """Check if the MCP server is healthy."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(self._config.health_url)
                return resp.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    async def initialize(self) -> dict[str, Any]:
        """Initialize the MCP session."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "terra-backend", "version": "0.1.0"},
            },
        }
        result = await self._send(payload, expect_session=True)

        # Send initialized notification
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        await self._send_notification(notification)

        return result

    async def list_tools(self) -> list[MCPToolSchema]:
        """List all tools available on the MCP server."""
        if not self._session_id:
            await self.initialize()

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {},
        }
        result = await self._send(payload)
        tools: list[MCPToolSchema] = []
        for tool_data in result.get("tools", []):
            tools.append(
                MCPToolSchema(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    annotations=tool_data.get("annotations", {}),
                )
            )
        return tools

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> MCPToolCallResult:
        """Call a tool on the MCP server."""
        if not self._session_id:
            await self.initialize()

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        try:
            result = await self._send(payload)
            content = result.get("content", [])
            is_error = result.get("isError", False)
            return MCPToolCallResult(
                success=not is_error,
                content=content,
                is_error=is_error,
            )
        except Exception as e:
            return MCPToolCallResult(
                success=False,
                error=str(e),
                is_error=True,
            )

    async def _send(
        self, payload: dict[str, Any], expect_session: bool = False
    ) -> dict[str, Any]:
        """Send a JSON-RPC request and parse the SSE response."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                self._config.endpoint_url,
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()

            # Capture session ID from headers
            if expect_session:
                session_id = resp.headers.get("mcp-session-id")
                if session_id:
                    self._session_id = session_id

            # Parse SSE response
            return self._parse_sse_response(resp.text)

    async def _send_notification(self, payload: dict[str, Any]) -> None:
        """Send a notification (no response expected)."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            await client.post(
                self._config.endpoint_url,
                json=payload,
                headers=self._headers(),
            )

    def _parse_sse_response(self, text: str) -> dict[str, Any]:
        """Parse SSE event stream and extract the JSON-RPC result."""
        for line in text.split("\n"):
            if line.startswith("data: "):
                data = line[6:]
                parsed = json.loads(data)
                if "result" in parsed:
                    result: dict[str, Any] = parsed["result"]
                    return result
                if "error" in parsed:
                    error = parsed["error"]
                    msg = error.get("message", "MCP error")
                    raise RuntimeError(f"MCP error: {msg}")
        msg = "No valid response in SSE stream"
        raise RuntimeError(msg)
