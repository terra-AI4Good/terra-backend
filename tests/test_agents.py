"""Tests for the agent system."""

from typing import Any

import pytest

from terra.agents.base import Agent, AgentConfig, AgentResult
from terra.agents.registry import AgentRegistry
from terra.llm.types import ChatMessage


class StubAgent(Agent):
    """Minimal agent implementation for testing."""

    async def run(
        self,
        input_message: str,
        context: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> AgentResult:
        return AgentResult(
            success=True,
            output=f"Stub response to: {input_message}",
            iterations=1,
        )

    async def step(self, messages: list[ChatMessage]) -> ChatMessage:  # noqa: ARG002
        return ChatMessage(role="assistant", content="stub step")


class TestAgentRegistry:
    def test_register_and_lookup(self):
        registry = AgentRegistry()
        config = AgentConfig(name="test-agent", description="A test agent")
        registry.register(StubAgent, config)

        assert "test-agent" in registry
        assert registry.get_class("test-agent") is StubAgent
        assert registry.get_config("test-agent") == config

    def test_register_duplicate_raises(self):
        registry = AgentRegistry()
        config = AgentConfig(name="test-agent")
        registry.register(StubAgent, config)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(StubAgent, config)

    def test_unregister(self):
        registry = AgentRegistry()
        config = AgentConfig(name="test-agent")
        registry.register(StubAgent, config)
        registry.unregister("test-agent")

        assert "test-agent" not in registry
        assert len(registry) == 0

    def test_create_agent(self):
        registry = AgentRegistry()
        config = AgentConfig(
            name="test-agent",
            description="Test",
            tools=["web_search"],
        )
        registry.register(StubAgent, config)

        agent = registry.create("test-agent")
        assert isinstance(agent, StubAgent)
        assert agent.name == "test-agent"

    def test_create_unknown_raises(self):
        registry = AgentRegistry()

        with pytest.raises(KeyError, match="not found"):
            registry.create("nonexistent")

    def test_list_names(self):
        registry = AgentRegistry()
        registry.register(StubAgent, AgentConfig(name="agent-a", description="A"))
        registry.register(StubAgent, AgentConfig(name="agent-b", description="B"))

        names = registry.list_names()
        assert "agent-a" in names
        assert "agent-b" in names


class TestAgentExecution:
    async def test_stub_agent_run(self):
        config = AgentConfig(name="stub", description="Stub agent")
        agent = StubAgent(config)

        result = await agent.run("Hello")
        assert result.success is True
        assert "Hello" in result.output

    async def test_stub_agent_step(self):
        config = AgentConfig(name="stub")
        agent = StubAgent(config)

        msg = await agent.step([ChatMessage(role="user", content="Hi")])
        assert msg.role == "assistant"
