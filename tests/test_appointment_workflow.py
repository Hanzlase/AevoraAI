"""Tests for progressive appointment intake state machine and workflow transitions."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import create_app

# Isolated in-memory SQLite database for test suite
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
    with TestClient(app) as test_client:
        yield test_client


def test_appointment_multi_turn_intake(client):
    # Turn 1: Start booking
    res1 = client.post(
        "/api/v1/chat",
        json={"message": "I would like to book an appointment with Dr. Farhan"},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    conv_id = data1["conversation_id"]
    assert data1["workflow"] == "appointment_intake"
    assert data1["workflow_status"] == "in_progress"
    # Should ask for patient name
    assert "name" in data1["response"].lower()

    # Turn 2: Provide patient name
    res2 = client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "The patient is Bilal Tariq"},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["workflow"] == "appointment_intake"
    # Should ask for date
    assert "date" in data2["response"].lower() or "day" in data2["response"].lower()

    # Turn 3: Provide preferred date
    res3 = client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "Tomorrow Friday"},
    )
    assert res3.status_code == 200
    data3 = res3.json()
    # Should ask for time
    assert "time" in data3["response"].lower()

    # Turn 4: Provide preferred time
    res4 = client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "5:30 PM in the evening"},
    )
    assert res4.status_code == 200
    data4 = res4.json()
    # Should ask for contact phone number
    assert "phone" in data4["response"].lower() or "number" in data4["response"].lower()

    # Turn 5: Provide phone number
    res5 = client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "03001234567"},
    )
    assert res5.status_code == 200
    data5 = res5.json()
    assert data5["workflow_status"] == "awaiting_confirmation"
    assert "Bilal Tariq" in data5["response"]
    assert "Dr. Farhan" in data5["response"]
    assert "03001234567" in data5["response"]
    assert "confirm" in data5["response"].lower() or "yes" in data5["response"].lower()

    # Turn 6: Confirm appointment request
    res6 = client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "Yes, please confirm"},
    )
    assert res6.status_code == 200
    data6 = res6.json()
    assert data6["workflow_status"] == "confirmed"
    assert "Pending Staff Confirmation" in data6["response"]
    assert data6["appointment_id"] is not None

    # Check staff appointment endpoint
    staff_res = client.get("/api/v1/staff/appointments")
    assert staff_res.status_code == 200
    appts = staff_res.json()
    assert len(appts) == 1
    assert (
        appts[0]["patient_name"] == "The patient is Bilal Tariq"
        or "Bilal Tariq" in appts[0]["patient_name"]
    )
    assert appts[0]["status"] == "pending_staff_confirmation"
    assert "booked" not in appts[0]["status"]


def test_appointment_intake_cancellation(client):
    # Turn 1: Start booking
    res1 = client.post(
        "/api/v1/chat",
        json={"message": "I need to schedule a consultation"},
    )
    conv_id = res1.json()["conversation_id"]

    # Provide name
    client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "Ayesha Ahmed"},
    )

    # Now cancel
    res_cancel = client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "Cancel this request"},
    )
    assert res_cancel.status_code == 200
    data_cancel = res_cancel.json()
    assert data_cancel["workflow_status"] == "cancelled"
    assert "cancelled" in data_cancel["response"].lower()
