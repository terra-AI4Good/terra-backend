"""Types for LLM interactions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: str | None = None
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class ToolCall(BaseModel):
    """A tool call requested by the model."""

    id: str
    type: Literal["function"] = "function"
    function: FunctionCall


class FunctionCall(BaseModel):
    """Function invocation details within a tool call."""

    name: str
    arguments: str  # JSON string


class TokenUsage(BaseModel):
    """Token usage from an LLM response."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    """Structured response from an LLM call."""

    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: TokenUsage = Field(default_factory=TokenUsage)
    model: str = ""
    finish_reason: str | None = None

    @classmethod
    def from_litellm_response(cls, response: Any) -> LLMResponse:
        """Parse a LiteLLM ModelResponse into our internal type."""
        choice = response.choices[0]
        message = choice.message

        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    type=tc.type,
                    function=FunctionCall(
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    ),
                )
                for tc in message.tool_calls
            ]

        usage = TokenUsage()
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        return cls(
            content=message.content,
            tool_calls=tool_calls,
            usage=usage,
            model=response.model or "",
            finish_reason=choice.finish_reason,
        )
