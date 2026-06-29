"""Tests for the chatbot endpoint and memory integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from terra.llm.types import LLMResponse, TokenUsage
from terra.memory.db_store import DatabaseMemoryStore

# -- Helpers --


async def _register_and_get_token(client: AsyncClient) -> str:
    """Register a user and return the auth token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"username": "chatuser", "password": "chatpass123"},
    )
    return resp.json()["token"]


def _mock_llm_response(content: str = "Hello! How can I help?") -> LLMResponse:
    """Create a mock LLM response."""
    return LLMResponse(
        content=content,
        tool_calls=[],
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        model="gpt-4o-mini",
        finish_reason="stop",
    )


# -- Tests --


class TestChatbotAuth:
    async def test_unauthenticated_request_rejected(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/chat",
            json={"message": "hello"},
        )
        assert response.status_code == 401

    async def test_invalid_token_rejected(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/chat",
            json={"message": "hello"},
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


class TestChatbotEndpoint:
    @patch("terra.services.chatbot.LLMService.completion", new_callable=AsyncMock)
    async def test_send_message_and_get_response(
        self, mock_completion, client: AsyncClient
    ):
        mock_completion.return_value = _mock_llm_response("I'm doing well!")
        token = await _register_and_get_token(client)

        response = await client.post(
            "/api/v1/chat",
            json={"message": "How are you?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "I'm doing well!"
        assert data["used_tools"] == []

    @patch("terra.services.chatbot.LLMService.completion", new_callable=AsyncMock)
    async def test_no_history_required_in_payload(
        self, mock_completion, client: AsyncClient
    ):
        """Client sends only the message — no conversation history."""
        mock_completion.return_value = _mock_llm_response("Sure thing!")
        token = await _register_and_get_token(client)

        # Just a message, nothing else
        response = await client.post(
            "/api/v1/chat",
            json={"message": "Do something"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["response"] == "Sure thing!"

    @patch("terra.services.chatbot.LLMService.completion", new_callable=AsyncMock)
    async def test_empty_message_rejected(self, mock_completion, client: AsyncClient):
        token = await _register_and_get_token(client)
        response = await client.post(
            "/api/v1/chat",
            json={"message": ""},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    @patch("terra.services.chatbot.LLMService.completion", new_callable=AsyncMock)
    async def test_memory_context_hidden_in_non_debug(
        self, mock_completion, client: AsyncClient
    ):
        mock_completion.return_value = _mock_llm_response("Answer")
        token = await _register_and_get_token(client)

        response = await client.post(
            "/api/v1/chat",
            json={"message": "question"},
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()
        assert data["memory_context"] is None


class TestMemoryIntegration:
    @patch("terra.services.chatbot.LLMService.completion", new_callable=AsyncMock)
    async def test_memory_written_after_chat(
        self, mock_completion, client: AsyncClient, db: AsyncSession
    ):
        """After a chat call, both user and assistant messages are stored."""
        mock_completion.return_value = _mock_llm_response("Stored response")
        token = await _register_and_get_token(client)

        await client.post(
            "/api/v1/chat",
            json={"message": "Remember this"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check memory was written
        memory = DatabaseMemoryStore(db)
        entries = await memory.retrieve(user_id=1, limit=10)
        assert len(entries) == 2
        assert entries[0].role == "user"
        assert entries[0].content == "Remember this"
        assert entries[1].role == "assistant"
        assert entries[1].content == "Stored response"

    @patch("terra.services.chatbot.LLMService.completion", new_callable=AsyncMock)
    async def test_memory_retrieved_on_next_call(
        self, mock_completion, client: AsyncClient, db: AsyncSession
    ):
        """On the second call, previous memory is retrieved and passed to LLM."""
        mock_completion.return_value = _mock_llm_response("First answer")
        token = await _register_and_get_token(client)

        # First message
        await client.post(
            "/api/v1/chat",
            json={"message": "First question"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Second message — LLM should receive memory context
        mock_completion.return_value = _mock_llm_response("Second answer")
        await client.post(
            "/api/v1/chat",
            json={"message": "Second question"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify the LLM was called with memory context
        # Second call should have system + memory(2 entries) + user = 4 messages
        last_call_messages = (
            mock_completion.call_args_list[-1][1].get("messages")
            or mock_completion.call_args_list[-1][0][0]
        )
        assert len(last_call_messages) >= 4  # system + 2 memory + current


class TestMemoryStore:
    async def test_add_and_retrieve(self, db: AsyncSession):
        store = DatabaseMemoryStore(db)

        await store.add(user_id=99, role="user", content="Hello")
        await store.add(user_id=99, role="assistant", content="Hi there")

        entries = await store.retrieve(user_id=99)
        assert len(entries) == 2
        assert entries[0].role == "user"
        assert entries[0].content == "Hello"
        assert entries[1].role == "assistant"
        assert entries[1].content == "Hi there"

    async def test_retrieve_respects_limit(self, db: AsyncSession):
        store = DatabaseMemoryStore(db)

        for i in range(10):
            await store.add(user_id=99, role="user", content=f"Message {i}")

        entries = await store.retrieve(user_id=99, limit=3)
        assert len(entries) == 3
        # Should be the 3 most recent in chronological order
        assert entries[0].content == "Message 7"
        assert entries[2].content == "Message 9"

    async def test_clear(self, db: AsyncSession):
        store = DatabaseMemoryStore(db)

        await store.add(user_id=99, role="user", content="To delete")
        await store.clear(user_id=99)

        count = await store.count(user_id=99)
        assert count == 0

    async def test_count(self, db: AsyncSession):
        store = DatabaseMemoryStore(db)

        assert await store.count(user_id=99) == 0
        await store.add(user_id=99, role="user", content="One")
        await store.add(user_id=99, role="user", content="Two")
        assert await store.count(user_id=99) == 2

    async def test_user_isolation(self, db: AsyncSession):
        store = DatabaseMemoryStore(db)

        await store.add(user_id=1, role="user", content="User 1 msg")
        await store.add(user_id=2, role="user", content="User 2 msg")

        entries_1 = await store.retrieve(user_id=1)
        entries_2 = await store.retrieve(user_id=2)

        assert len(entries_1) == 1
        assert len(entries_2) == 1
        assert entries_1[0].content == "User 1 msg"
        assert entries_2[0].content == "User 2 msg"
