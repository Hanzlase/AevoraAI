"""Tests for Staff Dashboard APIs, authentication, authorization, and static assets."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import create_access_token, hash_password
from app.core.config import Settings
from app.database.session import Base, get_db
from app.main import create_app
from app.models.appointment import AppointmentRequest
from app.models.conversation import Conversation
from app.models.handoff import HandoffRequest
from app.models.message import Message
from app.models.user import StaffUser

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
        # Seed test admin user
        h, s = hash_password("NovaCare2026!")
        admin = StaffUser(
            username="admin",
            hashed_password=h,
            salt=s,
            full_name="Dr. Administrator",
            role="admin",
            is_active=True,
        )
        session.add(admin)
        session.commit()
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def test_settings():
    return Settings(
        environment="development",
        staff_jwt_secret="test_secret_for_staff_dashboard_tests_2026",
    )


@pytest.fixture(scope="function")
def client(db_session, test_settings):
    app = create_app(settings=test_settings)

    def override_get_db():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def test_staff_login_success(client):
    res = client.post(
        "/api/v1/staff/auth/login",
        json={"username": "admin", "password": "NovaCare2026!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == "admin"


def test_staff_login_invalid_password(client):
    res = client.post(
        "/api/v1/staff/auth/login",
        json={"username": "admin", "password": "WrongPassword!"},
    )
    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]


def test_staff_login_nonexistent_user(client):
    res = client.post(
        "/api/v1/staff/auth/login",
        json={"username": "ghost_user", "password": "AnyPassword"},
    )
    assert res.status_code == 401


def test_staff_auth_me_profile(client, db_session, test_settings):
    admin = db_session.query(StaffUser).filter_by(username="admin").first()
    token = create_access_token(admin, test_settings)

    res = client.get(
        "/api/v1/staff/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"


def test_staff_overview_metrics(client, db_session, test_settings):
    admin = db_session.query(StaffUser).filter_by(username="admin").first()
    token = create_access_token(admin, test_settings)

    # Insert sample conversation, appointment, and handoff
    conv = Conversation(channel="whatsapp", external_user_id="923001234567")
    db_session.add(conv)
    db_session.flush()

    appt = AppointmentRequest(
        conversation_id=conv.id,
        patient_name="Hamza Tariq",
        preferred_date="Tomorrow",
        preferred_time="10:00 AM",
        status="pending_staff_confirmation",
    )
    db_session.add(appt)

    handoff = HandoffRequest(
        conversation_id=conv.id,
        reason="user_requested",
        summary="Patient needs help",
        status="pending",
    )
    db_session.add(handoff)
    db_session.commit()

    res = client.get(
        "/api/v1/staff/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_conversations"] >= 1
    assert data["pending_appointments"] >= 1
    assert data["pending_handoffs"] >= 1


def test_staff_conversation_list_and_detail(client, db_session, test_settings):
    admin = db_session.query(StaffUser).filter_by(username="admin").first()
    token = create_access_token(admin, test_settings)

    conv = Conversation(channel="whatsapp", external_user_id="923009998877")
    db_session.add(conv)
    db_session.flush()

    msg1 = Message(
        conversation_id=conv.id,
        role="user",
        content="Dr Farhan ki timing kya hai?",
        language="roman_ur",
    )
    msg2 = Message(
        conversation_id=conv.id,
        role="assistant",
        content="Dr. Farhan clinic mein 10 AM to 2 PM available hotay hain.",
        language="roman_ur",
        sources=[
            {
                "entity_id": "DOC-001",
                "category": "doctor",
                "section": "Doctors",
                "provenance": "json",
            }
        ],
    )
    db_session.add_all([msg1, msg2])
    db_session.commit()

    # List conversations
    res_list = client.get(
        "/api/v1/staff/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) >= 1
    found = next((c for c in items if c["id"] == conv.id), None)
    assert found is not None
    assert found["channel"] == "whatsapp"
    assert found["message_count"] == 2

    # Get conversation detail
    res_det = client.get(
        f"/api/v1/staff/conversations/{conv.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_det.status_code == 200
    detail = res_det.json()
    assert len(detail["messages"]) == 2
    assert detail["messages"][1]["sources"][0]["entity_id"] == "DOC-001"


def test_staff_update_appointment_status(client, db_session, test_settings):
    admin = db_session.query(StaffUser).filter_by(username="admin").first()
    token = create_access_token(admin, test_settings)

    conv = Conversation(channel="web", external_user_id="anonymous")
    db_session.add(conv)
    db_session.flush()

    appt = AppointmentRequest(
        conversation_id=conv.id,
        patient_name="Sana Bilal",
        preferred_date="Monday",
        preferred_time="4:00 PM",
        status="pending_staff_confirmation",
    )
    db_session.add(appt)
    db_session.commit()

    # Confirm appointment
    patch_res = client.patch(
        f"/api/v1/staff/appointments/{appt.id}",
        json={"status": "confirmed_by_staff"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "confirmed_by_staff"

    # Verify in DB
    refreshed = db_session.get(AppointmentRequest, appt.id)
    assert refreshed.status == "confirmed_by_staff"


def test_staff_update_appointment_invalid_status(client, db_session, test_settings):
    admin = db_session.query(StaffUser).filter_by(username="admin").first()
    token = create_access_token(admin, test_settings)

    conv = Conversation(channel="web", external_user_id="anonymous")
    db_session.add(conv)
    db_session.flush()

    appt = AppointmentRequest(
        conversation_id=conv.id,
        patient_name="Test Patient",
        preferred_date="Tomorrow",
        preferred_time="11:00 AM",
        status="pending_staff_confirmation",
    )
    db_session.add(appt)
    db_session.commit()

    res = client.patch(
        f"/api/v1/staff/appointments/{appt.id}",
        json={"status": "invalid_bogus_status"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400


def test_staff_system_and_kb_status(client, db_session, test_settings):
    admin = db_session.query(StaffUser).filter_by(username="admin").first()
    token = create_access_token(admin, test_settings)

    kb_res = client.get(
        "/api/v1/staff/knowledge-base/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert kb_res.status_code == 200
    kb_data = kb_res.json()
    assert "index_ready" in kb_data

    sys_res = client.get(
        "/api/v1/staff/system/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sys_res.status_code == 200
    sys_data = sys_res.json()
    assert sys_data["fastapi_status"] == "Operational"


def test_dashboard_static_files_and_redirect(client):
    # Root redirects to /dashboard
    root_res = client.get("/", follow_redirects=False)
    assert root_res.status_code in (302, 307)
    assert root_res.headers["location"] == "/dashboard"

    # Dashboard index HTML
    dash_res = client.get("/dashboard/")
    assert dash_res.status_code == 200
    assert "Aevora AI" in dash_res.text
    assert "NovaCare" in dash_res.text

    # Dashboard CSS
    css_res = client.get("/dashboard/styles.css")
    assert css_res.status_code == 200
    assert "#142B3A" in css_res.text
    assert "#126E75" in css_res.text
