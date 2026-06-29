"""Agent execution runner — manages the tool-call loop."""

from __future__ import annotations

import json
from typing import Any

from terra.agents.base import Agent, AgentResult
from terra.llm.types import ChatMessage
from terra.orchestration.hooks import ExecutionHook, NullHook
from terra.tools.registry import ToolRegistry


class AgentRunner:
    """Runs an agent through its reasoning loop.

    Handles the tool-call cycle: LLM generates tool calls → runner executes
    them → results fed back → repeat until done or max_iterations reached.
    """

    def __init__(
        self,
        agent: Agent,
        tool_registry: ToolRegistry,
        hook: ExecutionHook | None = None,
    ) -> None:
        self._agent = agent
        self._tools = tool_registry
        self._hook = hook or NullHook()

    async def run(
        self,
        input_message: str,
        context: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> AgentResult:
        """Execute the full agent loop.

        Args:
            input_message: User's request.
            context: Optional context dict.

        Returns:
            AgentResult with output and execution metadata.
        """
        messages: list[ChatMessage] = []

        # System prompt
        if self._agent.config.system_prompt:
            messages.append(
                ChatMessage(role="system", content=self._agent.config.system_prompt)
            )

        # User input
        messages.append(ChatMessage(role="user", content=input_message))

        await self._hook.on_start(self._agent.name, input_message)

        iterations = 0
        tool_calls_made = 0

        while iterations < self._agent.config.max_iterations:
            iterations += 1

            # Get next response from the agent
            response = await self._agent.step(messages)
            messages.append(response)

            await self._hook.on_step(self._agent.name, iterations, response)

            # If no tool calls, we're done
            if not response.tool_calls:
                break

            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_calls_made += 1
                await self._hook.on_tool_call(
                    self._agent.name, tool_call.function.name, tool_call.id
                )

                try:
                    kwargs = json.loads(tool_call.function.arguments)
                    tool_result = await self._tools.execute(
                        tool_call.function.name, **kwargs
                    )
                    tool_response = tool_result.model_dump_json()
                except (KeyError, json.JSONDecodeError) as e:
                    tool_response = json.dumps({"error": str(e)})

                messages.append(
                    ChatMessage(
                        role="tool",
                        content=tool_response,
                        tool_call_id=tool_call.id,
                    )
                )

                await self._hook.on_tool_result(
                    self._agent.name, tool_call.function.name, tool_response
                )

        # Extract final output
        final_content = ""
        if messages and messages[-1].role == "assistant":
            final_content = messages[-1].content or ""

        result = AgentResult(
            success=True,
            output=final_content,
            messages=messages,
            tool_calls_made=tool_calls_made,
            iterations=iterations,
        )

        await self._hook.on_complete(self._agent.name, result)
        return result
