"""Base agent interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from terra.llm.config import ModelConfig
from terra.llm.types import ChatMessage


class AgentConfig(BaseModel):
    """Configuration for an agent instance."""

    name: str
    description: str = ""
    system_prompt: str = ""
    model_config_override: ModelConfig | None = Field(
        default=None, alias="model_config"
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Names of tools this agent has access to.",
    )
    max_iterations: int = Field(
        default=10,
        description="Maximum tool-call loops before stopping.",
    )


class AgentResult(BaseModel):
    """Result from an agent execution."""

    success: bool = True
    output: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)
    tool_calls_made: int = 0
    iterations: int = 0
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Agent(ABC):
    """Abstract base class for agents.

    An agent combines an LLM with tools and a system prompt to accomplish
    a task through iterative reasoning and tool use.
    """

    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    @property
    def name(self) -> str:
        """Agent's registered name."""
        return self._config.name

    @property
    def config(self) -> AgentConfig:
        """Agent configuration."""
        return self._config

    @abstractmethod
    async def run(
        self,
        input_message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute the agent with the given input.

        Args:
            input_message: The user's request or task description.
            context: Optional additional context (conversation history, etc.).

        Returns:
            AgentResult with the final output and execution metadata.
        """

    @abstractmethod
    async def step(
        self,
        messages: list[ChatMessage],
    ) -> ChatMessage:
        """Execute a single reasoning step.

        Used internally by `run` and exposed for fine-grained control.

        Args:
            messages: Current conversation state.

        Returns:
            The assistant's next message (may contain tool calls).
        """
