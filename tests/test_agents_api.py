"""Tests for the agent API endpoints."""

from httpx import AsyncClient


async def test_agents_health(client: AsyncClient):
    response = await client.get("/api/v1/agents/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["subsystem"] == "agents"


async def test_list_agents_empty(client: AsyncClient):
    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_tools_empty(client: AsyncClient):
    response = await client.get("/api/v1/tools")
    assert response.status_code == 200
    assert response.json() == []


async def test_run_agent_not_found(client: AsyncClient):
    response = await client.post(
        "/api/v1/agents/run",
        json={
            "agent_name": "nonexistent",
            "input_message": "hello",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["error"]
