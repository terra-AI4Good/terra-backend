# Static Knowledge Base — Integreat CMS Pages

## Source

**API**: `https://cms.integreat-app.de/testumgebung-frag-integreat/de/wp-json/extensions/v3/pages/`
**Format**: JSON array of page objects
**Auth**: None required

## Payload Structure

The API returns a flat list of 616 page records. Each record is a single informational page from the Integreat integration guide (München test environment).

### Record Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Unique page ID |
| `url` | string | Admin/canonical URL |
| `path` | string | Hierarchical path (e.g. `/region/de/category/page/`) |
| `title` | string | Page title (German) |
| `modified_gmt` | string | Last modification timestamp (ISO 8601) |
| `last_updated` | string | Same with timezone |
| `excerpt` | string | Short excerpt (often empty) |
| `content` | string | Full HTML content of the page |
| `parent` | object | `{id, url, path}` — parent page reference |
| `order` | int | Sort order within parent |
| `available_languages` | dict/list | Available translations (keys are language codes) |
| `thumbnail` | string/null | Image URL |
| `organization` | string/null | Responsible organization |
| `hash` | string/null | Content hash |
| `embedded_offers` | list | Embedded offers (usually empty) |

### Hierarchy

Pages are organized hierarchically via `parent.id`. Top-level pages (parent.id = 0) are category roots.

### Categories (derived from path)

| Category Slug | Topic |
|---------------|-------|
| `alltag` | Daily life, housing, banking |
| `arbeit-ausbildung` | Work and vocational training |
| `beratung-und-hilfe-4` | Counseling and support services |
| `gesundheit` | Healthcare |
| `info-aufenthalt` | Residence and legal status |
| `kinder-jugendliche-familie` | Children, youth, family |
| `kultur-freizeit-sport` | Culture, leisure, sports |
| `schule-studium-bildung` | School, university, education |
| `angebote-für-frauen-und-mädchen` | Services for women and girls |
| `frag-integreat` | FAQ / ask Integreat |
| `sprache` | Language courses |
| `willkommen` | Welcome / getting started |
| `medien` | Media |

### Statistics

- **Total records**: 616
- **Pages with content**: 520
- **Categories**: 13
- **Available languages**: 23 (de, en, ar, fr, es, tr, uk, fa, ru, etc.)

## Processed Format

The fetch script normalizes raw pages into:

```json
{
  "id": "7003369",
  "title": "Über Integreat",
  "path": "/testumgebung-frag-integreat/de/willkommen/über-integreat/",
  "category": "willkommen",
  "content_text": "Plain text version (HTML stripped)",
  "content_html": "Original HTML",
  "excerpt": "",
  "url": "https://admin.integreat-app.de/...",
  "modified": "2025-01-16T12:38:21.708Z",
  "parent_id": "52039",
  "languages": ["en", "ar", "fr", ...],
  "thumbnail": "..."
}
```

## Retrieval

Current implementation: keyword-based search over `title` and `content_text` with category filtering. Scoring weights title matches higher than content matches.

Future options:
- SQLite FTS5 for full-text search
- Vector embeddings for semantic retrieval
- Chunking + RAG for long-form answers
