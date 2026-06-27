"""Fetch and process the static knowledge base from the Integreat CMS API.

Usage:
    python -m terra.scripts.fetch_static_kb
"""

from __future__ import annotations

import json
import re
import sys
from html import unescape
from pathlib import Path
from typing import Any

import httpx

from terra.config import get_settings


def strip_html(html: str) -> str:
    """Strip HTML tags and decode entities to plain text."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    # Collapse whitespace
    return re.sub(r"\s+", " ", text).strip()


def fetch_payload() -> list[dict[str, Any]]:
    """Fetch the raw JSON payload from the configured API URL."""
    settings = get_settings()
    url = settings.static_kb_api_url
    timeout = settings.static_kb_fetch_timeout_seconds

    print(f"Fetching from: {url}")  # noqa: T201
    headers: dict[str, str] = {}
    if settings.static_kb_api_key:
        headers["Authorization"] = f"Bearer {settings.static_kb_api_key}"

    with httpx.Client(timeout=timeout) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()

    data = response.json()
    if not isinstance(data, list):
        msg = f"Expected a list, got {type(data).__name__}"
        raise TypeError(msg)

    return data


def save_raw(data: list[dict[str, Any]], path: str) -> Path:
    """Save the raw payload to disk."""
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return filepath


def process_pages(raw_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize raw pages into a searchable format."""
    pages: list[dict[str, Any]] = []
    for record in raw_data:
        content_html = record.get("content", "") or ""
        content_text = strip_html(content_html)

        # Skip empty pages (category containers without content)
        if not content_text and not record.get("title"):
            continue

        # Extract category from path
        path = record.get("path", "")
        path_parts = path.strip("/").split("/")
        category = path_parts[2] if len(path_parts) > 2 else ""

        page = {
            "id": str(record.get("id", "")),
            "title": record.get("title", ""),
            "path": path,
            "category": category,
            "content_text": content_text,
            "content_html": content_html,
            "excerpt": record.get("excerpt", "") or "",
            "url": record.get("url", ""),
            "modified": record.get("modified_gmt", ""),
            "parent_id": str(
                record.get("parent", {}).get("id", 0)
                if isinstance(record.get("parent"), dict)
                else 0
            ),
            "languages": (
                list(record.get("available_languages", {}).keys())
                if isinstance(record.get("available_languages"), dict)
                else record.get("available_languages", [])
            ),
            "thumbnail": record.get("thumbnail", ""),
        }
        pages.append(page)

    return pages


def save_processed(pages: list[dict[str, Any]], path: str) -> Path:
    """Save normalized pages to disk."""
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(
        json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return filepath


def main() -> None:
    """Fetch, process, and save the static knowledge base."""
    settings = get_settings()

    # Fetch
    try:
        raw_data = fetch_payload()
    except Exception as e:
        print(f"ERROR: Failed to fetch: {e}", file=sys.stderr)  # noqa: T201
        sys.exit(1)

    # Save raw
    raw_path = save_raw(raw_data, settings.static_kb_raw_path)
    raw_size_mb = raw_path.stat().st_size / (1024 * 1024)
    print(f"Saved raw payload: {raw_path} ({raw_size_mb:.1f} MB)")  # noqa: T201

    # Process
    pages = process_pages(raw_data)
    proc_path = save_processed(pages, settings.static_kb_processed_path)
    proc_size_mb = proc_path.stat().st_size / (1024 * 1024)
    print(f"Saved processed: {proc_path} ({proc_size_mb:.1f} MB)")  # noqa: T201

    # Summary
    categories = {p["category"] for p in pages if p["category"]}
    with_content = sum(1 for p in pages if p["content_text"])
    print("\nSummary:")  # noqa: T201
    print(f"  Total records: {len(raw_data)}")  # noqa: T201
    print(f"  Processed pages: {len(pages)}")  # noqa: T201
    print(f"  Pages with content: {with_content}")  # noqa: T201
    print(f"  Categories: {len(categories)}")  # noqa: T201
    print(f"  Sample categories: {sorted(categories)[:8]}")  # noqa: T201


if __name__ == "__main__":
    main()
