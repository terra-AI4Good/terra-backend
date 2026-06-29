"""Search agent — general-purpose web search capability."""

from __future__ import annotations

from typing import Any

from terra.agents.base import Agent, AgentConfig, AgentResult
from terra.llm.types import ChatMessage
from terra.services.search.base import SearchProvider
from terra.tools.search import WebSearchTool

SEARCH_AGENT_SYSTEM_PROMPT = (
    "You are a research assistant. When asked a question that requires "
    "current or external information, use the web_search tool to find "
    "relevant results. Summarize findings clearly with source URLs."
)


class SearchAgent(Agent):
    """Agent that searches the web and returns structured results.

    Can be used standalone or called by other agents/orchestrator
    when external information is needed.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        provider: SearchProvider | None = None,
    ) -> None:
        if config is None:
            config = AgentConfig(
                name="web_search",
                description="Search the web for current information",
                system_prompt=SEARCH_AGENT_SYSTEM_PROMPT,
                tools=["web_search"],
            )
        super().__init__(config)
        self._provider = provider

    async def run(
        self,
        input_message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Search the web for the given query and return results."""
        ctx = context or {}
        max_results = ctx.get("max_results", 5)
        search_depth = ctx.get("search_depth", "basic")
        include_answer = ctx.get("include_answer", False)

        tool = WebSearchTool(provider=self._provider)
        result = await tool.execute(
            query=input_message,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=include_answer,
        )

        if not result.success:
            return AgentResult(
                success=False,
                output=f"Search failed: {result.error}",
                error=result.error,
            )

        # Format output
        data = result.data
        output = self._format_results(data)

        return AgentResult(
            success=True,
            output=output,
            tool_calls_made=1,
            iterations=1,
            metadata={
                "query": data.get("query", input_message),
                "answer": data.get("answer"),
                "result_count": len(data.get("results", [])),
                "results": data.get("results", []),
            },
        )

    async def step(self, messages: list[ChatMessage]) -> ChatMessage:
        """Single step — for orchestrator integration."""
        # Extract the last user message as query
        query = ""
        for msg in reversed(messages):
            if msg.role == "user" and msg.content:
                query = msg.content
                break

        if not query:
            return ChatMessage(
                role="assistant",
                content="I need a search query to look something up.",
            )

        result = await self.run(query)
        return ChatMessage(role="assistant", content=result.output)

    def _format_results(self, data: dict[str, Any]) -> str:
        """Format search results into readable text."""
        results = data.get("results", [])
        if not results:
            return "No results found for your query."

        lines: list[str] = []

        # Include AI answer if present
        answer = data.get("answer")
        if answer:
            lines.append(f"**Summary:** {answer}\n")

        lines.append(f"Found {len(results)} results:\n")
        for i, r in enumerate(results, 1):
            lines.append(
                f"{i}. **{r['title']}**\n"
                f"   {r['snippet'][:200]}\n"
                f"   Source: {r['domain']} — {r['url']}\n"
            )

        return "\n".join(lines)
