"""Tests for chat endpoints (mocked OpenAI calls)."""

from fastapi.testclient import TestClient


class TestChatQuery:
    def test_query_no_documents(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/chat/query",
            headers=auth_headers,
            json={"query": "What is this about?"},
        )
        assert resp.status_code == 400
        assert "No processed documents" in resp.json()["detail"]

    def test_query_invalid_document_ids(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/chat/query",
            headers=auth_headers,
            json={"query": "Tell me about this", "document_ids": [99999]},
        )
        assert resp.status_code == 400

    def test_query_requires_auth(self, client: TestClient):
        resp = client.post("/api/chat/query", json={"query": "hello"})
        assert resp.status_code == 401

    def test_query_empty_string(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/chat/query",
            headers=auth_headers,
            json={"query": ""},
        )
        assert resp.status_code == 422
