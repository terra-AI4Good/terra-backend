"""Static Knowledge Base service — search and retrieve Integreat pages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from terra.config import get_settings


class StaticKBService:
    """Service for querying the static knowledge base (Integreat pages).

    Loads the processed pages JSON into memory and provides keyword-based
    search with category filtering. Designed to be fast and simple —
    can be upgraded to FTS/vector search later.
    """

    _instance: StaticKBService | None = None
    _pages: list[dict[str, Any]] | None = None

    def __init__(self, data_path: str | None = None) -> None:
        self._data_path = data_path

    @classmethod
    def get_default(cls) -> StaticKBService:
        """Return a singleton instance using default settings."""
        if cls._instance is None:
            settings = get_settings()
            cls._instance = cls(data_path=settings.static_kb_processed_path)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None
        cls._pages = None

    def _load_pages(self) -> list[dict[str, Any]]:
        """Load pages from the processed JSON file."""
        if StaticKBService._pages is not None:
            return StaticKBService._pages

        path = Path(self._data_path or "data/static_kb/processed/pages.json")
        if not path.exists():
            return []

        data: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        StaticKBService._pages = data
        return data

    def search(
        self,
        query: str,
        limit: int = 5,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search pages by keyword matching on title and content.

        Args:
            query: Search terms (space-separated, case-insensitive).
            limit: Max results to return.
            category: Optional category filter.

        Returns:
            List of matching page dicts, ranked by relevance.
        """
        pages = self._load_pages()
        if not pages:
            return []

        terms = query.lower().split()
        if not terms:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []
        for page in pages:
            # Category filter
            if category and page.get("category", "") != category:
                continue

            score = self._score_page(page, terms)
            if score > 0:
                scored.append((score, page))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [page for _, page in scored[:limit]]

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        """Fetch a single page by ID."""
        pages = self._load_pages()
        for page in pages:
            if page.get("id") == item_id:
                return page
        return None

    def list_categories(self) -> list[str]:
        """Return all unique categories."""
        pages = self._load_pages()
        return sorted({p.get("category", "") for p in pages if p.get("category")})

    def _score_page(self, page: dict[str, Any], terms: list[str]) -> float:
        """Score a page against search terms."""
        title = page.get("title", "").lower()
        content = page.get("content_text", "").lower()

        score = 0.0
        for term in terms:
            # Title match is worth more
            if term in title:
                score += 10.0
            # Content match
            if term in content:
                score += 1.0
                # Bonus for multiple occurrences
                count = content.count(term)
                if count > 1:
                    score += min(count * 0.5, 5.0)

        # Bonus for pages with actual content
        if page.get("content_text") and score > 0:
            score += 0.5

        return score
