"""Execution hooks for tracing, logging, and evaluation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from terra.agents.base import AgentResult
    from terra.llm.types import ChatMessage


class ExecutionHook(ABC):
    """Base class for execution lifecycle hooks.

    Implement this to add tracing, logging, cost tracking, or evaluation
    instrumentation to agent runs.
    """

    @abstractmethod
    async def on_start(self, agent_name: str, input_message: str) -> None:
        """Called when an agent run begins."""

    @abstractmethod
    async def on_step(
        self, agent_name: str, iteration: int, message: ChatMessage
    ) -> None:
        """Called after each LLM step."""

    @abstractmethod
    async def on_tool_call(self, agent_name: str, tool_name: str, call_id: str) -> None:
        """Called before a tool is executed."""

    @abstractmethod
    async def on_tool_result(
        self, agent_name: str, tool_name: str, result: str
    ) -> None:
        """Called after a tool returns."""

    @abstractmethod
    async def on_complete(self, agent_name: str, result: AgentResult) -> None:
        """Called when the agent run finishes."""


class NullHook(ExecutionHook):
    """No-op hook — used when no instrumentation is configured."""

    async def on_start(self, agent_name: str, input_message: str) -> None:
        pass

    async def on_step(
        self, agent_name: str, iteration: int, message: ChatMessage
    ) -> None:
        pass

    async def on_tool_call(self, agent_name: str, tool_name: str, call_id: str) -> None:
        pass

    async def on_tool_result(
        self, agent_name: str, tool_name: str, result: str
    ) -> None:
        pass

    async def on_complete(self, agent_name: str, result: AgentResult) -> None:
        pass


class LoggingHook(ExecutionHook):
    """Simple logging hook — prints execution events to stdout.

    Useful for development. Replace with structured logging in production.
    """

    async def on_start(self, agent_name: str, input_message: str) -> None:
        self._log(f"[{agent_name}] Starting: {input_message[:100]}")

    async def on_step(
        self, agent_name: str, iteration: int, message: ChatMessage
    ) -> None:
        has_tools = bool(message.tool_calls)
        self._log(
            f"[{agent_name}] Step {iteration} — "
            f"tool_calls={has_tools}, content_len={len(message.content or '')}"
        )

    async def on_tool_call(self, agent_name: str, tool_name: str, call_id: str) -> None:
        self._log(f"[{agent_name}] Calling tool: {tool_name} ({call_id})")

    async def on_tool_result(
        self, agent_name: str, tool_name: str, result: str
    ) -> None:
        self._log(f"[{agent_name}] Tool result from {tool_name}: {len(result)} chars")

    async def on_complete(self, agent_name: str, result: AgentResult) -> None:
        self._log(
            f"[{agent_name}] Complete — "
            f"iterations={result.iterations}, tools_used={result.tool_calls_made}"
        )

    def _log(self, msg: str) -> None:
        # TODO: Replace with structlog or standard logging
        import sys

        sys.stdout.write(f"{msg}\n")
        sys.stdout.flush()
