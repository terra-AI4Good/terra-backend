"""Chat memory model — stores conversation turns per user."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from terra.db.base import Base


class ChatMemory(Base):
    """A single conversation turn stored for memory retrieval."""

    __tablename__ = "chat_memory"

    id: Mapped[int] = mapped_column(primary_key=True, init=False, repr=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        init=False,
        server_default=func.now(),
        index=True,
    )
