"""User model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from terra.db.base import Base


class User(Base):
    """Application user."""

    __tablename__ = "users"

    # Primary key — must be first (no default in dataclass sense,
    # but init=False so SQLAlchemy handles it)
    id: Mapped[int] = mapped_column(primary_key=True, init=False, repr=True)

    # Required fields
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    # Timestamps (auto-populated)
    created_at: Mapped[datetime] = mapped_column(
        init=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
