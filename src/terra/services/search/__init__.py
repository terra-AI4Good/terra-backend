"""Web search service — provider-agnostic search abstraction."""

from terra.services.search.base import SearchProvider, SearchResult

__all__ = ["SearchProvider", "SearchResult"]
