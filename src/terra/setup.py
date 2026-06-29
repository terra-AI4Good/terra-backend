"""Application startup: register tools, agents, and MCP servers."""

from __future__ import annotations

from terra.agents.base import AgentConfig
from terra.agents.job_listings import JobListingsAgent
from terra.agents.registry import agent_registry
from terra.agents.search_agent import SearchAgent
from terra.agents.static_kb_agent import StaticKnowledgeBaseAgent
from terra.config import get_settings
from terra.mcp.registry import mcp_registry
from terra.mcp.schemas import MCPServerConfig
from terra.tools.ba_jobs import GetBAJobDetailsTool, SearchBAJobsTool
from terra.tools.browser import WebBrowserTool
from terra.tools.custom_data import CustomDataTool
from terra.tools.database import DatabaseQueryTool
from terra.tools.knowledge import KnowledgeRetrievalTool
from terra.tools.registry import tool_registry
from terra.tools.search import WebSearchTool
from terra.tools.static_kb import (
    GetStaticKBItemTool,
    ListStaticKBCategoriesTool,
    SearchStaticKBTool,
)

_initialized = False


def register_all() -> None:
    """Register all tools, agents, and MCP servers. Safe to call multiple times."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    _register_tools()
    _register_agents()
    _register_mcp_servers()


def _register_tools() -> None:
    """Register all tool instances into the global tool registry."""
    tools = [
        WebSearchTool(),
        SearchBAJobsTool(),
        GetBAJobDetailsTool(),
        SearchStaticKBTool(),
        GetStaticKBItemTool(),
        ListStaticKBCategoriesTool(),
        WebBrowserTool(),
        CustomDataTool(),
        DatabaseQueryTool(),
        KnowledgeRetrievalTool(),
    ]
    for tool in tools:
        if tool.name not in tool_registry:
            tool_registry.register(tool)


def _register_agents() -> None:
    """Register all agent classes into the global agent registry."""
    agents: list[tuple[type, AgentConfig]] = [
        (
            SearchAgent,
            AgentConfig(
                name="web_search",
                description="Search the web for current information",
                tools=["web_search"],
            ),
        ),
        (
            JobListingsAgent,
            AgentConfig(
                name="job_listings",
                description="Search and rank German job listings from BA Jobsuche",
                tools=["search_ba_jobs", "get_ba_job_details"],
            ),
        ),
        (
            StaticKnowledgeBaseAgent,
            AgentConfig(
                name="static_knowledge_base",
                description=(
                    "Answer questions about living in Germany using "
                    "the Integreat integration knowledge base"
                ),
                tools=[
                    "search_static_kb",
                    "get_static_kb_item",
                    "list_static_kb_categories",
                ],
            ),
        ),
    ]
    for agent_cls, config in agents:
        if config.name not in agent_registry:
            agent_registry.register(agent_cls, config)


def _register_mcp_servers() -> None:
    """Register configured MCP servers."""
    settings = get_settings()
    if not settings.mcp_enabled:
        return

    terra_mig = MCPServerConfig(
        name=settings.mcp_terra_mig_name,
        description="Make-it-in-Germany / migration-related MCP server",
        health_url=settings.mcp_terra_mig_health_url,
        endpoint_url=settings.mcp_terra_mig_endpoint_url,
        enabled=True,
    )
    if terra_mig.name not in mcp_registry:
        mcp_registry.register(terra_mig)


async def discover_mcp_tools() -> int:
    """Discover and register tools from all enabled MCP servers.

    Call this during app startup (async context required).
    Returns total number of MCP tools registered.
    """
    from terra.mcp.service import MCPService

    settings = get_settings()
    if not settings.mcp_enabled:
        return 0

    service = MCPService(timeout=settings.mcp_request_timeout_seconds)
    total = 0
    for server in mcp_registry.list_servers():
        if server.enabled:
            try:
                count = await service.discover_and_register_tools(server.name)
                total += count
            except Exception:
                pass  # Non-fatal: server might be down
    return total
