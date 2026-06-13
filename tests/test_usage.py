"""Tests for usage analytics endpoints."""

from fastapi.testclient import TestClient


class TestUsageEndpoints:
    def test_summary_empty(self, client: TestClient, auth_headers):
        resp = client.get("/api/usage/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_queries"] == 0
        assert data["total_cost_usd"] == 0.0

    def test_analytics_empty(self, client: TestClient, auth_headers):
        resp = client.get("/api/usage/analytics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_queries"] == 0
        assert data["daily_usage"] == []
        assert data["cost_by_operation"] == {}

    def test_analytics_custom_days(self, client: TestClient, auth_headers):
        resp = client.get("/api/usage/analytics?days=7", headers=auth_headers)
        assert resp.status_code == 200

    def test_usage_requires_auth(self, client: TestClient):
        resp = client.get("/api/usage/summary")
        assert resp.status_code == 401
