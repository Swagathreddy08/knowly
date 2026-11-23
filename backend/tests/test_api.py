import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register(client: TestClient, tenant: str = "Acme"):
    response = client.post(
        "/auth/register",
        json={
            "tenant_name": tenant,
            "email": f"{tenant.lower()}@example.com",
            "password": "a-secure-password",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_registration_and_login(client):
    registered = register(client)
    response = client.post(
        "/auth/login",
        json={
            "tenant_id": registered["tenant_id"],
            "email": "acme@example.com",
            "password": "a-secure-password",
        },
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_document_list_is_tenant_isolated(client):
    first = register(client, "First")
    second = register(client, "Second")

    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}

    first_upload = client.post(
        "/documents",
        headers=first_headers,
        files={"file": ("notes.txt", b"Confidential first tenant content", "text/plain")},
    )
    assert first_upload.status_code == 202

    response = client.get("/documents", headers=second_headers)
    assert response.status_code == 200
    assert response.json() == []
