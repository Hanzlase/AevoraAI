"""Tests for multilingual chat conversations across English, Urdu script, and Roman Urdu."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.gemini_client import MockLLMClient, set_llm_client
from app.database.session import Base, get_db
from app.main import create_app

engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine_test)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def client(db_session):
    app = create_app()

    def override_get_db():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    mock_llm = MockLLMClient(
        default_response="NovaCare Medical Centre me khushamdeed! Timings Monday to Saturday 9am to 8pm hain."
    )
    set_llm_client(mock_llm)

    with TestClient(app) as test_client:
        yield test_client

    set_llm_client(None)


def test_english_query_flow(client):
    res = client.post(
        "/api/v1/chat",
        json={"message": "What is the consultation fee for cardiology at NovaCare?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "en"
    assert len(data["sources"]) > 0
    assert any(
        s["category"] in ("doctor", "service", "clinic_info")
        or "cardiology" in s["section"].lower()
        or "doctor" in s["section"].lower()
        for s in data["sources"]
    )


def test_urdu_script_query_flow(client):
    res = client.post(
        "/api/v1/chat",
        json={"message": "کلینک کے کھلنے کے اوقات کیا ہیں؟"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "ur"
    assert len(data["sources"]) > 0


def test_roman_urdu_query_flow(client):
    res = client.post(
        "/api/v1/chat",
        json={"message": "Dr Farhan ki appointment ki fees kitni hai aur clinic kab khulta hai?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["language"] in ("roman_ur", "mixed")
    assert len(data["sources"]) > 0


def test_mixed_language_query_flow(client):
    res = client.post(
        "/api/v1/chat",
        json={"message": "Cardiologist Dr Farhan ki availability aur consultation fee kya hai?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["language"] in ("roman_ur", "mixed")
    assert len(data["sources"]) > 0
