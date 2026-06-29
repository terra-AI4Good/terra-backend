"""Web browsing / page fetching tool (placeholder)."""

from __future__ import annotations

from typing import Any

from terra.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class WebBrowserTool(Tool):
    """Fetch and extract content from a web page.

    Placeholder — will use httpx + readability or a headless browser.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_browse",
            description="Fetch a web page and extract its main text content.",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="The URL to fetch.",
                    required=True,
                ),
                ToolParameter(
                    name="extract_links",
                    type="boolean",
                    description="Whether to include links in the output.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Fetch page content (stub)."""
        url = kwargs.get("url", "")
        return ToolResult(
            success=True,
            data={
                "url": url,
                "content": "",
                "message": "Web browsing not yet implemented",
            },
        )
