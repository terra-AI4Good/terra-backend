"""Static knowledge base tools — search Integreat integration pages."""

from __future__ import annotations

from typing import Any

from terra.services.static_kb import StaticKBService
from terra.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class SearchStaticKBTool(Tool):
    """Search the static knowledge base (Integreat pages)."""

    def __init__(self, service: StaticKBService | None = None) -> None:
        self._service = service

    def _get_service(self) -> StaticKBService:
        return self._service or StaticKBService.get_default()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_static_kb",
            description=(
                "Search the Integreat integration knowledge base for "
                "information about living in Germany — topics like "
                "healthcare, education, work, housing, legal info, etc."
            ),
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search terms (German or English).",
                    required=True,
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Max results (default 5).",
                    required=False,
                ),
                ToolParameter(
                    name="category",
                    type="string",
                    description="Filter by category slug.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Search the knowledge base."""
        query = kwargs.get("query", "")
        if not query:
            return ToolResult(success=False, error="query is required")

        limit = kwargs.get("limit", 5)
        category = kwargs.get("category")

        service = self._get_service()
        results = service.search(query=query, limit=limit, category=category)

        # Return compact results (no full HTML content)
        compact = [
            {
                "id": r["id"],
                "title": r["title"],
                "category": r["category"],
                "snippet": r.get("content_text", "")[:200],
                "url": r.get("url", ""),
                "path": r.get("path", ""),
            }
            for r in results
        ]

        return ToolResult(
            success=True,
            data={"query": query, "results": compact, "total": len(compact)},
        )


class GetStaticKBItemTool(Tool):
    """Fetch a specific page from the static knowledge base by ID."""

    def __init__(self, service: StaticKBService | None = None) -> None:
        self._service = service

    def _get_service(self) -> StaticKBService:
        return self._service or StaticKBService.get_default()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_static_kb_item",
            description="Get full details of an Integreat page by its ID.",
            parameters=[
                ToolParameter(
                    name="item_id",
                    type="string",
                    description="The page ID.",
                    required=True,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Fetch a page by ID."""
        item_id = kwargs.get("item_id", "")
        if not item_id:
            return ToolResult(success=False, error="item_id is required")

        service = self._get_service()
        item = service.get_item(item_id)

        if item is None:
            return ToolResult(success=False, error=f"Page '{item_id}' not found")

        # Return without full HTML
        result = {
            "id": item["id"],
            "title": item["title"],
            "category": item["category"],
            "content": item.get("content_text", ""),
            "url": item.get("url", ""),
            "path": item.get("path", ""),
            "modified": item.get("modified", ""),
            "languages": item.get("languages", []),
        }
        return ToolResult(success=True, data=result)


class ListStaticKBCategoriesTool(Tool):
    """List all categories in the static knowledge base."""

    def __init__(self, service: StaticKBService | None = None) -> None:
        self._service = service

    def _get_service(self) -> StaticKBService:
        return self._service or StaticKBService.get_default()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_static_kb_categories",
            description=("List all topic categories in the Integreat knowledge base."),
            parameters=[],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:  # noqa: ARG002
        """List categories."""
        service = self._get_service()
        categories = service.list_categories()
        return ToolResult(success=True, data={"categories": categories})
