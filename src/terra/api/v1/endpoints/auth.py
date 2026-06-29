"""Authentication endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from terra.api.deps import get_db
from terra.services.auth import (
    authenticate_user,
    create_session,
    create_user,
    get_session,
    get_user_by_id,
    invalidate_session,
)

router = APIRouter()


# -- Schemas --


class RegisterRequest(BaseModel):
    """Registration request."""

    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Login request."""

    username: str
    password: str


class AuthResponse(BaseModel):
    """Response containing the session token."""

    token: str
    expires_at: str


class UserResponse(BaseModel):
    """Public user information."""

    id: int
    username: str
    created_at: str


# -- Endpoints --


@router.post(
    "/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Register a new user and return a session token."""
    try:
        user = await create_user(db, body.username, body.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e

    session = await create_session(db, user.id)
    return AuthResponse(
        token=session.token,
        expires_at=session.expires_at.isoformat(),
    )


@router.post("/auth/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate and return a session token."""
    user = await authenticate_user(db, body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    session = await create_session(db, user.id)
    return AuthResponse(
        token=session.token,
        expires_at=session.expires_at.isoformat(),
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Invalidate the current session."""
    token = _extract_token(authorization)
    if token:
        await invalidate_session(db, token)


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get the currently authenticated user."""
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

    return UserResponse(
        id=user.id,
        username=user.username,
        created_at=user.created_at.isoformat(),
    )


def _extract_token(authorization: str | None) -> str | None:
    """Extract a Bearer token from the Authorization header."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    # Allow raw token as well (simple mode)
    return authorization
