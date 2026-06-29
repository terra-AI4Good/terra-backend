"""Job listings agent — searches and ranks German job listings."""

from __future__ import annotations

from typing import Any

from terra.agents.base import Agent, AgentConfig, AgentResult
from terra.config import get_settings
from terra.llm.config import LLMSettings
from terra.llm.service import LLMService
from terra.llm.types import ChatMessage
from terra.tools.ba_jobs import SearchBAJobsTool

# System prompt for the job listings agent
JOB_AGENT_SYSTEM_PROMPT = (
    "You are a job search assistant specializing in German job listings.\n\n"
    "When a user asks for jobs, you should:\n"
    "1. Understand their search intent (job title, location, preferences).\n"
    "2. Translate or expand English job titles into useful German search "
    "terms.\n"
    "   Examples:\n"
    "   - 'machine learning engineer' → 'Machine Learning', 'KI Entwickler'\n"
    "   - 'software developer' → 'Softwareentwickler'\n"
    "   - 'nurse' → 'Krankenpfleger', 'Pflegefachkraft'\n"
    "3. Use the search_ba_jobs tool with appropriate parameters.\n"
    "4. Present results as compact job cards.\n\n"
    "Always indicate that results come from BA Jobsuche "
    "(Bundesagentur für Arbeit)."
)

# Translation hints for common English → German job terms
TERM_EXPANSIONS: dict[str, list[str]] = {
    "software engineer": ["Softwareentwickler", "Software Engineer"],
    "software developer": ["Softwareentwickler", "Software Developer"],
    "data scientist": ["Data Scientist", "Datenwissenschaftler"],
    "machine learning": ["Machine Learning", "KI Entwickler", "Data Scientist"],
    "web developer": ["Webentwickler", "Frontend Entwickler", "Web Developer"],
    "devops": ["DevOps Engineer", "Cloud Engineer", "Site Reliability"],
    "nurse": ["Pflegefachkraft", "Krankenpfleger", "Gesundheitspfleger"],
    "teacher": ["Lehrer", "Lehrkraft", "Pädagoge"],
    "accountant": ["Buchhalter", "Bilanzbuchhalter", "Accountant"],
    "marketing": ["Marketing Manager", "Online Marketing"],
    "project manager": ["Projektmanager", "Projektleiter"],
}


def expand_search_terms(query: str) -> list[str]:
    """Expand an English query into German search terms.

    Returns a list of search terms to try. The original query is always included.
    """
    terms = [query]
    query_lower = query.lower()
    for english, german_terms in TERM_EXPANSIONS.items():
        if english in query_lower:
            terms.extend(german_terms)
            break
    return terms


class JobListingsAgent(Agent):
    """Agent that searches and ranks German job listings from BA Jobsuche."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        if config is None:
            config = AgentConfig(
                name="job_listings",
                description="Search and rank German job listings from BA Jobsuche",
                system_prompt=JOB_AGENT_SYSTEM_PROMPT,
                tools=["search_ba_jobs", "get_ba_job_details"],
            )
        super().__init__(config)

    async def run(
        self,
        input_message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Search for jobs based on the user's request.

        For now, does a direct tool call without LLM reasoning.
        This can be upgraded to use the full orchestration loop later.
        """
        ctx = context or {}
        location = ctx.get("location")
        work_time = ctx.get("work_time")
        job_type = ctx.get("job_type", 1)

        # Expand search terms
        terms = expand_search_terms(input_message)
        primary_query = terms[0]
        # Use the best German expansion if available
        if len(terms) > 1:
            primary_query = terms[1]  # First German term

        # Execute the search tool
        tool = SearchBAJobsTool()
        settings = get_settings()

        tool_kwargs: dict[str, Any] = {
            "query": primary_query,
            "size": settings.ba_jobs_default_size,
        }
        if location:
            tool_kwargs["location"] = location
        if work_time:
            tool_kwargs["work_time"] = work_time
        if job_type:
            tool_kwargs["job_type"] = job_type

        result = await tool.execute(**tool_kwargs)

        if not result.success:
            return AgentResult(
                success=False,
                output=f"Job search failed: {result.error}",
                error=result.error,
            )

        # Rank results (basic ranking by recency for now)
        jobs = result.data.get("jobs", [])
        ranked_jobs = self._rank_jobs(jobs, input_message)

        # Format output
        output = self._format_output(ranked_jobs, result.data.get("total_results", 0))

        return AgentResult(
            success=True,
            output=output,
            tool_calls_made=1,
            iterations=1,
            metadata={
                "jobs": ranked_jobs,
                "total_results": result.data.get("total_results", 0),
                "search_query": primary_query,
                "expanded_terms": terms,
            },
        )

    async def step(self, messages: list[ChatMessage]) -> ChatMessage:
        """Single reasoning step using LLM (for orchestrator integration)."""
        settings = get_settings()
        llm = LLMService(
            settings=LLMSettings(
                default_model=settings.llm_default_model,
                openai_api_key=settings.openai_api_key,
            )
        )
        tool = SearchBAJobsTool()
        response = await llm.completion(
            messages=messages,
            tools=[tool.to_openai_schema()],
        )
        return ChatMessage(
            role="assistant",
            content=response.content,
            tool_calls=response.tool_calls or None,
        )

    def _rank_jobs(
        self, jobs: list[dict[str, Any]], query: str
    ) -> list[dict[str, Any]]:
        """Rank job cards by relevance signals.

        Current signals:
        - Title match (query terms in title)
        - Recency (recent jobs ranked higher)
        - Remote/telework preference
        """
        query_terms = set(query.lower().split())

        def score(job: dict[str, Any]) -> float:
            s = 0.0
            title_lower = job.get("title", "").lower()
            # Title keyword match
            for term in query_terms:
                if term in title_lower:
                    s += 10.0
            # Remote bonus
            work_time = job.get("work_time", "").lower()
            if "home" in work_time or "remote" in work_time or "tele" in work_time:
                s += 2.0
            return s

        for job in jobs:
            job["_score"] = score(job)

        jobs.sort(key=lambda j: j.get("_score", 0), reverse=True)

        # Add match reasons based on score
        for job in jobs:
            reasons = []
            title_lower = job.get("title", "").lower()
            for term in query_terms:
                if term in title_lower:
                    reasons.append(f"Title matches '{term}'")
            work_time = job.get("work_time", "").lower()
            if "home" in work_time or "remote" in work_time:
                reasons.append("Remote/Telework available")
            job["match_reason"] = "; ".join(reasons) if reasons else "Relevant listing"
            job.pop("_score", None)

        return jobs

    def _format_output(self, jobs: list[dict[str, Any]], total: int) -> str:
        """Format job cards into readable text output."""
        if not jobs:
            return "No matching jobs found. Try broadening your search."

        lines = [f"Found {total} total results. Here are the top matches:\n"]
        for i, job in enumerate(jobs, 1):
            lines.append(
                f"{i}. **{job['title']}**\n"
                f"   Employer: {job['employer']}\n"
                f"   Location: {job['location']}\n"
                f"   Work time: {job.get('work_time', 'N/A')}\n"
                f"   Published: {job.get('published_date', 'N/A')}\n"
                f"   Why: {job.get('match_reason', '')}\n"
                f"   Link: {job['detail_url']}\n"
                f"   Source: BA Jobsuche\n"
            )
        return "\n".join(lines)
