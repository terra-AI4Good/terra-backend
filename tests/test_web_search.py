"""Tests for the web search tool and agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from terra.agents.search_agent import SearchAgent
from terra.services.search.base import SearchProvider, SearchResponse, SearchResult
from terra.services.search.tavily import TavilySearchProvider
from terra.tools.search import WebSearchTool

# -- Mock Provider --


class MockSearchProvider(SearchProvider):
    """In-memory search provider for testing."""

    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self._results = results or [
            SearchResult(
                title="Test Result 1",
                url="https://example.com/page1",
                snippet="This is a test result about AI.",
                domain="example.com",
                score=0.95,
            ),
            SearchResult(
                title="Test Result 2",
                url="https://docs.python.org/3/",
                snippet="Python documentation for developers.",
                domain="docs.python.org",
                score=0.85,
            ),
        ]

    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
        include_answer: bool = False,
        include_raw_content: bool = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> SearchResponse:
        results = self._results[:max_results]
        answer = "AI summary of results" if include_answer else None
        return SearchResponse(query=query, results=results, answer=answer)


# -- Config Tests --


class TestSearchConfig:
    def test_tavily_provider_requires_api_key(self):
        with pytest.raises(ValueError, match="TAVILY_API_KEY"):
            TavilySearchProvider(api_key="")

    def test_tavily_provider_accepts_api_key(self):
        provider = TavilySearchProvider(api_key="test-key-123")
        assert provider._api_key == "test-key-123"

    def test_config_loads_search_settings(self):
        from terra.config import Settings

        settings = Settings(
            tavily_api_key="my-key",
            tavily_search_depth="advanced",
            tavily_default_max_results=10,
        )
        assert settings.tavily_api_key == "my-key"
        assert settings.tavily_search_depth == "advanced"
        assert settings.tavily_default_max_results == 10


# -- Tool Tests --


class TestWebSearchTool:
    def test_definition(self):
        tool = WebSearchTool()
        assert tool.name == "web_search"
        assert "query" in [p.name for p in tool.definition.parameters]

    def test_openai_schema(self):
        tool = WebSearchTool()
        schema = tool.to_openai_schema()
        assert schema["function"]["name"] == "web_search"
        props = schema["function"]["parameters"]["properties"]
        assert "query" in props
        assert "max_results" in props
        assert "search_depth" in props

    async def test_execute_returns_results(self):
        provider = MockSearchProvider()
        tool = WebSearchTool(provider=provider)

        result = await tool.execute(query="AI policy Germany")
        assert result.success is True
        assert result.data["query"] == "AI policy Germany"
        assert len(result.data["results"]) == 2
        assert result.data["results"][0]["title"] == "Test Result 1"

    async def test_execute_respects_max_results(self):
        provider = MockSearchProvider()
        tool = WebSearchTool(provider=provider)

        result = await tool.execute(query="test", max_results=1)
        assert result.success is True
        assert len(result.data["results"]) == 1

    async def test_execute_includes_answer(self):
        provider = MockSearchProvider()
        tool = WebSearchTool(provider=provider)

        result = await tool.execute(query="test", include_answer=True)
        assert result.data["answer"] == "AI summary of results"

    async def test_execute_empty_query_fails(self):
        tool = WebSearchTool(provider=MockSearchProvider())
        result = await tool.execute(query="")
        assert result.success is False
        assert "required" in result.error

    async def test_execute_handles_provider_error(self):
        class FailingProvider(SearchProvider):
            async def search(self, **kwargs) -> SearchResponse:
                msg = "API timeout"
                raise TimeoutError(msg)

        tool = WebSearchTool(provider=FailingProvider())
        result = await tool.execute(query="test")
        assert result.success is False
        assert "Search failed" in result.error


# -- Agent Tests --


class TestSearchAgent:
    async def test_run_returns_results(self):
        provider = MockSearchProvider()
        agent = SearchAgent(provider=provider)

        result = await agent.run("latest AI policy in Germany")
        assert result.success is True
        assert "Test Result 1" in result.output
        assert result.metadata["result_count"] == 2

    async def test_run_includes_urls_in_output(self):
        provider = MockSearchProvider()
        agent = SearchAgent(provider=provider)

        result = await agent.run("python docs")
        assert "https://example.com/page1" in result.output
        assert "example.com" in result.output

    async def test_run_with_answer(self):
        provider = MockSearchProvider()
        agent = SearchAgent(provider=provider)

        result = await agent.run("what is AI", context={"include_answer": True})
        assert result.metadata["answer"] == "AI summary of results"

    async def test_run_handles_failure(self):
        class FailProvider(SearchProvider):
            async def search(self, **kwargs) -> SearchResponse:
                msg = "No connection"
                raise ConnectionError(msg)

        agent = SearchAgent(provider=FailProvider())
        result = await agent.run("test")
        assert result.success is False
        assert "failed" in result.output.lower()

    async def test_step_extracts_user_query(self):
        from terra.llm.types import ChatMessage

        provider = MockSearchProvider()
        agent = SearchAgent(provider=provider)

        messages = [
            ChatMessage(role="system", content="You are helpful."),
            ChatMessage(role="user", content="Find me info on climate change"),
        ]
        response = await agent.step(messages)
        assert response.role == "assistant"
        assert "Test Result" in response.content


# -- Registry Integration --


class TestRegistryIntegration:
    def test_tool_can_be_registered(self):
        from terra.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool = WebSearchTool(provider=MockSearchProvider())
        registry.register(tool)

        assert "web_search" in registry
        schemas = registry.get_openai_schemas()
        assert any(s["function"]["name"] == "web_search" for s in schemas)

    async def test_tool_callable_from_registry(self):
        from terra.tools.registry import ToolRegistry

        registry = ToolRegistry()
        registry.register(WebSearchTool(provider=MockSearchProvider()))

        result = await registry.execute("web_search", query="test")
        assert result.success is True
        assert len(result.data["results"]) > 0

    def test_agent_can_be_registered(self):
        from terra.agents.base import AgentConfig
        from terra.agents.registry import AgentRegistry

        registry = AgentRegistry()
        config = AgentConfig(
            name="web_search",
            description="Web search agent",
            tools=["web_search"],
        )
        registry.register(SearchAgent, config)
        assert "web_search" in registry


# -- Tavily Client (mocked) --


class TestTavilyProvider:
    @patch("tavily.AsyncTavilyClient")
    async def test_search_calls_tavily_client(self, mock_client_cls):
        mock_instance = AsyncMock()
        mock_instance.search = AsyncMock(
            return_value={
                "results": [
                    {
                        "title": "Tavily Result",
                        "url": "https://tavily.com/result",
                        "content": "Found by Tavily",
                        "score": 0.9,
                    }
                ],
                "answer": None,
            }
        )
        mock_client_cls.return_value = mock_instance

        provider = TavilySearchProvider(api_key="test-key")
        response = await provider.search(
            query="test query", max_results=3, search_depth="basic"
        )

        mock_instance.search.assert_called_once()
        call_kwargs = mock_instance.search.call_args[1]
        assert call_kwargs["query"] == "test query"
        assert call_kwargs["max_results"] == 3
        assert call_kwargs["search_depth"] == "basic"
        assert len(response.results) == 1
        assert response.results[0].title == "Tavily Result"
        assert response.results[0].domain == "tavily.com"
