"""Memory store abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """A single memory entry (one conversational turn)."""

    role: Literal["user", "assistant"] = "user"
    content: str
    timestamp: datetime
    metadata: dict[str, object] = Field(default_factory=dict)


class MemoryStore(ABC):
    """Abstract memory store interface.

    Implementations can use SQLite, a vector DB, mem0, or anything else.
    The chatbot service only interacts with this interface.
    """

    @abstractmethod
    async def add(
        self,
        user_id: int,
        role: Literal["user", "assistant"],
        content: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Store a new memory entry for a user."""

    @abstractmethod
    async def retrieve(
        self,
        user_id: int,
        query: str | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Retrieve relevant memory entries for a user.

        Args:
            user_id: The user whose memory to retrieve.
            query: Optional query for relevance-based retrieval.
                   If None, returns recent entries.
            limit: Maximum number of entries to return.

        Returns:
            List of memory entries, ordered by relevance or recency.
        """

    @abstractmethod
    async def clear(self, user_id: int) -> None:
        """Clear all memory for a user."""

    @abstractmethod
    async def count(self, user_id: int) -> int:
        """Return the number of stored entries for a user."""
