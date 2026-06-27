"""Custom internal data lookup tool (placeholder)."""

from __future__ import annotations

from typing import Any

from terra.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class CustomDataTool(Tool):
    """Look up internal/custom data sources.

    Placeholder — will query internal databases, APIs, or data stores.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="custom_data_lookup",
            description="Query internal data sources for structured information.",
            parameters=[
                ToolParameter(
                    name="source",
                    type="string",
                    description="The data source identifier to query.",
                    required=True,
                ),
                ToolParameter(
                    name="query",
                    type="string",
                    description="The lookup query or filter expression.",
                    required=True,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Query internal data (stub)."""
        source = kwargs.get("source", "")
        query = kwargs.get("query", "")
        return ToolResult(
            success=True,
            data={
                "source": source,
                "query": query,
                "results": [],
                "message": "Custom data lookup not yet implemented",
            },
        )
