"""Shared dependencies for dependency injection."""

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from terra.db.session import async_session_factory
from terra.models.user import User
from terra.services.auth import get_session, get_user_by_id


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for request scope."""
    async with async_session_factory() as session:
        yield session


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that resolves the authenticated user from the session token.

    Raises 401 if no valid session is found.
    """
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    session = await get_session(db, token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user = await get_user_by_id(db, session.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def _extract_token(authorization: str | None) -> str | None:
    """Extract a Bearer token from the Authorization header."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return authorization
