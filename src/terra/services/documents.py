"""Document service — CRUD and memory integration for uploaded documents."""

from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terra.memory.base import MemoryStore
from terra.models.document import Document

# Max chunk size for memory entries (characters).
# Documents are split into chunks so the chatbot retrieves relevant
# portions rather than flooding the context with full documents.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100


def _content_hash(content: str) -> str:
    """Compute a SHA-256 hash of the document content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks for memory storage."""
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


async def create_document(
    db: AsyncSession,
    memory: MemoryStore,
    user_id: int,
    title: str,
    content: str,
) -> Document:
    """Upload a new document: persist to DB and index into memory.

    Args:
        db: Database session.
        memory: Memory store for retrieval integration.
        user_id: Owner.
        title: Document title/filename.
        content: Plain-text content.

    Returns:
        The created Document.
    """
    doc = Document(
        user_id=user_id,
        title=title,
        content=content,
        content_hash=_content_hash(content),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Index chunks into memory for chatbot retrieval
    chunks = _chunk_text(content)
    for i, chunk in enumerate(chunks):
        await memory.add(
            user_id=user_id,
            role="user",
            content=f"[Document: {title}] {chunk}",
            metadata={"source": "document", "document_id": doc.id, "chunk": i},
        )

    return doc


async def list_documents(
    db: AsyncSession,
    user_id: int,
) -> list[Document]:
    """List all documents belonging to a user (without full content)."""
    stmt = (
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_document(
    db: AsyncSession,
    user_id: int,
    document_id: int,
) -> Document | None:
    """Fetch a specific document, scoped to the user."""
    stmt = select(Document).where(
        Document.id == document_id,
        Document.user_id == user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_document(
    db: AsyncSession,
    user_id: int,
    document_id: int,
) -> bool:
    """Delete a document. Returns True if deleted, False if not found."""
    doc = await get_document(db, user_id, document_id)
    if doc is None:
        return False
    await db.delete(doc)
    await db.commit()
    return True
