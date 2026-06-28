"""MCP schemas for server configuration and tool definitions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    name: str
    description: str = ""
    health_url: str
    endpoint_url: str
    enabled: bool = True
    auth_headers: dict[str, str] = Field(default_factory=dict)


class MCPToolSchema(BaseModel):
    """Schema for an MCP tool as reported by the server."""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    annotations: dict[str, Any] = Field(default_factory=dict)


class MCPToolCallResult(BaseModel):
    """Result from calling an MCP tool."""

    success: bool = True
    content: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    is_error: bool = False
