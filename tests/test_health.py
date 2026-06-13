"""Tests for root and health endpoints."""

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    def test_root(self, client: TestClient):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Multimodal RAG API"
        assert "version" in data

    def test_health(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_docs(self, client: TestClient):
        resp = client.get("/docs")
        assert resp.status_code == 200
