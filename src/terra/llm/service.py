"""LLM service — thin wrapper around LiteLLM for centralized model calls."""

from __future__ import annotations

from typing import Any

import litellm

from terra.llm.config import LLMSettings, ModelConfig
from terra.llm.types import ChatMessage, LLMResponse


class LLMService:
    """Centralized LLM interface.

    Wraps LiteLLM so the rest of the codebase never calls litellm directly.
    This gives us a single place to add caching, retries, tracing, cost
    tracking, and provider fallback logic.
    """

    def __init__(self, settings: LLMSettings | None = None) -> None:
        self._settings = settings or LLMSettings()
        self._configure_litellm()

    def _configure_litellm(self) -> None:
        """Apply global LiteLLM settings."""
        # Suppress litellm's verbose logging by default
        litellm.suppress_debug_info = True

        # Set API keys if provided
        if self._settings.openai_api_key:
            litellm.openai_key = self._settings.openai_api_key
        if self._settings.anthropic_api_key:
            litellm.anthropic_key = self._settings.anthropic_api_key

    async def completion(
        self,
        messages: list[ChatMessage],
        config: ModelConfig | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Make an async LLM completion call.

        Args:
            messages: Conversation history in OpenAI message format.
            config: Model configuration overrides.
            tools: Tool definitions in OpenAI function-calling format.
            tool_choice: Tool selection strategy.
            **kwargs: Additional LiteLLM parameters.

        Returns:
            Structured LLM response.
        """
        cfg = config or self._default_config()

        params: dict[str, Any] = {
            "model": cfg.model,
            "messages": [m.model_dump() for m in messages],
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "timeout": cfg.timeout,
            "top_p": cfg.top_p,
            "stream": cfg.stream,
            **kwargs,
        }

        if tools:
            params["tools"] = tools
        if tool_choice is not None:
            params["tool_choice"] = tool_choice

        response = await litellm.acompletion(**params)
        return LLMResponse.from_litellm_response(response)

    def _default_config(self) -> ModelConfig:
        """Build default config from settings."""
        return ModelConfig(
            model=self._settings.default_model,
            temperature=self._settings.default_temperature,
            max_tokens=self._settings.default_max_tokens,
            timeout=self._settings.default_timeout,
        )

    @property
    def settings(self) -> LLMSettings:
        """Access current settings (read-only)."""
        return self._settings
