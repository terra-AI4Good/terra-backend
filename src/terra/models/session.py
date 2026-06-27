"""Session model for session-based authentication."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from terra.db.base import Base


class Session(Base):
    """User authentication session."""

    __tablename__ = "sessions"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, init=False, repr=True)

    # Session token — what the client presents to authenticate
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Owner
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Expiration
    expires_at: Mapped[datetime] = mapped_column()

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        init=False,
        server_default=func.now(),
    )
