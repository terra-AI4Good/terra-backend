"""Tests for the agent API endpoints."""

from httpx import AsyncClient


async def test_agents_health(client: AsyncClient):
    response = await client.get("/api/v1/agents/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["subsystem"] == "agents"


async def test_list_agents_returns_registered(client: AsyncClient):
    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    agents = response.json()
    assert len(agents) >= 3
    names = {a["name"] for a in agents}
    assert "web_search" in names
    assert "job_listings" in names
    assert "static_knowledge_base" in names


async def test_list_tools_returns_registered(client: AsyncClient):
    response = await client.get("/api/v1/tools")
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) >= 6
    names = {t["name"] for t in tools}
    assert "web_search" in names
    assert "search_ba_jobs" in names
    assert "search_static_kb" in names
    assert "get_static_kb_item" in names


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
