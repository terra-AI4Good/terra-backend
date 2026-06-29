"""Base search provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A single search result."""

    title: str
    url: str
    snippet: str = ""
    domain: str = ""
    score: float = 0.0
    raw_content: str | None = None


class SearchResponse(BaseModel):
    """Full search response from a provider."""

    query: str
    results: list[SearchResult] = Field(default_factory=list)
    answer: str | None = None


class SearchProvider(ABC):
    """Abstract interface for web search providers.

    Swap implementations (Tavily, Serper, Brave, etc.) without
    changing the tool or agent code.
    """

    @abstractmethod
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
        """Execute a web search.

        Args:
            query: The search query.
            max_results: Maximum number of results.
            search_depth: 'basic' or 'advanced'.
            include_answer: Whether to include an AI-generated answer.
            include_raw_content: Whether to include full page content.
            include_domains: Only search these domains.
            exclude_domains: Exclude these domains.

        Returns:
            SearchResponse with results and optional answer.
        """
