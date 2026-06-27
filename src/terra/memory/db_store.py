"""SQLite-backed memory store using the existing database."""

from __future__ import annotations

from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from terra.memory.base import MemoryEntry, MemoryStore
from terra.models.memory import ChatMemory


class DatabaseMemoryStore(MemoryStore):
    """Memory store backed by the application database.

    Stores conversation turns as rows. Retrieval is recency-based
    (most recent N entries). This can be swapped for a vector-based
    store later without changing the interface.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(
        self,
        user_id: int,
        role: Literal["user", "assistant"],
        content: str,
        metadata: dict[str, object] | None = None,  # noqa: ARG002
    ) -> None:
        """Store a conversation turn."""
        entry = ChatMemory(
            user_id=user_id,
            role=role,
            content=content,
        )
        self._db.add(entry)
        await self._db.commit()

    async def retrieve(
        self,
        user_id: int,
        query: str | None = None,  # noqa: ARG002
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Retrieve recent conversation entries for the user.

        Currently uses recency-based retrieval (most recent N turns).
        A future implementation could add semantic search with embeddings.
        """
        stmt = (
            select(ChatMemory)
            .where(ChatMemory.user_id == user_id)
            .order_by(ChatMemory.id.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        rows = result.scalars().all()

        # Reverse so they're in chronological order
        return [
            MemoryEntry(
                role=row.role,
                content=row.content,
                timestamp=row.created_at,
            )
            for row in reversed(rows)
        ]

    async def clear(self, user_id: int) -> None:
        """Delete all memory for a user."""
        stmt = select(ChatMemory).where(ChatMemory.user_id == user_id)
        result = await self._db.execute(stmt)
        for row in result.scalars().all():
            await self._db.delete(row)
        await self._db.commit()

    async def count(self, user_id: int) -> int:
        """Count stored entries for a user."""
        stmt = (
            select(func.count())
            .select_from(ChatMemory)
            .where(ChatMemory.user_id == user_id)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one()
