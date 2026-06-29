"""Schemas for web search API requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """API request for a web search."""

    query: str = Field(min_length=1, max_length=1000)
    max_results: int = Field(default=5, ge=1, le=20)


class SearchResultItem(BaseModel):
    """A single search result for API output."""

    title: str
    url: str
    snippet: str
    domain: str
    score: float = 0.0


class SearchApiResponse(BaseModel):
    """API response for a web search."""

    query: str
    results: list[SearchResultItem] = Field(default_factory=list)
    answer: str | None = None
