"""Tests for MCP server integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from terra.mcp.client import MCPClient
from terra.mcp.registry import MCPRegistry
from terra.mcp.schemas import MCPServerConfig, MCPToolSchema
from terra.mcp.service import MCPService
from terra.mcp.tool_adapter import MCPToolAdapter
from terra.tools.registry import ToolRegistry


def _terra_mig_config() -> MCPServerConfig:
    return MCPServerConfig(
        name="terra-mig",
        description="Migration MCP server",
        health_url="https://example.com/health",
        endpoint_url="https://example.com/mcp",
        enabled=True,
    )


class TestMCPConfig:
    def test_config_loads_mcp_settings(self):
        from terra.config import Settings

        settings = Settings(
            mcp_enabled=True,
            mcp_terra_mig_name="terra-mig",
            mcp_terra_mig_health_url="https://x.com/health",
            mcp_terra_mig_endpoint_url="https://x.com/mcp",
        )
        assert settings.mcp_enabled is True
        assert settings.mcp_terra_mig_name == "terra-mig"

    def test_config_mcp_disabled(self):
        from terra.config import Settings

        settings = Settings(mcp_enabled=False)
        assert settings.mcp_enabled is False


class TestMCPRegistry:
    def test_register_and_list(self):
        registry = MCPRegistry()
        config = _terra_mig_config()
        registry.register(config)

        assert "terra-mig" in registry
        assert len(registry) == 1
        assert registry.list_names() == ["terra-mig"]

    def test_get_config(self):
        registry = MCPRegistry()
        config = _terra_mig_config()
        registry.register(config)

        result = registry.get_config("terra-mig")
        assert result is not None
        assert result.name == "terra-mig"
        assert result.endpoint_url == "https://example.com/mcp"

    def test_get_client(self):
        registry = MCPRegistry()
        registry.register(_terra_mig_config())

        client = registry.get_client("terra-mig")
        assert client is not None
        assert client.server_name == "terra-mig"

    def test_get_client_disabled(self):
        registry = MCPRegistry()
        config = _terra_mig_config()
        config.enabled = False
        registry.register(config)

        client = registry.get_client("terra-mig")
        assert client is None

    def test_global_registry_has_terra_mig(self):
        """After app startup, the global registry should have terra-mig."""
        from terra.mcp.registry import mcp_registry
        from terra.setup import register_all

        register_all()
        assert "terra-mig" in mcp_registry


class TestMCPClient:
    async def test_health_check_success(self):
        config = _terra_mig_config()
        client = MCPClient(config=config)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = AsyncMock(status_code=200)
            result = await client.health_check()
            assert result is True

    async def test_health_check_failure(self):
        config = _terra_mig_config()
        client = MCPClient(config=config)

        with patch("terra.mcp.client.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=OSError("Connection refused"))
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.health_check()
            assert result is False

    async def test_initialize_captures_session(self):
        config = _terra_mig_config()
        client = MCPClient(config=config)

        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"mcp-session-id": "test-session-123"}
        mock_resp.text = (
            "event: message\n"
            'data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05",'
            '"capabilities":{},"serverInfo":{"name":"test","version":"1.0"}}}\n'
        )
        mock_resp.raise_for_status = AsyncMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await client.initialize()
            assert client._session_id == "test-session-123"
            assert "protocolVersion" in result

    async def test_list_tools(self):
        config = _terra_mig_config()
        client = MCPClient(config=config)
        client._session_id = "existing-session"

        tool_response = (
            "event: message\n"
            'data: {"jsonrpc":"2.0","id":2,"result":{"tools":['
            '{"name":"search_jobs","description":"Search jobs",'
            '"inputSchema":{"properties":{"was":{"type":"string"}},"type":"object"}}'
            "]}}\n"
        )
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = tool_response
        mock_resp.headers = {}
        mock_resp.raise_for_status = AsyncMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            tools = await client.list_tools()
            assert len(tools) == 1
            assert tools[0].name == "search_jobs"
            assert tools[0].description == "Search jobs"

    async def test_call_tool(self):
        config = _terra_mig_config()
        client = MCPClient(config=config)
        client._session_id = "existing-session"

        call_response = (
            "event: message\n"
            'data: {"jsonrpc":"2.0","id":3,"result":{"content":'
            '[{"type":"text","text":"{\\"results\\": []}"}],"isError":false}}\n'
        )
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = call_response
        mock_resp.headers = {}
        mock_resp.raise_for_status = AsyncMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await client.call_tool("search_jobs", {"was": "Python"})
            assert result.success is True
            assert len(result.content) == 1


class TestMCPToolAdapter:
    def test_adapter_creates_tool_definition(self):
        config = _terra_mig_config()
        client = MCPClient(config=config)
        schema = MCPToolSchema(
            name="search_jobs",
            description="Search for jobs",
            input_schema={
                "properties": {
                    "was": {"type": "string", "title": "Keyword"},
                    "wo": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "title": "Location",
                    },
                },
                "required": ["was"],
                "type": "object",
            },
        )
        adapter = MCPToolAdapter(
            client=client, tool_schema=schema, server_name="terra-mig"
        )

        assert adapter.name == "mcp_terra-mig_search_jobs"
        defn = adapter.definition
        assert defn.description == "Search for jobs"
        param_names = [p.name for p in defn.parameters]
        assert "was" in param_names
        assert "wo" in param_names

    def test_adapter_openai_schema(self):
        config = _terra_mig_config()
        client = MCPClient(config=config)
        schema = MCPToolSchema(
            name="get_salary",
            description="Get salary",
            input_schema={
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
                "type": "object",
            },
        )
        adapter = MCPToolAdapter(
            client=client, tool_schema=schema, server_name="terra-mig"
        )
        openai = adapter.to_openai_schema()
        assert openai["function"]["name"] == "mcp_terra-mig_get_salary"
        assert "code" in openai["function"]["parameters"]["required"]

    async def test_adapter_execute_calls_mcp(self):
        config = _terra_mig_config()
        client = MCPClient(config=config)
        client._session_id = "test"
        schema = MCPToolSchema(name="test_tool", description="Test")

        adapter = MCPToolAdapter(client=client, tool_schema=schema, server_name="test")

        call_response = (
            "event: message\n"
            'data: {"jsonrpc":"2.0","id":1,"result":{"content":'
            '[{"type":"text","text":"{\\"answer\\": 42}"}],"isError":false}}\n'
        )
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = call_response
        mock_resp.headers = {}
        mock_resp.raise_for_status = AsyncMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await adapter.execute(param1="value1")
            assert result.success is True
            assert result.data["answer"] == 42


class TestMCPService:
    async def test_discover_registers_tools(self):
        registry = MCPRegistry()
        config = _terra_mig_config()
        registry.register(config)
        tool_reg = ToolRegistry()

        service = MCPService(registry=registry, tool_reg=tool_reg)

        # Get the real client that the service will use
        real_client = registry.get_client("terra-mig")
        assert real_client is not None

        # Patch list_tools on the real client instance
        real_client.list_tools = AsyncMock(  # type: ignore[method-assign]
            return_value=[
                MCPToolSchema(
                    name="tool_a",
                    description="Tool A",
                    input_schema={"properties": {}, "type": "object"},
                ),
                MCPToolSchema(
                    name="tool_b",
                    description="Tool B",
                    input_schema={"properties": {}, "type": "object"},
                ),
            ]
        )

        count = await service.discover_and_register_tools("terra-mig")
        assert count == 2
        assert "mcp_terra-mig_tool_a" in tool_reg
        assert "mcp_terra-mig_tool_b" in tool_reg


class TestMCPApiEndpoints:
    async def test_list_servers(self, client: AsyncClient):
        # Register and get token
        resp = await client.post(
            "/api/v1/auth/register",
            json={"username": "mcpuser", "password": "mcppass123!"},
        )
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/mcp/servers", headers=headers)
        assert response.status_code == 200
        servers = response.json()
        assert len(servers) >= 1
        names = {s["name"] for s in servers}
        assert "terra-mig" in names

    async def test_get_server(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"username": "mcpuser2", "password": "mcppass123!"},
        )
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/mcp/servers/terra-mig", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "terra-mig"
        assert data["enabled"] is True

    async def test_get_server_not_found(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"username": "mcpuser3", "password": "mcppass123!"},
        )
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/mcp/servers/nonexistent", headers=headers)
        assert response.status_code == 404

    async def test_unauthenticated_rejected(self, client: AsyncClient):
        response = await client.get("/api/v1/mcp/servers")
        assert response.status_code == 401
