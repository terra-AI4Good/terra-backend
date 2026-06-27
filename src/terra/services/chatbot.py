"""Chatbot service — orchestrates memory, LLM, and tools for a chat turn."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from terra.llm.service import LLMService
from terra.llm.types import ChatMessage
from terra.memory.base import MemoryEntry, MemoryStore
from terra.tools.registry import ToolRegistry

# Default system prompt for the chatbot agent
DEFAULT_SYSTEM_PROMPT = (
    "You are Terra, a helpful AI assistant. "
    "Answer the user's questions clearly and concisely. "
    "Use tools when they would help provide a better answer."
)


@dataclass
class ChatResponse:
    """Result of a single chat turn."""

    response: str
    used_tools: list[str] = field(default_factory=list)
    memory_context: list[dict[str, str]] = field(default_factory=list)


class ChatbotService:
    """Orchestrates a single chat turn.

    1. Retrieves relevant memory for the user
    2. Builds the message context (system + memory + user message)
    3. Calls the LLM (with tool schemas if tools registered)
    4. Handles tool calls in a loop
    5. Stores the interaction back into memory
    6. Returns the response
    """

    def __init__(
        self,
        llm: LLMService,
        memory: MemoryStore,
        tools: ToolRegistry | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_tool_rounds: int = 5,
    ) -> None:
        self._llm = llm
        self._memory = memory
        self._tools = tools
        self._system_prompt = system_prompt
        self._max_tool_rounds = max_tool_rounds

    async def chat(
        self,
        user_id: int,
        message: str,
    ) -> ChatResponse:
        """Process a single user message and return the assistant response."""
        # 1. Retrieve relevant memory
        memory_entries = await self._memory.retrieve(
            user_id=user_id, query=message, limit=20
        )

        # 2. Build message context
        messages = self._build_messages(message, memory_entries)

        # 3. Get tool schemas if tools are available
        tool_schemas = None
        if self._tools and len(self._tools) > 0:
            tool_schemas = self._tools.get_openai_schemas()

        # 4. Call LLM with tool loop
        used_tools: list[str] = []
        rounds = 0

        while rounds < self._max_tool_rounds:
            rounds += 1
            response = await self._llm.completion(
                messages=messages,
                tools=tool_schemas,
            )

            # If no tool calls, we have the final response
            if not response.tool_calls:
                break

            # Process tool calls
            messages.append(
                ChatMessage(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )

            for tool_call in response.tool_calls:
                used_tools.append(tool_call.function.name)
                tool_result = await self._execute_tool(tool_call)
                messages.append(
                    ChatMessage(
                        role="tool",
                        content=tool_result,
                        tool_call_id=tool_call.id,
                    )
                )

        # 5. Extract final response
        assistant_response = response.content or ""

        # 6. Store interaction in memory
        await self._memory.add(user_id=user_id, role="user", content=message)
        await self._memory.add(
            user_id=user_id, role="assistant", content=assistant_response
        )

        # 7. Build response
        memory_context = [
            {"role": e.role, "content": e.content} for e in memory_entries
        ]

        return ChatResponse(
            response=assistant_response,
            used_tools=used_tools,
            memory_context=memory_context,
        )

    def _build_messages(
        self,
        current_message: str,
        memory_entries: list[MemoryEntry],
    ) -> list[ChatMessage]:
        """Build the message list for the LLM call."""
        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=self._system_prompt),
        ]

        # Add memory as conversation context
        for entry in memory_entries:
            messages.append(
                ChatMessage(
                    role=entry.role,
                    content=entry.content,
                )
            )

        # Add current user message
        messages.append(ChatMessage(role="user", content=current_message))
        return messages

    async def _execute_tool(self, tool_call: Any) -> str:
        """Execute a tool call and return the result as a string."""
        import json

        if not self._tools:
            return json.dumps({"error": "No tools available"})

        try:
            kwargs = json.loads(tool_call.function.arguments)
            result = await self._tools.execute(tool_call.function.name, **kwargs)
            return result.model_dump_json()
        except (KeyError, json.JSONDecodeError) as e:
            return json.dumps({"error": str(e)})
