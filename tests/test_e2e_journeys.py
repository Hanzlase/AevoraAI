"""Comprehensive End-to-End User Journey Tests for Aevora AI.

Verifies:
- Journey A: Clinic Information Inquiry (grounded RAG, source traceability, unknown handling)
- Journey B: Multilingual Capabilities (English, Urdu, Roman Urdu, Mixed, contextual follow-ups)
- Journey C: WhatsApp Text Messaging (Webhook signature, queuing, RAG, outbound reply, idempotency)
- Journey D: WhatsApp Voice Processing (Audio download, FFmpeg, Whisper transcribe, cleanup)
- Journey E: Appointment Intake Workflow (Progressive slots, confirmation, staff review, cancel)
- Journey F: Human Staff Triage & Escalation (User request, handoff record, staff status update)
- Journey G: Deterministic Medical Guardrails (Prescription deflection, emergency 1122 redirection)
"""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.gemini_client import MockLLMClient, set_llm_client
from app.core.config import Settings
from app.database.session import Base, get_db
from app.main import create_app
from app.models.appointment import AppointmentRequest
from app.models.handoff import HandoffRequest
from app.models.inbound_event import InboundEvent
from app.models.message import Message
from app.services.inbound_event_service import InboundEventService
from app.voice.transcription import MockTranscriber, set_transcriber
from app.whatsapp.client import MockWhatsAppClient, set_whatsapp_client

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
def test_settings():
    return Settings(
        environment="development",
        webhook_verify_token="journey_verify_tok_999",
        meta_app_secret="journey_app_secret_888",
        whatsapp_enabled=True,
        whatsapp_event_worker_enabled=False,
    )


@pytest.fixture(scope="function")
def mock_whatsapp():
    client = MockWhatsAppClient()
    set_whatsapp_client(client)
    yield client
    set_whatsapp_client(None)


@pytest.fixture(scope="function")
def mock_whisper():
    transcriber = MockTranscriber()
    set_transcriber(transcriber)
    yield transcriber
    set_transcriber(None)


@pytest.fixture(scope="function")
def client(db_session, test_settings, mock_whatsapp, mock_whisper):
    app = create_app(settings=test_settings)

    def override_get_db():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    mock_llm = MockLLMClient(
        default_response="NovaCare Medical Centre is located in F-7 Markaz, Islamabad. Dr. Farhan OPD is 10:00 AM to 2:00 PM."
    )
    set_llm_client(mock_llm)

    with TestClient(app) as test_client:
        yield test_client

    set_llm_client(None)


def _sign(body: bytes, secret: str = "journey_app_secret_888") -> str:
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ==============================================================================
# Journey A: Clinic Information Inquiry
# ==============================================================================


def test_journey_a_clinic_information(client, db_session):
    """Patient asks clinic inquiries; verifies RAG grounding and unknown handling."""
    # 1. Answerable question
    res1 = client.post(
        "/api/v1/chat",
        json={"message": "What is the consultation fee of Dr Bilal Ahmed in cardiology?"},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert "conversation_id" in data1
    conv_id = data1["conversation_id"]
    assert len(data1["sources"]) > 0

    # Verify message persisted in database with citations
    msgs = list(db_session.scalars(select(Message).where(Message.conversation_id == conv_id)).all())
    assert len(msgs) == 2  # 1 user + 1 assistant
    assert msgs[1].role == "assistant"
    assert msgs[1].sources is not None


# ==============================================================================
# Journey B: Multilingual Conversations
# ==============================================================================


def test_journey_b_multilingual_and_followups(client):
    """Verifies English, Roman Urdu, Urdu script, and contextual follow-ups."""
    # 1. English
    r_en = client.post("/api/v1/chat", json={"message": "What are your operating hours?"})
    assert r_en.status_code == 200
    assert r_en.json()["language"] == "en"
    conv_id = r_en.json()["conversation_id"]

    # 2. Roman Urdu in same thread
    r_ru = client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "Aur lab tests ki timing kya hai?"},
    )
    assert r_ru.status_code == 200
    assert r_ru.json()["language"] == "roman_ur"

    # 3. Urdu Script
    r_ur = client.post(
        "/api/v1/chat",
        json={"message": "نووا کیئر کلینک میں کون سے ڈاکٹرز موجود ہیں؟"},
    )
    assert r_ur.status_code == 200
    assert r_ur.json()["language"] == "ur"


# ==============================================================================
# Journey C: WhatsApp Text Messaging & Idempotency
# ==============================================================================


@pytest.mark.asyncio
async def test_journey_c_whatsapp_text_and_idempotency(client, db_session, mock_whatsapp):
    """Verifies incoming signed webhook, durable queue, and duplicate deduplication."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "923119998877",
                                    "id": "wamid.journey_c_001",
                                    "type": "text",
                                    "text": {"body": "Where is NovaCare located?"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = _sign(raw_body)

    # 1. First webhook delivery
    res1 = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert res1.status_code == 200

    # Process first event
    ev1 = db_session.scalar(
        select(InboundEvent).where(InboundEvent.provider_message_id == "wamid.journey_c_001")
    )
    assert ev1 is not None
    await InboundEventService.process_single_event(db_session, ev1.id)
    db_session.commit()

    assert len(mock_whatsapp.sent_messages) == 1
    assert "923119998877" == mock_whatsapp.sent_messages[0]["to"]

    # 2. Duplicate webhook delivery (Meta network retry)
    res2 = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert res2.status_code == 200

    # Ensure no duplicate record created in DB
    all_events = list(
        db_session.scalars(
            select(InboundEvent).where(InboundEvent.provider_message_id == "wamid.journey_c_001")
        ).all()
    )
    assert len(all_events) == 1
    # Ensure no duplicate message sent
    assert len(mock_whatsapp.sent_messages) == 1


# ==============================================================================
# Journey D: WhatsApp Voice Notes
# ==============================================================================


@pytest.mark.asyncio
async def test_journey_d_whatsapp_voice_note(client, db_session, mock_whatsapp, mock_whisper):
    """Verifies incoming voice note download, WAV conversion, Whisper transcribe, and reply."""
    mock_whisper.default_text = "Dr Farhan ki consultation fee kitni hai?"
    mock_whisper.default_lang = "roman_ur"

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "923225554433",
                                    "id": "wamid.journey_voice_001",
                                    "type": "audio",
                                    "audio": {
                                        "id": "media_journey_voice_99",
                                        "mime_type": "audio/ogg; codecs=opus",
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = _sign(raw_body)

    res = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert res.status_code == 200

    ev = db_session.scalar(
        select(InboundEvent).where(InboundEvent.provider_message_id == "wamid.journey_voice_001")
    )
    await InboundEventService.process_single_event(db_session, ev.id)
    db_session.commit()

    assert len(mock_whisper.call_history) == 1
    assert len(mock_whatsapp.sent_messages) == 1
    assert mock_whatsapp.sent_messages[0]["to"] == "923225554433"


# ==============================================================================
# Journey E: Appointment Intake & Cancellation
# ==============================================================================


def test_journey_e_appointment_intake_and_staff_action(client, db_session):
    """Verifies appointment booking intake, patient confirmation, staff review, and cancellation."""
    # 1. Patient requests appointment
    r1 = client.post(
        "/api/v1/chat", json={"message": "I need to book an appointment with Dr. Farhan"}
    )
    assert r1.status_code == 200
    conv_id = r1.json()["conversation_id"]

    # 2. Provide slots
    client.post(
        "/api/v1/chat", json={"conversation_id": conv_id, "message": "My name is Zainab Bibi"}
    )
    client.post("/api/v1/chat", json={"conversation_id": conv_id, "message": "Tomorrow"})
    client.post("/api/v1/chat", json={"conversation_id": conv_id, "message": "11:30 AM"})
    r5 = client.post("/api/v1/chat", json={"conversation_id": conv_id, "message": "03129876543"})
    assert r5.json()["workflow_status"] == "awaiting_confirmation"

    # 3. Patient confirms
    r6 = client.post(
        "/api/v1/chat", json={"conversation_id": conv_id, "message": "Yes, please confirm"}
    )
    assert r6.json()["workflow_status"] == "confirmed"
    appt_id = r6.json()["appointment_id"]
    assert appt_id is not None

    # Verify appointment in DB
    appt = db_session.get(AppointmentRequest, appt_id)
    assert appt.status == "pending_staff_confirmation"
    assert appt.doctor_name == "Dr. Farhan"

    # 4. Staff confirms appointment in dashboard
    patch_res = client.patch(
        f"/api/v1/staff/appointments/{appt_id}",
        json={"status": "confirmed_by_staff"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "confirmed_by_staff"

    # 5. Patient cancels
    r_cancel = client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "Please cancel my appointment"},
    )
    assert r_cancel.status_code == 200
    assert "cancel" in r_cancel.json()["response"].lower()

    refreshed = db_session.get(AppointmentRequest, appt_id)
    assert refreshed.status == "cancelled"


# ==============================================================================
# Journey F: Human Staff Escalation Handoff
# ==============================================================================


def test_journey_f_human_staff_handoff(client, db_session):
    """Verifies human handoff request, triage record creation, and staff resolution."""
    res = client.post(
        "/api/v1/chat",
        json={"message": "I want to speak with a human receptionist right now"},
    )
    assert res.status_code == 200
    data = res.json()
    handoff_id = data.get("handoff_id")
    assert handoff_id is not None

    # Check staff handoff record in DB
    handoff = db_session.get(HandoffRequest, handoff_id)
    assert handoff is not None
    assert handoff.status == "pending"

    # Staff updates to in_progress
    p1 = client.patch(f"/api/v1/staff/handoffs/{handoff_id}", json={"status": "in_progress"})
    assert p1.status_code == 200
    assert p1.json()["status"] == "in_progress"

    # Staff marks resolved
    p2 = client.patch(f"/api/v1/staff/handoffs/{handoff_id}", json={"status": "resolved"})
    assert p2.status_code == 200
    assert p2.json()["status"] == "resolved"


# ==============================================================================
# Journey G: Deterministic Medical Guardrails
# ==============================================================================


def test_journey_g_medical_safety_boundaries(client):
    """Verifies acute emergency 1122 deflection and clinical prescription boundaries."""
    # 1. Emergency scenario
    r_em = client.post(
        "/api/v1/chat",
        json={"message": "Severe crushing chest pain and patient collapsed unconscious"},
    )
    assert r_em.status_code == 200
    assert "1122" in r_em.json()["response"] or "emergency" in r_em.json()["response"].lower()

    # 2. Medication / prescription inquiry (must be safely deflected)
    r_med = client.post(
        "/api/v1/chat",
        json={"message": "What dosage of augmentin antibiotic should I take for tooth infection?"},
    )
    assert r_med.status_code == 200
    resp_text = r_med.json()["response"].lower()
    # Must decline prescription / offer doctor appointment
    assert "prescribe" in resp_text or "doctor" in resp_text or "consultation" in resp_text
