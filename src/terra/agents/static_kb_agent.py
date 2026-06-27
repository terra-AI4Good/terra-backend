"""Static Knowledge Base agent — answers questions using Integreat pages."""

from __future__ import annotations

from typing import Any

from terra.agents.base import Agent, AgentConfig, AgentResult
from terra.llm.types import ChatMessage
from terra.services.static_kb import StaticKBService
from terra.tools.static_kb import SearchStaticKBTool

STATIC_KB_SYSTEM_PROMPT = (
    "You are a knowledgeable assistant for newcomers in Germany. "
    "You use the Integreat knowledge base to answer questions about "
    "daily life, healthcare, education, work, legal matters, housing, "
    "and integration services. Always cite your sources with page titles "
    "and URLs when available."
)


class StaticKnowledgeBaseAgent(Agent):
    """Agent that answers questions from the Integreat static knowledge base."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        service: StaticKBService | None = None,
    ) -> None:
        if config is None:
            config = AgentConfig(
                name="static_knowledge_base",
                description=(
                    "Answers questions about living in Germany using "
                    "the Integreat integration knowledge base"
                ),
                system_prompt=STATIC_KB_SYSTEM_PROMPT,
                tools=["search_static_kb", "get_static_kb_item"],
            )
        super().__init__(config)
        self._service = service

    async def run(
        self,
        input_message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Search the KB and return relevant information."""
        ctx = context or {}
        limit = ctx.get("limit", 5)
        category = ctx.get("category")

        tool = SearchStaticKBTool(service=self._service)
        result = await tool.execute(query=input_message, limit=limit, category=category)

        if not result.success:
            return AgentResult(
                success=False,
                output=f"Knowledge base search failed: {result.error}",
                error=result.error,
            )

        results = result.data.get("results", [])
        output = self._format_results(results, input_message)

        return AgentResult(
            success=True,
            output=output,
            tool_calls_made=1,
            iterations=1,
            metadata={
                "query": input_message,
                "result_count": len(results),
                "results": results,
            },
        )

    async def step(self, messages: list[ChatMessage]) -> ChatMessage:
        """Single reasoning step for orchestrator integration."""
        query = ""
        for msg in reversed(messages):
            if msg.role == "user" and msg.content:
                query = msg.content
                break

        if not query:
            return ChatMessage(
                role="assistant",
                content="What would you like to know about living in Germany?",
            )

        result = await self.run(query)
        return ChatMessage(role="assistant", content=result.output)

    def _format_results(self, results: list[dict[str, Any]], query: str) -> str:
        """Format search results into a readable answer."""
        if not results:
            return (
                f"I couldn't find information about '{query}' in the "
                "knowledge base. Try rephrasing or ask about a different topic."
            )

        lines = [
            f"Here's what I found about '{query}' ({len(results)} relevant pages):\n"
        ]
        for i, r in enumerate(results, 1):
            snippet = r.get("snippet", "")[:150]
            url = r.get("url", "")
            lines.append(
                f"{i}. **{r['title']}** ({r['category']})\n"
                f"   {snippet}...\n"
                f"   Source: {url}\n"
            )

        lines.append("\nSource: Integreat Integration Guide")
        return "\n".join(lines)
