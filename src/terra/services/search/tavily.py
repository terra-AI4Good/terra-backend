"""Tavily search provider implementation."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from terra.services.search.base import SearchProvider, SearchResponse, SearchResult


class TavilySearchProvider(SearchProvider):
    """Web search powered by the Tavily API.

    Requires a TAVILY_API_KEY to be configured.
    """

    def __init__(
        self,
        api_key: str,
        timeout: float = 20.0,
    ) -> None:
        if not api_key:
            msg = "TAVILY_API_KEY is required for the Tavily search provider"
            raise ValueError(msg)
        self._api_key = api_key
        self._timeout = timeout

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
        """Execute a search via the Tavily API."""
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=self._api_key)

        kwargs: dict[str, Any] = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains

        response = await client.search(**kwargs)
        return self._parse_response(query, response)

    def _parse_response(self, query: str, raw: dict[str, Any]) -> SearchResponse:
        """Parse raw Tavily API response into our schema."""
        results: list[SearchResult] = []
        for item in raw.get("results", []):
            url = item.get("url", "")
            domain = urlparse(url).netloc if url else ""
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("content", ""),
                    domain=domain,
                    score=item.get("score", 0.0),
                    raw_content=item.get("raw_content"),
                )
            )

        return SearchResponse(
            query=query,
            results=results,
            answer=raw.get("answer"),
        )
