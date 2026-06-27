"""Agent subsystem API endpoints (placeholder)."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class AgentRunRequest(BaseModel):
    """Request to execute an agent."""

    agent_name: str
    input_message: str
    context: dict[str, Any] = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    """Response from an agent execution."""

    success: bool
    output: str
    tool_calls_made: int = 0
    iterations: int = 0
    error: str | None = None


class AgentInfo(BaseModel):
    """Summary info for a registered agent."""

    name: str
    description: str
    tools: list[str]


class ToolInfo(BaseModel):
    """Summary info for a registered tool."""

    name: str
    description: str


@router.get("/agents/health")
async def agents_health() -> dict[str, str]:
    """Health check for the agent subsystem."""
    return {"status": "healthy", "subsystem": "agents"}


@router.get("/agents", response_model=list[AgentInfo])
async def list_agents() -> list[AgentInfo]:
    """List all registered agents."""
    from terra.agents.registry import agent_registry

    return [
        AgentInfo(
            name=config.name,
            description=config.description,
            tools=config.tools,
        )
        for config in agent_registry.list_configs()
    ]


@router.get("/tools", response_model=list[ToolInfo])
async def list_tools() -> list[ToolInfo]:
    """List all registered tools."""
    from terra.tools.registry import tool_registry

    return [
        ToolInfo(
            name=tool.definition.name,
            description=tool.definition.description,
        )
        for tool in tool_registry.list_tools()
    ]


@router.post("/agents/run", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    """Execute a registered agent."""
    from terra.agents.registry import agent_registry

    if request.agent_name not in agent_registry:
        return AgentRunResponse(
            success=False,
            output="",
            error=f"Agent '{request.agent_name}' not found",
        )

    agent = agent_registry.create(request.agent_name)
    result = await agent.run(
        input_message=request.input_message,
        context=request.context or None,
    )

    return AgentRunResponse(
        success=result.success,
        output=result.output,
        tool_calls_made=result.tool_calls_made,
        iterations=result.iterations,
        error=result.error,
    )
