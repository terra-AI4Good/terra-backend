"""Smoke test for the health endpoint."""

from httpx import AsyncClient


async def test_health_returns_healthy(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
