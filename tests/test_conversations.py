"""Tests for conversation management endpoints."""

from fastapi.testclient import TestClient


class TestConversations:
    def test_list_empty(self, client: TestClient, auth_headers):
        resp = client.get("/api/conversations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_conversation(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/conversations",
            headers=auth_headers,
            json={"title": "Test conversation"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test conversation"
        assert data["message_count"] == 0

    def test_get_conversation(self, client: TestClient, auth_headers):
        create_resp = client.post(
            "/api/conversations",
            headers=auth_headers,
            json={"title": "My chat"},
        )
        conv_id = create_resp.json()["id"]

        resp = client.get(f"/api/conversations/{conv_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "My chat"
        assert data["messages"] == []

    def test_delete_conversation(self, client: TestClient, auth_headers):
        create_resp = client.post(
            "/api/conversations",
            headers=auth_headers,
            json={"title": "To delete"},
        )
        conv_id = create_resp.json()["id"]

        resp = client.delete(f"/api/conversations/{conv_id}", headers=auth_headers)
        assert resp.status_code == 204

        resp = client.get(f"/api/conversations/{conv_id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_conversation_not_found(self, client: TestClient, auth_headers):
        resp = client.get("/api/conversations/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_conversation_isolation(self, client: TestClient):
        client.post("/api/auth/register", json={
            "email": "a@test.com", "username": "usera", "password": "password123",
        })
        resp_a = client.post("/api/auth/login", data={
            "username": "usera", "password": "password123",
        })
        headers_a = {"Authorization": f"Bearer {resp_a.json()['access_token']}"}

        client.post("/api/auth/register", json={
            "email": "b@test.com", "username": "userb", "password": "password123",
        })
        resp_b = client.post("/api/auth/login", data={
            "username": "userb", "password": "password123",
        })
        headers_b = {"Authorization": f"Bearer {resp_b.json()['access_token']}"}

        create_resp = client.post(
            "/api/conversations", headers=headers_a, json={"title": "Private"},
        )
        conv_id = create_resp.json()["id"]

        resp = client.get(f"/api/conversations/{conv_id}", headers=headers_b)
        assert resp.status_code == 404
