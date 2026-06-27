"""Chatbot endpoint — authenticated conversational AI."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from terra.api.deps import get_current_user, get_db
from terra.config import get_settings
from terra.llm.config import LLMSettings
from terra.llm.service import LLMService
from terra.memory.db_store import DatabaseMemoryStore
from terra.models.user import User
from terra.tools.registry import tool_registry

router = APIRouter()


# -- Schemas --


class ChatRequest(BaseModel):
    """Chatbot request — only the current message, no history."""

    message: str = Field(min_length=1, max_length=10000)


class ChatResponseSchema(BaseModel):
    """Chatbot response."""

    response: str
    used_tools: list[str] = Field(default_factory=list)
    # Only exposed in debug mode
    memory_context: list[dict[str, str]] | None = None


# -- Endpoint --


@router.post("/chat", response_model=ChatResponseSchema)
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponseSchema:
    """Send a message and get an AI response.

    The backend automatically maintains conversation memory.
    No history needs to be sent by the client.
    """
    from terra.services.chatbot import ChatbotService

    settings = get_settings()

    # Build service dependencies
    llm_settings = LLMSettings(
        default_model=settings.llm_default_model,
        default_temperature=settings.llm_default_temperature,
        default_max_tokens=settings.llm_default_max_tokens,
        default_timeout=settings.llm_default_timeout,
        openai_api_key=settings.openai_api_key,
        anthropic_api_key=settings.anthropic_api_key,
    )
    llm = LLMService(settings=llm_settings)
    memory = DatabaseMemoryStore(db)

    chatbot = ChatbotService(
        llm=llm,
        memory=memory,
        tools=tool_registry if len(tool_registry) > 0 else None,
    )

    result = await chatbot.chat(user_id=user.id, message=body.message)

    # Only expose memory context in debug mode
    memory_context = None
    if settings.debug:
        memory_context = result.memory_context

    return ChatResponseSchema(
        response=result.response,
        used_tools=result.used_tools,
        memory_context=memory_context,
    )
