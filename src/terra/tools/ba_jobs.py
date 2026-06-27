"""BA Jobsuche tools — search and fetch German job listings."""

from __future__ import annotations

import contextlib
from typing import Any

from terra.config import get_settings
from terra.schemas.jobs import BASearchParams, JobCard
from terra.services.ba_jobs_client import BAJobsClient
from terra.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


def _get_client() -> BAJobsClient:
    """Build a BAJobsClient from current settings."""
    settings = get_settings()
    return BAJobsClient(
        base_url=settings.ba_jobs_base_url,
        api_key=settings.ba_jobs_api_key,
    )


class SearchBAJobsTool(Tool):
    """Search for job listings on the BA Jobsuche API."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_ba_jobs",
            description=(
                "Search German job listings from the Bundesagentur für Arbeit. "
                "Returns job cards with title, employer, location, and links."
            ),
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Job title or keyword (German recommended).",
                    required=True,
                ),
                ToolParameter(
                    name="location",
                    type="string",
                    description="City or region, e.g. 'Berlin' or 'München'.",
                    required=False,
                ),
                ToolParameter(
                    name="radius_km",
                    type="integer",
                    description="Search radius in km (default 50).",
                    required=False,
                ),
                ToolParameter(
                    name="job_type",
                    type="integer",
                    description=(
                        "1=job, 2=self-employment, 4=Ausbildung, 34=internship/trainee."
                    ),
                    required=False,
                ),
                ToolParameter(
                    name="work_time",
                    type="string",
                    description=("vz=full-time, tz=part-time, ho=remote, mj=minijob."),
                    required=False,
                    enum=["vz", "tz", "ho", "mj"],
                ),
                ToolParameter(
                    name="published_since_days",
                    type="integer",
                    description="Only jobs published in the last N days.",
                    required=False,
                ),
                ToolParameter(
                    name="page",
                    type="integer",
                    description="Page number (starts at 1).",
                    required=False,
                ),
                ToolParameter(
                    name="size",
                    type="integer",
                    description="Number of results per page.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Search BA jobs and return compact job cards."""
        settings = get_settings()
        client = _get_client()

        params = BASearchParams(
            was=kwargs.get("query"),
            wo=kwargs.get("location"),
            umkreis=kwargs.get("radius_km", settings.ba_jobs_default_radius_km),
            angebotsart=kwargs.get("job_type", 1),
            arbeitszeit=kwargs.get("work_time"),
            veroeffentlichtseit=kwargs.get("published_since_days", 30),
            page=kwargs.get("page", 1),
            size=kwargs.get("size", settings.ba_jobs_default_size),
        )

        try:
            search_result = await client.search(params)
        except Exception as e:
            return ToolResult(success=False, error=f"BA API error: {e}")

        # Fetch details for top N results
        details_limit = min(
            len(search_result.stellenangebote),
            settings.ba_jobs_fetch_details_limit,
        )

        cards: list[dict[str, Any]] = []
        for job in search_result.stellenangebote[:details_limit]:
            detail = None
            if job.refnr:
                with contextlib.suppress(Exception):
                    detail = await client.get_details(job.refnr)

            card = _build_job_card(job, detail)
            cards.append(card.model_dump())

        # Include remaining jobs without details
        for job in search_result.stellenangebote[details_limit:]:
            card = _build_job_card(job, None)
            cards.append(card.model_dump())

        return ToolResult(
            success=True,
            data={
                "total_results": search_result.maxErgebnisse,
                "returned": len(cards),
                "jobs": cards,
            },
        )


class GetBAJobDetailsTool(Tool):
    """Fetch detailed information for a specific BA job listing."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_ba_job_details",
            description=(
                "Get full details for a German job listing by its "
                "Referenznummer (refnr)."
            ),
            parameters=[
                ToolParameter(
                    name="refnr",
                    type="string",
                    description="The job reference number (Referenznummer).",
                    required=True,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Fetch job details."""
        refnr = kwargs.get("refnr", "")
        if not refnr:
            return ToolResult(success=False, error="refnr is required")

        client = _get_client()
        try:
            detail = await client.get_details(refnr)
        except Exception as e:
            return ToolResult(success=False, error=f"BA API error: {e}")

        if detail is None:
            return ToolResult(success=False, error="Job not found")

        return ToolResult(success=True, data=detail.model_dump())


def _build_job_card(
    summary: Any,
    detail: Any | None,
) -> JobCard:
    """Build a compact JobCard from search summary and optional detail."""
    location = ""
    if summary.arbeitsort:
        location = summary.arbeitsort.ort
        if summary.arbeitsort.region:
            location = f"{location}, {summary.arbeitsort.region}"

    work_time = summary.arbeitszeit or ""
    if detail and detail.arbeitszeit:
        work_time = detail.arbeitszeit

    # Build detail URL
    detail_url = ""
    if detail and detail.aktpiLink:
        detail_url = detail.aktpiLink
    elif summary.aktpiLink:
        detail_url = summary.aktpiLink
    elif summary.refnr:
        detail_url = f"https://www.arbeitsagentur.de/jobsuche/suche?id={summary.refnr}"

    return JobCard(
        title=detail.titel if detail else summary.titel,
        employer=detail.arbeitgeber if detail else summary.arbeitgeber,
        location=location,
        published_date=summary.veroeffentlichtAm,
        work_time=work_time,
        match_reason="",
        detail_url=detail_url,
        refnr=summary.refnr,
    )
