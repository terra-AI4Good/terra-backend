"""Tests for the BA Jobsuche integration."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from terra.agents.job_listings import JobListingsAgent, expand_search_terms
from terra.schemas.jobs import BAArbeitsort, BAJobDetail, BAJobSummary, BASearchParams
from terra.services.ba_jobs_client import BAJobsClient
from terra.tools.ba_jobs import GetBAJobDetailsTool, SearchBAJobsTool

# -- Client Tests --


class TestBAJobsClient:
    def test_encode_refnr(self):
        refnr = "10000-1234567890-S"
        encoded = BAJobsClient.encode_refnr(refnr)
        # Should be valid base64
        decoded = base64.b64decode(encoded).decode("utf-8")
        assert decoded == refnr

    def test_build_query_params_basic(self):
        client = BAJobsClient(
            base_url="https://example.com",
            api_key="test-key",
        )
        params = BASearchParams(was="Softwareentwickler", wo="Berlin", page=1, size=10)
        qp = client._build_query_params(params)
        assert qp["was"] == "Softwareentwickler"
        assert qp["wo"] == "Berlin"
        assert qp["page"] == 1
        assert qp["size"] == 10

    def test_build_query_params_with_filters(self):
        client = BAJobsClient(
            base_url="https://example.com",
            api_key="test-key",
        )
        params = BASearchParams(
            was="Data Scientist",
            wo="München",
            umkreis=25,
            angebotsart=1,
            arbeitszeit="vz",
            veroeffentlichtseit=7,
            page=2,
            size=5,
        )
        qp = client._build_query_params(params)
        assert qp["umkreis"] == 25
        assert qp["angebotsart"] == 1
        assert qp["arbeitszeit"] == "vz"
        assert qp["veroeffentlichtseit"] == 7
        assert qp["page"] == 2

    def test_build_query_params_skips_none(self):
        client = BAJobsClient(base_url="https://x.com", api_key="k")
        params = BASearchParams(was="test", page=1, size=10)
        qp = client._build_query_params(params)
        assert "wo" not in qp
        assert "umkreis" not in qp
        assert "angebotsart" not in qp

    def test_headers_contain_api_key(self):
        client = BAJobsClient(
            base_url="https://example.com",
            api_key="jobboerse-jobsuche",
        )
        headers = client._headers()
        assert headers["X-API-Key"] == "jobboerse-jobsuche"

    async def test_search_calls_correct_endpoint(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "maxErgebnisse": 1,
            "stellenangebote": [
                {
                    "titel": "Python Developer",
                    "refnr": "10000-123-S",
                    "arbeitgeber": "TechCo",
                    "arbeitsort": {"ort": "Berlin"},
                    "veroeffentlichtAm": "2025-01-15",
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        client = BAJobsClient(
            base_url="https://rest.arbeitsagentur.de/jobboerse/jobsuche-service",
            api_key="jobboerse-jobsuche",
            http_client=mock_client,
        )

        params = BASearchParams(was="Python", wo="Berlin", page=1, size=5)
        result = await client.search(params)

        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "/pc/v6/jobs" in call_args[0][0]
        assert call_args[1]["headers"]["X-API-Key"] == "jobboerse-jobsuche"
        assert result.maxErgebnisse == 1
        assert len(result.stellenangebote) == 1
        assert result.stellenangebote[0].titel == "Python Developer"

    async def test_get_details_encodes_refnr_in_url(self):
        refnr = "10000-1234567890-S"
        expected_encoded = base64.b64encode(refnr.encode()).decode()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "titel": "Senior Dev",
            "refnr": refnr,
            "arbeitgeber": "Corp",
            "arbeitsort": {"ort": "Hamburg"},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        client = BAJobsClient(
            base_url="https://rest.arbeitsagentur.de/jobboerse/jobsuche-service",
            api_key="jobboerse-jobsuche",
            http_client=mock_client,
        )

        result = await client.get_details(refnr)

        call_url = mock_client.get.call_args[0][0]
        assert expected_encoded in call_url
        assert "/pc/v4/jobdetails/" in call_url
        assert result is not None
        assert result.titel == "Senior Dev"

    async def test_get_details_returns_none_on_404(self):
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        client = BAJobsClient(
            base_url="https://example.com",
            api_key="key",
            http_client=mock_client,
        )

        result = await client.get_details("nonexistent-refnr")
        assert result is None


# -- Tool Tests --


class TestSearchBAJobsTool:
    def test_definition(self):
        tool = SearchBAJobsTool()
        assert tool.name == "search_ba_jobs"
        assert len(tool.definition.parameters) > 0

    def test_openai_schema(self):
        tool = SearchBAJobsTool()
        schema = tool.to_openai_schema()
        assert schema["function"]["name"] == "search_ba_jobs"
        assert "query" in schema["function"]["parameters"]["properties"]

    @patch("terra.tools.ba_jobs._get_client")
    async def test_execute_calls_search(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            return_value=MagicMock(
                maxErgebnisse=1,
                stellenangebote=[
                    BAJobSummary(
                        titel="ML Engineer",
                        refnr="REF-001",
                        arbeitgeber="AI Corp",
                        arbeitsort=BAArbeitsort(ort="Berlin"),
                        veroeffentlichtAm="2025-06-01",
                        arbeitszeit="Vollzeit",
                    )
                ],
            )
        )
        mock_client.get_details = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_client

        tool = SearchBAJobsTool()
        result = await tool.execute(query="Machine Learning", location="Berlin")

        assert result.success is True
        assert result.data["total_results"] == 1
        assert len(result.data["jobs"]) == 1
        assert result.data["jobs"][0]["title"] == "ML Engineer"

    @patch("terra.tools.ba_jobs._get_client")
    async def test_execute_maps_work_time(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            return_value=MagicMock(maxErgebnisse=0, stellenangebote=[])
        )
        mock_get_client.return_value = mock_client

        tool = SearchBAJobsTool()
        await tool.execute(query="Dev", work_time="ho")

        call_args = mock_client.search.call_args[0][0]
        assert call_args.arbeitszeit == "ho"


class TestGetBAJobDetailsTool:
    def test_definition(self):
        tool = GetBAJobDetailsTool()
        assert tool.name == "get_ba_job_details"

    @patch("terra.tools.ba_jobs._get_client")
    async def test_execute_fetches_details(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get_details = AsyncMock(
            return_value=BAJobDetail(
                titel="Senior Developer",
                refnr="REF-002",
                arbeitgeber="BigCo",
                arbeitsort=BAArbeitsort(ort="München"),
            )
        )
        mock_get_client.return_value = mock_client

        tool = GetBAJobDetailsTool()
        result = await tool.execute(refnr="REF-002")

        assert result.success is True
        assert result.data["titel"] == "Senior Developer"

    @patch("terra.tools.ba_jobs._get_client")
    async def test_execute_missing_refnr(self, mock_get_client):
        tool = GetBAJobDetailsTool()
        result = await tool.execute()
        assert result.success is False
        assert "required" in result.error


# -- Agent Tests --


class TestJobListingsAgent:
    def test_expand_search_terms_english(self):
        terms = expand_search_terms("machine learning engineer")
        assert "machine learning engineer" in terms
        assert any("Machine Learning" in t for t in terms)
        assert any("KI" in t for t in terms)

    def test_expand_search_terms_german_passthrough(self):
        terms = expand_search_terms("Softwareentwickler")
        assert terms == ["Softwareentwickler"]

    def test_expand_search_terms_nurse(self):
        terms = expand_search_terms("nurse practitioner")
        assert "Pflegefachkraft" in terms

    @patch("terra.tools.ba_jobs._get_client")
    async def test_agent_run_searches_and_returns_cards(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            return_value=MagicMock(
                maxErgebnisse=2,
                stellenangebote=[
                    BAJobSummary(
                        titel="Data Scientist",
                        refnr="REF-A",
                        arbeitgeber="DataCo",
                        arbeitsort=BAArbeitsort(ort="Berlin"),
                        veroeffentlichtAm="2025-06-10",
                        arbeitszeit="Vollzeit",
                    ),
                    BAJobSummary(
                        titel="ML Engineer",
                        refnr="REF-B",
                        arbeitgeber="AICo",
                        arbeitsort=BAArbeitsort(ort="Hamburg"),
                        veroeffentlichtAm="2025-06-09",
                        arbeitszeit="Teilzeit",
                    ),
                ],
            )
        )
        mock_client.get_details = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_client

        agent = JobListingsAgent()
        result = await agent.run("data scientist jobs")

        assert result.success is True
        assert "Data Scientist" in result.output or "ML Engineer" in result.output
        assert result.metadata["total_results"] == 2
        assert len(result.metadata["jobs"]) == 2

    @patch("terra.tools.ba_jobs._get_client")
    async def test_agent_expands_english_terms(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            return_value=MagicMock(maxErgebnisse=0, stellenangebote=[])
        )
        mock_client.get_details = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_client

        agent = JobListingsAgent()
        result = await agent.run("software engineer")

        # Should have used a German term for search
        assert "Softwareentwickler" in result.metadata["expanded_terms"]

    @patch("terra.tools.ba_jobs._get_client")
    async def test_agent_passes_context_location(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            return_value=MagicMock(maxErgebnisse=0, stellenangebote=[])
        )
        mock_client.get_details = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_client

        agent = JobListingsAgent()
        await agent.run("developer", context={"location": "München"})

        # Verify the search was called
        assert mock_client.search.called


# -- Integration with chatbot --


class TestChatbotIntegration:
    @patch("terra.tools.ba_jobs._get_client")
    async def test_search_tool_registered_and_callable(self, mock_get_client):
        """The search tool can be instantiated and called."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            return_value=MagicMock(maxErgebnisse=0, stellenangebote=[])
        )
        mock_get_client.return_value = mock_client

        from terra.tools.registry import ToolRegistry

        registry = ToolRegistry()
        registry.register(SearchBAJobsTool())
        registry.register(GetBAJobDetailsTool())

        assert "search_ba_jobs" in registry
        assert "get_ba_job_details" in registry

        result = await registry.execute("search_ba_jobs", query="test")
        assert result.success is True
