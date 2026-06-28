"""MCP server registry — manages configured MCP servers."""

from __future__ import annotations

from terra.mcp.client import MCPClient
from terra.mcp.schemas import MCPServerConfig


class MCPRegistry:
    """Registry of configured MCP servers."""

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerConfig] = {}
        self._clients: dict[str, MCPClient] = {}

    def register(self, config: MCPServerConfig) -> None:
        """Register an MCP server configuration."""
        self._servers[config.name] = config

    def unregister(self, name: str) -> None:
        """Remove a server from the registry."""
        self._servers.pop(name, None)
        self._clients.pop(name, None)

    def get_config(self, name: str) -> MCPServerConfig | None:
        """Get a server's configuration."""
        return self._servers.get(name)

    def get_client(self, name: str, timeout: float = 30.0) -> MCPClient | None:
        """Get or create an MCP client for a server."""
        config = self._servers.get(name)
        if config is None or not config.enabled:
            return None
        if name not in self._clients:
            self._clients[name] = MCPClient(config=config, timeout=timeout)
        return self._clients[name]

    def list_servers(self) -> list[MCPServerConfig]:
        """List all registered server configs."""
        return list(self._servers.values())

    def list_names(self) -> list[str]:
        """List names of all registered servers."""
        return list(self._servers.keys())

    def __len__(self) -> int:
        return len(self._servers)

    def __contains__(self, name: str) -> bool:
        return name in self._servers


# Global MCP registry
mcp_registry = MCPRegistry()
