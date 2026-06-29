"""Web search tool — generic, provider-agnostic search capability."""

from __future__ import annotations

from typing import Any

from terra.config import get_settings
from terra.services.search.base import SearchProvider, SearchResponse
from terra.services.search.tavily import TavilySearchProvider
from terra.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


def _get_search_provider() -> SearchProvider:
    """Build the configured search provider."""
    settings = get_settings()
    api_key = settings.tavily_api_key or settings.search_api_key or ""
    return TavilySearchProvider(
        api_key=api_key,
        timeout=settings.tavily_timeout_seconds,
    )


class WebSearchTool(Tool):
    """Search the web for current information using Tavily (or other provider).

    Returns structured results with title, URL, snippet, and domain.
    """

    def __init__(self, provider: SearchProvider | None = None) -> None:
        self._provider = provider

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description=(
                "Search the web for current information on any topic. "
                "Returns titles, URLs, and snippets from relevant pages."
            ),
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search query.",
                    required=True,
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Max results to return (1-20, default 5).",
                    required=False,
                ),
                ToolParameter(
                    name="search_depth",
                    type="string",
                    description="'basic' (fast) or 'advanced' (thorough).",
                    required=False,
                    enum=["basic", "advanced"],
                ),
                ToolParameter(
                    name="include_answer",
                    type="boolean",
                    description="Include an AI-generated answer summary.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute a web search."""
        query = kwargs.get("query", "")
        if not query:
            return ToolResult(success=False, error="query is required")

        settings = get_settings()
        max_results = kwargs.get("max_results", settings.tavily_default_max_results)
        search_depth = kwargs.get("search_depth", settings.tavily_search_depth)
        include_answer = kwargs.get("include_answer", False)

        provider = self._provider or _get_search_provider()

        try:
            response: SearchResponse = await provider.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=include_answer,
                include_domains=kwargs.get("include_domains"),
                exclude_domains=kwargs.get("exclude_domains"),
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Search failed: {e}")

        return ToolResult(
            success=True,
            data={
                "query": response.query,
                "answer": response.answer,
                "results": [r.model_dump() for r in response.results],
            },
        )
