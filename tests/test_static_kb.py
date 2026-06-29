"""Tests for the static knowledge base integration."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from terra.agents.static_kb_agent import StaticKnowledgeBaseAgent
from terra.scripts.fetch_static_kb import process_pages, strip_html
from terra.services.static_kb import StaticKBService
from terra.tools.static_kb import (
    GetStaticKBItemTool,
    ListStaticKBCategoriesTool,
    SearchStaticKBTool,
)

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "static_kb_sample.json")


def _get_service() -> StaticKBService:
    """Create a service pointing to the test fixture."""
    StaticKBService.reset()
    return StaticKBService(data_path=FIXTURE_PATH)


# -- Fetch Script Tests --


class TestFetchScript:
    def test_strip_html(self):
        html = "<p>Hello <strong>world</strong></p><br/><a href='#'>link</a>"
        text = strip_html(html)
        assert "Hello" in text
        assert "world" in text
        assert "<" not in text

    def test_process_pages_extracts_fields(self):
        raw = [
            {
                "id": 999,
                "title": "Test Page",
                "path": "/region/de/category/test-page/",
                "content": "<p>Some content here</p>",
                "url": "https://example.com/test",
                "modified_gmt": "2025-01-01T00:00:00Z",
                "excerpt": "",
                "parent": {"id": 1, "url": None, "path": None},
                "available_languages": {"en": {}, "ar": {}},
                "thumbnail": None,
            }
        ]
        pages = process_pages(raw)
        assert len(pages) == 1
        assert pages[0]["id"] == "999"
        assert pages[0]["title"] == "Test Page"
        assert pages[0]["category"] == "category"
        assert "Some content here" in pages[0]["content_text"]
        assert "<p>" not in pages[0]["content_text"]

    def test_process_pages_handles_empty_content(self):
        raw = [
            {
                "id": 1,
                "title": "Empty",
                "path": "/r/de/cat/empty/",
                "content": "",
                "url": "",
                "modified_gmt": "",
                "excerpt": "",
                "parent": {"id": 0},
                "available_languages": {},
                "thumbnail": None,
            }
        ]
        pages = process_pages(raw)
        assert len(pages) == 1
        assert pages[0]["content_text"] == ""

    def test_fetch_saves_valid_json(self):
        """Process + save produces valid JSON."""
        raw = [
            {
                "id": 42,
                "title": "Saved",
                "path": "/r/de/c/saved/",
                "content": "<b>Bold</b>",
                "url": "https://x.com",
                "modified_gmt": "2025-06-01",
                "excerpt": "",
                "parent": {"id": 0},
                "available_languages": ["en"],
                "thumbnail": "",
            }
        ]
        pages = process_pages(raw)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(pages, f)
            f.flush()
            loaded = json.loads(Path(f.name).read_text())
        assert len(loaded) == 1
        assert loaded[0]["title"] == "Saved"


# -- Service Tests --


class TestStaticKBService:
    def test_search_by_keyword(self):
        service = _get_service()
        results = service.search("Krankenversicherung")
        assert len(results) >= 1
        assert results[0]["title"] == "Gesundheitsversorgung"

    def test_search_multiple_terms(self):
        service = _get_service()
        results = service.search("Wohnung finden")
        assert len(results) >= 1
        assert any("Wohnung" in r["title"] for r in results)

    def test_search_with_category_filter(self):
        service = _get_service()
        results = service.search("Kurs", category="schule-studium-bildung")
        assert all(r["category"] == "schule-studium-bildung" for r in results)

    def test_search_respects_limit(self):
        service = _get_service()
        results = service.search("Deutschland", limit=2)
        assert len(results) <= 2

    def test_get_item_by_id(self):
        service = _get_service()
        item = service.get_item("100003")
        assert item is not None
        assert item["title"] == "Wohnung finden"

    def test_get_item_not_found(self):
        service = _get_service()
        item = service.get_item("nonexistent")
        assert item is None

    def test_list_categories(self):
        service = _get_service()
        categories = service.list_categories()
        assert "gesundheit" in categories
        assert "alltag" in categories
        assert "arbeit-ausbildung" in categories


# -- Tool Tests --


class TestSearchStaticKBTool:
    def test_definition(self):
        tool = SearchStaticKBTool()
        assert tool.name == "search_static_kb"

    async def test_execute_returns_results(self):
        service = _get_service()
        tool = SearchStaticKBTool(service=service)
        result = await tool.execute(query="Krankenversicherung")
        assert result.success is True
        assert result.data["total"] >= 1
        assert result.data["results"][0]["title"] == "Gesundheitsversorgung"

    async def test_execute_empty_query_fails(self):
        tool = SearchStaticKBTool(service=_get_service())
        result = await tool.execute(query="")
        assert result.success is False


class TestGetStaticKBItemTool:
    async def test_execute_gets_item(self):
        service = _get_service()
        tool = GetStaticKBItemTool(service=service)
        result = await tool.execute(item_id="100004")
        assert result.success is True
        assert result.data["title"] == "Arbeitserlaubnis"
        assert "content" in result.data

    async def test_execute_not_found(self):
        tool = GetStaticKBItemTool(service=_get_service())
        result = await tool.execute(item_id="missing")
        assert result.success is False


class TestListCategoriesTool:
    async def test_execute_lists_categories(self):
        tool = ListStaticKBCategoriesTool(service=_get_service())
        result = await tool.execute()
        assert result.success is True
        assert "gesundheit" in result.data["categories"]


# -- Agent Tests --


class TestStaticKBAgent:
    async def test_run_searches_and_returns_formatted(self):
        service = _get_service()
        agent = StaticKnowledgeBaseAgent(service=service)
        result = await agent.run("Deutschkurs")
        assert result.success is True
        assert "Deutschkurse" in result.output
        assert result.metadata["result_count"] >= 1

    async def test_run_no_results(self):
        service = _get_service()
        agent = StaticKnowledgeBaseAgent(service=service)
        result = await agent.run("xyznonexistent123")
        assert result.success is True
        assert "couldn't find" in result.output.lower()

    async def test_agent_callable_from_registry(self):
        from terra.agents.base import AgentConfig
        from terra.agents.registry import AgentRegistry

        registry = AgentRegistry()
        config = AgentConfig(
            name="static_knowledge_base",
            description="KB agent",
            tools=["search_static_kb"],
        )
        registry.register(StaticKnowledgeBaseAgent, config)
        assert "static_knowledge_base" in registry

    async def test_step_returns_chat_message(self):
        from terra.llm.types import ChatMessage

        service = _get_service()
        agent = StaticKnowledgeBaseAgent(service=service)
        messages = [
            ChatMessage(role="user", content="healthcare in Germany"),
        ]
        response = await agent.step(messages)
        assert response.role == "assistant"
        assert len(response.content) > 0
