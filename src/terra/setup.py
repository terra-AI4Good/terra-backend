"""Application startup — register all tools and agents into global registries."""

from __future__ import annotations

from terra.agents.base import AgentConfig
from terra.agents.job_listings import JobListingsAgent
from terra.agents.registry import agent_registry
from terra.agents.search_agent import SearchAgent
from terra.agents.static_kb_agent import StaticKnowledgeBaseAgent
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
    """Register all tools and agents. Safe to call multiple times."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    _register_tools()
    _register_agents()


def _register_tools() -> None:
    """Register all tool instances into the global tool registry."""
    tools = [
        # Web search (Tavily-backed)
        WebSearchTool(),
        # BA Jobsuche
        SearchBAJobsTool(),
        GetBAJobDetailsTool(),
        # Static knowledge base (Integreat)
        SearchStaticKBTool(),
        GetStaticKBItemTool(),
        ListStaticKBCategoriesTool(),
        # Placeholder tools
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
                description=("Search and rank German job listings from BA Jobsuche"),
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
