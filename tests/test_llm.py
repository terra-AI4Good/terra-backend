"""Tests for the LLM service layer."""

from terra.llm.config import LLMSettings, ModelConfig
from terra.llm.service import LLMService
from terra.llm.types import ChatMessage, FunctionCall, LLMResponse, TokenUsage, ToolCall


class TestLLMConfig:
    def test_default_model_config(self):
        config = ModelConfig()
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.stream is False

    def test_custom_model_config(self):
        config = ModelConfig(
            model="anthropic/claude-3-sonnet",
            temperature=0.3,
            max_tokens=2048,
        )
        assert config.model == "anthropic/claude-3-sonnet"
        assert config.temperature == 0.3

    def test_llm_settings_defaults(self):
        settings = LLMSettings()
        assert settings.default_model == "gpt-4o-mini"
        assert settings.openai_api_key is None


class TestLLMService:
    def test_initialization(self):
        settings = LLMSettings(
            default_model="gpt-4o",
            default_temperature=0.5,
        )
        service = LLMService(settings=settings)
        assert service.settings.default_model == "gpt-4o"
        assert service.settings.default_temperature == 0.5

    def test_default_initialization(self):
        service = LLMService()
        assert service.settings.default_model == "gpt-4o-mini"


class TestLLMTypes:
    def test_chat_message(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_tool_call(self):
        tc = ToolCall(
            id="call_123",
            function=FunctionCall(name="web_search", arguments='{"query": "test"}'),
        )
        assert tc.function.name == "web_search"
        assert tc.type == "function"

    def test_llm_response(self):
        response = LLMResponse(
            content="Hello!",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            model="gpt-4o-mini",
            finish_reason="stop",
        )
        assert response.content == "Hello!"
        assert response.usage.total_tokens == 15
