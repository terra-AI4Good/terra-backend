"""Tests for the tool system."""

import pytest

from terra.services.search.base import SearchProvider, SearchResponse, SearchResult
from terra.tools.base import ToolDefinition, ToolParameter
from terra.tools.browser import WebBrowserTool
from terra.tools.custom_data import CustomDataTool
from terra.tools.database import DatabaseQueryTool
from terra.tools.knowledge import KnowledgeRetrievalTool
from terra.tools.registry import ToolRegistry
from terra.tools.search import WebSearchTool


class _MockProvider(SearchProvider):
    async def search(self, query: str, **kwargs) -> SearchResponse:
        return SearchResponse(
            query=query,
            results=[
                SearchResult(
                    title="Mock",
                    url="https://mock.test",
                    snippet="mock result",
                    domain="mock.test",
                )
            ],
        )


class TestToolRegistry:
    def test_register_and_lookup(self):
        registry = ToolRegistry()
        tool = WebSearchTool(provider=_MockProvider())
        registry.register(tool)

        assert "web_search" in registry
        assert registry.get("web_search") is tool
        assert len(registry) == 1

    def test_register_duplicate_raises(self):
        registry = ToolRegistry()
        tool = WebSearchTool(provider=_MockProvider())
        registry.register(tool)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool)

    def test_unregister(self):
        registry = ToolRegistry()
        tool = WebSearchTool()
        registry.register(tool)
        registry.unregister("web_search")

        assert "web_search" not in registry
        assert len(registry) == 0

    def test_list_names(self):
        registry = ToolRegistry()
        registry.register(WebSearchTool(provider=_MockProvider()))
        registry.register(WebBrowserTool())

        names = registry.list_names()
        assert "web_search" in names
        assert "web_browse" in names

    def test_get_openai_schemas(self):
        registry = ToolRegistry()
        registry.register(WebSearchTool(provider=_MockProvider()))

        schemas = registry.get_openai_schemas()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "web_search"

    async def test_execute_tool(self):
        registry = ToolRegistry()
        registry.register(WebSearchTool(provider=_MockProvider()))

        result = await registry.execute("web_search", query="test")
        assert result.success is True
        assert result.data["query"] == "test"

    async def test_execute_unknown_tool_raises(self):
        registry = ToolRegistry()

        with pytest.raises(KeyError, match="not found"):
            await registry.execute("nonexistent")


class TestToolImplementations:
    """Verify all placeholder tools can be imported and instantiated."""

    def test_web_search_tool(self):
        tool = WebSearchTool(provider=_MockProvider())
        assert tool.name == "web_search"
        assert tool.definition.parameters

    def test_web_browser_tool(self):
        tool = WebBrowserTool()
        assert tool.name == "web_browse"

    def test_custom_data_tool(self):
        tool = CustomDataTool()
        assert tool.name == "custom_data_lookup"

    def test_database_query_tool(self):
        tool = DatabaseQueryTool()
        assert tool.name == "database_query"

    def test_knowledge_retrieval_tool(self):
        tool = KnowledgeRetrievalTool()
        assert tool.name == "knowledge_retrieval"


class TestToolDefinition:
    def test_to_openai_schema(self):
        defn = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True,
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Max results",
                    required=False,
                ),
            ],
        )

        schema = defn.to_openai_schema()
        assert schema["function"]["name"] == "test_tool"
        assert "query" in schema["function"]["parameters"]["properties"]
        assert "query" in schema["function"]["parameters"]["required"]
        assert "limit" not in schema["function"]["parameters"]["required"]
