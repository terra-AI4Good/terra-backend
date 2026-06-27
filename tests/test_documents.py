"""Tests for document upload and management."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from terra.memory.db_store import DatabaseMemoryStore
from terra.services.documents import _chunk_text, _content_hash

# -- Helpers --


async def _auth_token(client: AsyncClient, username: str = "docuser") -> str:
    """Register a user and return their auth token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "docpass123!"},
    )
    return resp.json()["token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# -- Tests --


class TestDocumentUpload:
    async def test_upload_document(self, client: AsyncClient):
        token = await _auth_token(client)
        response = await client.post(
            "/api/v1/documents",
            json={"title": "test.txt", "content": "Hello world document"},
            headers=_auth_headers(token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "test.txt"
        assert data["id"] > 0
        assert "content_hash" in data
        assert "created_at" in data

    async def test_upload_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/documents",
            json={"title": "test.txt", "content": "content"},
        )
        assert response.status_code == 401

    async def test_upload_empty_title_rejected(self, client: AsyncClient):
        token = await _auth_token(client)
        response = await client.post(
            "/api/v1/documents",
            json={"title": "", "content": "content"},
            headers=_auth_headers(token),
        )
        assert response.status_code == 422

    async def test_upload_empty_content_rejected(self, client: AsyncClient):
        token = await _auth_token(client)
        response = await client.post(
            "/api/v1/documents",
            json={"title": "test.txt", "content": ""},
            headers=_auth_headers(token),
        )
        assert response.status_code == 422


class TestDocumentList:
    async def test_list_documents(self, client: AsyncClient):
        token = await _auth_token(client)
        headers = _auth_headers(token)

        # Upload two documents
        await client.post(
            "/api/v1/documents",
            json={"title": "doc1.txt", "content": "First document"},
            headers=headers,
        )
        await client.post(
            "/api/v1/documents",
            json={"title": "doc2.txt", "content": "Second document"},
            headers=headers,
        )

        response = await client.get("/api/v1/documents", headers=headers)
        assert response.status_code == 200
        docs = response.json()
        assert len(docs) == 2
        titles = {d["title"] for d in docs}
        assert "doc1.txt" in titles
        assert "doc2.txt" in titles

    async def test_list_empty(self, client: AsyncClient):
        token = await _auth_token(client)
        response = await client.get("/api/v1/documents", headers=_auth_headers(token))
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/documents")
        assert response.status_code == 401


class TestDocumentFetch:
    async def test_get_document_with_content(self, client: AsyncClient):
        token = await _auth_token(client)
        headers = _auth_headers(token)

        upload = await client.post(
            "/api/v1/documents",
            json={"title": "detail.txt", "content": "Full content here"},
            headers=headers,
        )
        doc_id = upload.json()["id"]

        response = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Full content here"
        assert data["title"] == "detail.txt"

    async def test_get_nonexistent_document(self, client: AsyncClient):
        token = await _auth_token(client)
        response = await client.get(
            "/api/v1/documents/9999", headers=_auth_headers(token)
        )
        assert response.status_code == 404

    async def test_cannot_access_other_users_document(self, client: AsyncClient):
        # User A uploads
        token_a = await _auth_token(client, username="user_a")
        upload = await client.post(
            "/api/v1/documents",
            json={"title": "private.txt", "content": "Secret stuff"},
            headers=_auth_headers(token_a),
        )
        doc_id = upload.json()["id"]

        # User B tries to access it
        token_b = await _auth_token(client, username="user_b")
        response = await client.get(
            f"/api/v1/documents/{doc_id}", headers=_auth_headers(token_b)
        )
        assert response.status_code == 404


class TestDocumentDelete:
    async def test_delete_document(self, client: AsyncClient):
        token = await _auth_token(client)
        headers = _auth_headers(token)

        upload = await client.post(
            "/api/v1/documents",
            json={"title": "delete-me.txt", "content": "To be deleted"},
            headers=headers,
        )
        doc_id = upload.json()["id"]

        response = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
        assert response.status_code == 204

        # Confirm it's gone
        response = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert response.status_code == 404

    async def test_delete_nonexistent(self, client: AsyncClient):
        token = await _auth_token(client)
        response = await client.delete(
            "/api/v1/documents/9999", headers=_auth_headers(token)
        )
        assert response.status_code == 404

    async def test_cannot_delete_other_users_document(self, client: AsyncClient):
        token_a = await _auth_token(client, username="owner")
        upload = await client.post(
            "/api/v1/documents",
            json={"title": "mine.txt", "content": "Owner content"},
            headers=_auth_headers(token_a),
        )
        doc_id = upload.json()["id"]

        token_b = await _auth_token(client, username="attacker")
        response = await client.delete(
            f"/api/v1/documents/{doc_id}", headers=_auth_headers(token_b)
        )
        assert response.status_code == 404


class TestMemoryIntegration:
    async def test_uploaded_document_stored_in_memory(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Document content should be indexed into the memory store."""
        token = await _auth_token(client)
        await client.post(
            "/api/v1/documents",
            json={
                "title": "knowledge.txt",
                "content": "Important fact for retrieval",
            },
            headers=_auth_headers(token),
        )

        # Check memory was written
        memory = DatabaseMemoryStore(db)
        entries = await memory.retrieve(user_id=1, limit=50)
        # Should find at least one entry with document content
        doc_entries = [e for e in entries if "[Document: knowledge.txt]" in e.content]
        assert len(doc_entries) >= 1
        assert "Important fact for retrieval" in doc_entries[0].content

    async def test_large_document_chunked_in_memory(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Large documents should be split into chunks."""
        token = await _auth_token(client)
        # Create content larger than chunk size
        large_content = "A" * 2500
        await client.post(
            "/api/v1/documents",
            json={"title": "large.txt", "content": large_content},
            headers=_auth_headers(token),
        )

        memory = DatabaseMemoryStore(db)
        entries = await memory.retrieve(user_id=1, limit=50)
        doc_entries = [e for e in entries if "[Document: large.txt]" in e.content]
        # Should be chunked into multiple entries
        assert len(doc_entries) >= 2


class TestUtilities:
    def test_content_hash(self):
        h = _content_hash("hello world")
        assert len(h) == 64  # SHA-256 hex
        assert h == _content_hash("hello world")  # deterministic
        assert h != _content_hash("different")

    def test_chunk_text_short(self):
        chunks = _chunk_text("Short text", chunk_size=1000)
        assert chunks == ["Short text"]

    def test_chunk_text_large(self):
        text = "A" * 2500
        chunks = _chunk_text(text, chunk_size=1000, overlap=100)
        assert len(chunks) >= 3
        # Each chunk (except possibly last) should be chunk_size
        assert len(chunks[0]) == 1000
        # Verify overlap
        assert chunks[0][-100:] == chunks[1][:100]
