"""Schemas for BA Jobsuche API responses and internal job cards."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JobCard(BaseModel):
    """Compact job card returned to the user."""

    title: str
    employer: str
    location: str
    published_date: str | None = None
    work_time: str | None = None
    match_reason: str = ""
    detail_url: str
    refnr: str
    source: str = "BA Jobsuche (Bundesagentur für Arbeit)"


class BASearchParams(BaseModel):
    """Parameters for the BA search endpoint."""

    was: str | None = None
    wo: str | None = None
    umkreis: int | None = None
    page: int = 1
    size: int = 10
    angebotsart: int | None = None
    arbeitszeit: str | None = None
    befristung: int | None = None
    veroeffentlichtseit: int | None = None
    zeitarbeit: bool | None = None
    pav: bool | None = None
    arbeitgeber: str | None = None
    berufsfeld: str | None = None


class BAJobSummary(BaseModel):
    """A single job result from the BA search response."""

    titel: str = ""
    refnr: str = ""
    arbeitgeber: str = ""
    arbeitsort: BAArbeitsort | None = None
    eintrittsdatum: str | None = None
    veroeffentlichtAm: str | None = None
    arbeitszeit: str | None = None
    befristung: str | None = None
    aktpiLink: str | None = None


class BAArbeitsort(BaseModel):
    """Location info from BA API."""

    ort: str = ""
    plz: str | None = None
    region: str | None = None
    land: str | None = None


class BASearchResponse(BaseModel):
    """Parsed BA search response."""

    maxErgebnisse: int = 0
    stellenangebote: list[BAJobSummary] = Field(default_factory=list)


class BAJobDetail(BaseModel):
    """Selected fields from the BA job details response."""

    titel: str = ""
    refnr: str = ""
    arbeitgeber: str = ""
    arbeitsort: BAArbeitsort | None = None
    stellenbeschreibung: str | None = None
    arbeitszeit: str | None = None
    befristung: str | None = None
    veroeffentlichtAm: str | None = None
    eintrittsdatum: str | None = None
    alternpiLink: str | None = None
    aktpiLink: str | None = None
    branche: str | None = None
    kundennummerHash: str | None = None
    # Additional fields that may be present
    arbeitszeitmodelle: list[str] = Field(default_factory=list)
    branchengruppe: str | None = None
