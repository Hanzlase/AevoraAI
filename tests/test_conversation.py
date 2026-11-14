"""Tests for conversation sessions, history persistence, deletion, and handoffs."""

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

    # Inject Mock LLM client to ensure tests run offline deterministically
    mock_llm = MockLLMClient(
        default_response="NovaCare Medical Centre clinic timings are Monday to Saturday, 9:00 AM to 8:00 PM."
    )
    set_llm_client(mock_llm)

    with TestClient(app) as test_client:
        yield test_client

    set_llm_client(None)


def test_chat_creates_conversation_and_returns_sources(client):
    res = client.post(
        "/api/v1/chat",
        json={"message": "What are the clinic opening hours?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "conversation_id" in data
    assert len(data["conversation_id"]) > 0
    assert "NovaCare" in data["response"]
    assert len(data["sources"]) > 0
    assert any(
        s["category"] in ("timings", "general_info", "faq")
        or "timings" in s["section"].lower()
        or "hours" in s["section"].lower()
        for s in data["sources"]
    )


def test_session_isolation_and_history(client):
    # Session A
    res_a = client.post(
        "/api/v1/chat",
        json={"message": "What is the fee for Dr. Farhan?"},
    )
    conv_a = res_a.json()["conversation_id"]

    # Session B
    res_b = client.post(
        "/api/v1/chat",
        json={"message": "Where is the laboratory located?"},
    )
    conv_b = res_b.json()["conversation_id"]

    assert conv_a != conv_b

    # Verify history of Session A
    hist_a = client.get(f"/api/v1/chat/{conv_a}/history")
    assert hist_a.status_code == 200
    msgs_a = hist_a.json()["messages"]
    assert len(msgs_a) == 2  # user + assistant
    assert msgs_a[0]["role"] == "user"
    assert "Dr. Farhan" in msgs_a[0]["content"]
    assert msgs_a[1]["role"] == "assistant"

    # Verify history of Session B
    hist_b = client.get(f"/api/v1/chat/{conv_b}/history")
    assert hist_b.status_code == 200
    msgs_b = hist_b.json()["messages"]
    assert len(msgs_b) == 2
    assert "laboratory" in msgs_b[0]["content"]


def test_delete_conversation(client):
    res = client.post(
        "/api/v1/chat",
        json={"message": "Hello NovaCare"},
    )
    conv_id = res.json()["conversation_id"]

    # Delete
    del_res = client.delete(f"/api/v1/chat/{conv_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify 404 after deletion
    hist_res = client.get(f"/api/v1/chat/{conv_id}/history")
    assert hist_res.status_code == 404


def test_staff_handoff_lifecycle(client):
    # User requests human staff
    res = client.post(
        "/api/v1/chat",
        json={"message": "I need to talk to a human receptionist please"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["handoff_id"] is not None
    handoff_id = data["handoff_id"]

    # Check staff endpoint lists the handoff
    list_res = client.get("/api/v1/staff/handoffs?status=pending")
    assert list_res.status_code == 200
    handoffs = list_res.json()
    assert len(handoffs) >= 1
    assert any(h["id"] == handoff_id for h in handoffs)

    # Update handoff status to in_progress
    patch_res = client.patch(
        f"/api/v1/staff/handoffs/{handoff_id}",
        json={"status": "in_progress"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "in_progress"
