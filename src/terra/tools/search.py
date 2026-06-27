"""Web search tool (placeholder)."""

from __future__ import annotations

from typing import Any

from terra.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class WebSearchTool(Tool):
    """Search the web for information.

    Placeholder — will be backed by a search API (e.g. Tavily, Serper, Brave).
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Search the web for current information on a topic.",
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
                    description="Maximum number of results to return.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute web search (stub)."""
        query = kwargs.get("query", "")
        return ToolResult(
            success=True,
            data={
                "query": query,
                "results": [],
                "message": "Web search not yet implemented",
            },
        )
