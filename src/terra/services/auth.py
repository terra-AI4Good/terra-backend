"""Authentication service — user registration, login, sessions."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terra.models.session import Session
from terra.models.user import User

# Session lifetime
SESSION_DURATION = timedelta(hours=24)
SESSION_TOKEN_BYTES = 32  # 32 bytes → 64 hex chars


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_session_token() -> str:
    """Generate a cryptographically secure session token."""
    return secrets.token_hex(SESSION_TOKEN_BYTES)


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> User:
    """Register a new user.

    Args:
        db: Database session.
        username: Desired username.
        password: Plain-text password (will be hashed).

    Returns:
        The created User.

    Raises:
        ValueError: If the username is already taken.
    """
    # Check for existing user
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none() is not None:
        msg = f"Username '{username}' is already taken"
        raise ValueError(msg)

    user = User(
        username=username,
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> User | None:
    """Validate credentials and return the user if correct.

    Returns None if username doesn't exist or password is wrong.
    """
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def create_session(
    db: AsyncSession,
    user_id: int,
) -> Session:
    """Create a new session for the given user."""
    token = generate_session_token()
    expires_at = datetime.now(UTC) + SESSION_DURATION

    session = Session(
        token=token,
        user_id=user_id,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(
    db: AsyncSession,
    token: str,
) -> Session | None:
    """Look up a session by token. Returns None if not found or expired."""
    result = await db.execute(select(Session).where(Session.token == token))
    session = result.scalar_one_or_none()
    if session is None:
        return None

    # Compare as UTC — SQLite stores naive datetimes, so normalize
    expires = session.expires_at
    now = datetime.now(UTC)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < now:
        # Expired — clean it up
        await db.delete(session)
        await db.commit()
        return None
    return session


async def invalidate_session(
    db: AsyncSession,
    token: str,
) -> bool:
    """Delete a session (logout). Returns True if a session was removed."""
    result = await db.execute(select(Session).where(Session.token == token))
    session = result.scalar_one_or_none()
    if session is None:
        return False
    await db.delete(session)
    await db.commit()
    return True


async def get_user_by_id(
    db: AsyncSession,
    user_id: int,
) -> User | None:
    """Fetch a user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
