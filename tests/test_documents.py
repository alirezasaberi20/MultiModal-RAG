"""Tests for document management endpoints."""

import io

from fastapi.testclient import TestClient


class TestUpload:
    def test_upload_pdf(self, client: TestClient, auth_headers):
        pdf_bytes = b"%PDF-1.4 minimal test content"
        resp = client.post(
            "/api/documents/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["original_name"] == "test.pdf"
        assert data["status"] == "pending"

    def test_upload_non_pdf(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/documents/upload",
            headers=auth_headers,
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]

    def test_upload_empty_file(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/documents/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", io.BytesIO(b""), "application/pdf")},
        )
        assert resp.status_code == 400
        assert "Empty" in resp.json()["detail"]

    def test_upload_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )
        assert resp.status_code == 401


class TestListDocuments:
    def test_list_empty(self, client: TestClient, auth_headers):
        resp = client.get("/api/documents", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_upload(self, client: TestClient, auth_headers):
        client.post(
            "/api/documents/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")},
        )
        resp = client.get("/api/documents", headers=auth_headers)
        assert resp.status_code == 200
        docs = resp.json()
        assert len(docs) == 1
        assert docs[0]["original_name"] == "test.pdf"


class TestUserIsolation:
    def test_users_cannot_see_each_others_docs(self, client: TestClient):
        client.post("/api/auth/register", json={
            "email": "user1@test.com", "username": "user1", "password": "password123",
        })
        resp1 = client.post("/api/auth/login", data={
            "username": "user1", "password": "password123",
        })
        headers1 = {"Authorization": f"Bearer {resp1.json()['access_token']}"}

        client.post("/api/auth/register", json={
            "email": "user2@test.com", "username": "user2", "password": "password123",
        })
        resp2 = client.post("/api/auth/login", data={
            "username": "user2", "password": "password123",
        })
        headers2 = {"Authorization": f"Bearer {resp2.json()['access_token']}"}

        client.post(
            "/api/documents/upload",
            headers=headers1,
            files={"file": ("user1.pdf", io.BytesIO(b"%PDF-1.4 user1"), "application/pdf")},
        )

        user2_docs = client.get("/api/documents", headers=headers2).json()
        assert len(user2_docs) == 0

        user1_docs = client.get("/api/documents", headers=headers1).json()
        assert len(user1_docs) == 1
