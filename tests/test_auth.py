"""Tests for authentication endpoints."""

from fastapi.testclient import TestClient


class TestRegister:
    def test_register_success(self, client: TestClient):
        resp = client.post("/api/auth/register", json={
            "email": "new@example.com",
            "username": "newuser",
            "password": "password123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert data["username"] == "newuser"
        assert "id" in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client: TestClient, registered_user):
        resp = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "username": "different",
            "password": "password123",
        })
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"]

    def test_register_duplicate_username(self, client: TestClient, registered_user):
        resp = client.post("/api/auth/register", json={
            "email": "different@example.com",
            "username": "testuser",
            "password": "password123",
        })
        assert resp.status_code == 400
        assert "already taken" in resp.json()["detail"]

    def test_register_weak_password(self, client: TestClient):
        resp = client.post("/api/auth/register", json={
            "email": "a@b.com",
            "username": "user",
            "password": "short",
        })
        assert resp.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        resp = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "username": "user",
            "password": "password123",
        })
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient, registered_user):
        resp = client.post("/api/auth/login", data={
            "username": "testuser",
            "password": "securepassword123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, registered_user):
        resp = client.post("/api/auth/login", data={
            "username": "testuser",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        resp = client.post("/api/auth/login", data={
            "username": "nobody",
            "password": "password123",
        })
        assert resp.status_code == 401


class TestMe:
    def test_get_me_authenticated(self, client: TestClient, auth_headers):
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_get_me_unauthenticated(self, client: TestClient):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401
