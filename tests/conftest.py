"""Shared test fixtures — in-memory SQLite, test client, auth helpers."""

import os
from collections.abc import Generator

os.environ["OPENAI_API_KEY"] = "sk-test-not-a-real-key"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_db
from app.db.models import Base
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client: TestClient) -> dict:
    payload = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepassword123",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
def auth_headers(client: TestClient, registered_user: dict) -> dict:
    resp = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "securepassword123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
