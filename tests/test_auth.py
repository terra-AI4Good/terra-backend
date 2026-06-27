"""Tests for user authentication."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from terra.models.session import Session as SessionModel
from terra.services.auth import (
    create_session,
    create_user,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pw = "my-secure-password"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct-password")
        assert not verify_password("wrong-password", hashed)


class TestUserRegistration:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "password": "securepass1"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "token" in data
        assert "expires_at" in data
        assert len(data["token"]) == 64  # 32 bytes hex

    async def test_register_duplicate_username(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"username": "bob", "password": "password123"},
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "bob", "password": "otherpass99"},
        )
        assert response.status_code == 409
        assert "already taken" in response.json()["detail"]

    async def test_register_short_username_rejected(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "ab", "password": "password123"},
        )
        assert response.status_code == 422

    async def test_register_short_password_rejected(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "validuser", "password": "short"},
        )
        assert response.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={"username": "carol", "password": "goodpass99"},
        )

        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "carol", "password": "goodpass99"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert len(data["token"]) == 64

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"username": "dave", "password": "realpass88"},
        )

        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "dave", "password": "wrongpass"},
        )
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "ghost", "password": "whatever1"},
        )
        assert response.status_code == 401


class TestSession:
    async def test_get_current_user(self, client: AsyncClient):
        # Register and get token
        reg = await client.post(
            "/api/v1/auth/register",
            json={"username": "eve", "password": "evepass123"},
        )
        token = reg.json()["token"]

        # Get current user
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "eve"
        assert "id" in data
        assert "created_at" in data

    async def test_invalid_token_rejected(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert response.status_code == 401

    async def test_missing_auth_header_rejected(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_logout_invalidates_session(self, client: AsyncClient):
        # Register
        reg = await client.post(
            "/api/v1/auth/register",
            json={"username": "frank", "password": "frankpass1"},
        )
        token = reg.json()["token"]

        # Logout
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Token should no longer work
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    async def test_expired_session_rejected(
        self, client: AsyncClient, db: AsyncSession
    ):
        # Create user directly
        user = await create_user(db, "grace", "gracepass1")

        # Create an already-expired session
        session = SessionModel(
            token="expired-token-abc123def456abc123def456abc123de",
            user_id=user.id,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db.add(session)
        await db.commit()

        response = await client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": "Bearer expired-token-abc123def456abc123def456abc123de"
            },
        )
        assert response.status_code == 401


class TestSessionService:
    async def test_create_session_generates_token(self, db: AsyncSession):
        user = await create_user(db, "henry", "henrypass1")
        session = await create_session(db, user.id)

        assert len(session.token) == 64
        assert session.user_id == user.id
        # Normalize timezone for comparison (SQLite stores naive)
        expires = session.expires_at
        if expires.tzinfo is None:
            from datetime import UTC as _UTC

            expires = expires.replace(tzinfo=_UTC)
        assert expires > datetime.now(UTC)
