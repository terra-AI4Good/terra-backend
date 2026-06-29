"""HTTP client for the Bundesagentur für Arbeit Jobsuche API."""

from __future__ import annotations

import base64
from typing import Any

import httpx

from terra.schemas.jobs import (
    BAJobDetail,
    BAJobSummary,
    BASearchParams,
    BASearchResponse,
)


class BAJobsClient:
    """Client for the BA Jobsuche REST API.

    Handles authentication, request building, and response parsing.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client = http_client

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=self._timeout)

    @staticmethod
    def encode_refnr(refnr: str) -> str:
        """Base64-encode a Referenznummer for the details endpoint."""
        return base64.b64encode(refnr.encode("utf-8")).decode("utf-8")

    async def search(self, params: BASearchParams) -> BASearchResponse:
        """Search for jobs using the BA API.

        Args:
            params: Search parameters.

        Returns:
            Parsed search response with job summaries.
        """
        query_params = self._build_query_params(params)
        client = await self._get_client()
        should_close = self._client is None

        try:
            response = await client.get(
                f"{self._base_url}/pc/v6/jobs",
                params=query_params,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_search_response(data)
        finally:
            if should_close:
                await client.aclose()

    async def get_details(self, refnr: str) -> BAJobDetail | None:
        """Fetch detailed job information by Referenznummer.

        Args:
            refnr: The job reference number.

        Returns:
            Parsed job detail or None if not found.
        """
        encoded = self.encode_refnr(refnr)
        client = await self._get_client()
        should_close = self._client is None

        try:
            response = await client.get(
                f"{self._base_url}/pc/v4/jobdetails/{encoded}",
                headers=self._headers(),
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return self._parse_detail_response(data)
        finally:
            if should_close:
                await client.aclose()

    async def get_employer_logo_url(self, kundennummer_hash: str) -> str:
        """Build the employer logo URL (no HTTP call needed)."""
        return (
            "https://rest.arbeitsagentur.de/vermittlung/"
            f"ag-darstellung-service/ct/v1/arbeitgeberlogo/{kundennummer_hash}"
        )

    def _build_query_params(self, params: BASearchParams) -> dict[str, Any]:
        """Convert BASearchParams to query string dict."""
        qp: dict[str, Any] = {}
        if params.was:
            qp["was"] = params.was
        if params.wo:
            qp["wo"] = params.wo
        if params.umkreis is not None:
            qp["umkreis"] = params.umkreis
        qp["page"] = params.page
        qp["size"] = params.size
        if params.angebotsart is not None:
            qp["angebotsart"] = params.angebotsart
        if params.arbeitszeit:
            qp["arbeitszeit"] = params.arbeitszeit
        if params.befristung is not None:
            qp["befristung"] = params.befristung
        if params.veroeffentlichtseit is not None:
            qp["veroeffentlichtseit"] = params.veroeffentlichtseit
        if params.zeitarbeit is not None:
            qp["zeitarbeit"] = params.zeitarbeit
        if params.pav is not None:
            qp["pav"] = params.pav
        if params.arbeitgeber:
            qp["arbeitgeber"] = params.arbeitgeber
        if params.berufsfeld:
            qp["berufsfeld"] = params.berufsfeld
        return qp

    def _parse_search_response(self, data: dict[str, Any]) -> BASearchResponse:
        """Parse the raw JSON search response."""
        stellenangebote: list[BAJobSummary] = []
        for item in data.get("stellenangebote", []):
            stellenangebote.append(BAJobSummary.model_validate(item))
        return BASearchResponse(
            maxErgebnisse=data.get("maxErgebnisse", 0),
            stellenangebote=stellenangebote,
        )

    def _parse_detail_response(self, data: dict[str, Any]) -> BAJobDetail:
        """Parse the raw JSON detail response."""
        return BAJobDetail.model_validate(data)
