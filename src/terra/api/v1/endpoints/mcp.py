"""MCP server management endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from terra.api.deps import get_current_user
from terra.mcp.registry import mcp_registry
from terra.mcp.service import MCPService
from terra.models.user import User

router = APIRouter()


# -- Schemas --


class MCPServerInfo(BaseModel):
    """MCP server info for API responses."""

    name: str
    description: str
    health_url: str
    endpoint_url: str
    enabled: bool


class MCPServerHealth(BaseModel):
    """MCP server health check result."""

    name: str
    healthy: bool


class MCPToolInfo(BaseModel):
    """MCP tool info."""

    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)


class MCPToolCallRequest(BaseModel):
    """Request to call an MCP tool."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPToolCallResponse(BaseModel):
    """Response from an MCP tool call."""

    success: bool
    content: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


# -- Endpoints --


@router.get("/mcp/servers", response_model=list[MCPServerInfo])
async def list_mcp_servers(
    user: User = Depends(get_current_user),  # noqa: ARG001
) -> list[MCPServerInfo]:
    """List all configured MCP servers."""
    return [
        MCPServerInfo(
            name=s.name,
            description=s.description,
            health_url=s.health_url,
            endpoint_url=s.endpoint_url,
            enabled=s.enabled,
        )
        for s in mcp_registry.list_servers()
    ]


@router.get("/mcp/servers/{server_name}", response_model=MCPServerInfo)
async def get_mcp_server(
    server_name: str,
    user: User = Depends(get_current_user),  # noqa: ARG001
) -> MCPServerInfo:
    """Get a specific MCP server configuration."""
    config = mcp_registry.get_config(server_name)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )
    return MCPServerInfo(
        name=config.name,
        description=config.description,
        health_url=config.health_url,
        endpoint_url=config.endpoint_url,
        enabled=config.enabled,
    )


@router.get("/mcp/servers/{server_name}/health", response_model=MCPServerHealth)
async def check_mcp_health(
    server_name: str,
    user: User = Depends(get_current_user),  # noqa: ARG001
) -> MCPServerHealth:
    """Check health of an MCP server."""
    if server_name not in mcp_registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )
    service = MCPService()
    healthy = await service.health_check(server_name)
    return MCPServerHealth(name=server_name, healthy=healthy)


@router.get("/mcp/servers/{server_name}/tools", response_model=list[MCPToolInfo])
async def list_mcp_tools(
    server_name: str,
    user: User = Depends(get_current_user),  # noqa: ARG001
) -> list[MCPToolInfo]:
    """List available tools on an MCP server."""
    if server_name not in mcp_registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )
    service = MCPService()
    tools = await service.list_server_tools(server_name)
    return [
        MCPToolInfo(
            name=t.name,
            description=t.description,
            input_schema=t.input_schema,
        )
        for t in tools
    ]


@router.post("/mcp/servers/{server_name}/call", response_model=MCPToolCallResponse)
async def call_mcp_tool(
    server_name: str,
    body: MCPToolCallRequest,
    user: User = Depends(get_current_user),  # noqa: ARG001
) -> MCPToolCallResponse:
    """Call a tool on an MCP server."""
    if server_name not in mcp_registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )
    service = MCPService()
    result = await service.call_tool(server_name, body.tool_name, body.arguments)
    return MCPToolCallResponse(
        success=result.success,
        content=result.content,
        error=result.error,
    )
