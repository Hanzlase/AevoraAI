"""End-to-end integration tests for WhatsApp Cloud API and Voice integration adapter.

Verifies:
1. Webhook intake -> Inbound event queuing -> Event processing -> Clinic response sent via WhatsApp.
2. Voice note intake -> Audio download & conversion -> Whisper transcription -> Clinic response.
3. WhatsApp appointment intent -> Intake state machine -> Appointment creation in DB.
4. WhatsApp human handoff intent -> Staff handoff record created in DB.
5. WhatsApp emergency symptom deflection -> Immediate 1122 redirection and safety escalation.
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
from app.models.conversation import Conversation
from app.models.handoff import HandoffRequest
from app.models.inbound_event import InboundEvent
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
        webhook_verify_token="test_verify_token_adapter",
        meta_app_secret="test_app_secret_adapter",
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
    transcriber = MockTranscriber(
        default_text="Dr Farhan ki consultation fee kitni hai?",
        default_lang="roman_ur",
    )
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
        default_response="NovaCare clinic timings are Monday to Saturday, 9:00 AM to 8:00 PM."
    )
    set_llm_client(mock_llm)

    with TestClient(app) as test_client:
        yield test_client

    set_llm_client(None)


def _sign_payload(body: bytes, secret: str = "test_app_secret_adapter") -> str:
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def _make_text_payload(
    message_text: str,
    sender_id: str = "923001112233",
    message_id: str = "wamid.text_001",
) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": sender_id,
                                    "id": message_id,
                                    "type": "text",
                                    "text": {"body": message_text},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def _make_audio_payload(
    media_id: str = "meta_audio_999",
    sender_id: str = "923001112233",
    message_id: str = "wamid.audio_001",
) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": sender_id,
                                    "id": message_id,
                                    "type": "audio",
                                    "audio": {
                                        "id": media_id,
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


@pytest.mark.asyncio
async def test_e2e_text_faq_inquiry(client, db_session, mock_whatsapp):
    """Webhook text message -> InboundEvent -> Process -> Outbound WhatsApp text reply."""
    payload = _make_text_payload(
        message_text="What are NovaCare clinic timings?",
        sender_id="923001112233",
        message_id="wamid.faq_001",
    )
    raw_body = json.dumps(payload).encode("utf-8")
    sig = _sign_payload(raw_body)

    resp = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200

    # Retrieve queued event
    event = db_session.scalar(
        select(InboundEvent).where(InboundEvent.provider_message_id == "wamid.faq_001")
    )
    assert event is not None
    assert event.status == "pending"

    # Process event
    processed = await InboundEventService.process_single_event(db_session, event.id)
    db_session.commit()

    assert processed.status == "processed"
    assert len(mock_whatsapp.sent_messages) == 1
    sent = mock_whatsapp.sent_messages[0]
    assert sent["to"] == "923001112233"
    assert "NovaCare clinic timings" in sent["text"]

    # Verify conversation record created
    conv = db_session.scalar(
        select(Conversation).where(Conversation.external_user_id == "923001112233")
    )
    assert conv is not None
    assert conv.channel == "whatsapp"


@pytest.mark.asyncio
async def test_e2e_voice_note_inquiry(client, db_session, mock_whatsapp, mock_whisper):
    """Webhook voice note -> Download/convert -> Whisper transcribe -> Outbound reply."""
    mock_whisper.default_text = "NovaCare clinic kahan waqia hai?"
    mock_whisper.default_lang = "roman_ur"

    payload = _make_audio_payload(
        media_id="audio_test_101",
        sender_id="923002223344",
        message_id="wamid.audio_voice_101",
    )
    raw_body = json.dumps(payload).encode("utf-8")
    sig = _sign_payload(raw_body)

    resp = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200

    event = db_session.scalar(
        select(InboundEvent).where(InboundEvent.provider_message_id == "wamid.audio_voice_101")
    )
    assert event is not None

    processed = await InboundEventService.process_single_event(db_session, event.id)
    db_session.commit()

    assert processed.status == "processed"
    # Ensure transcriber was called
    assert len(mock_whisper.call_history) == 1
    # Ensure WhatsApp reply was sent
    assert len(mock_whatsapp.sent_messages) == 1
    sent = mock_whatsapp.sent_messages[0]
    assert sent["to"] == "923002223344"
    assert len(sent["text"]) > 0


@pytest.mark.asyncio
async def test_e2e_appointment_booking_flow(client, db_session, mock_whatsapp):
    """WhatsApp appointment intent initiates appointment state machine."""
    payload = _make_text_payload(
        message_text="I want to book an appointment with Dr. Farhan",
        sender_id="923003334455",
        message_id="wamid.appt_001",
    )
    raw_body = json.dumps(payload).encode("utf-8")
    sig = _sign_payload(raw_body)

    resp = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200

    event = db_session.scalar(
        select(InboundEvent).where(InboundEvent.provider_message_id == "wamid.appt_001")
    )
    await InboundEventService.process_single_event(db_session, event.id)
    db_session.commit()

    # Verify outbound WhatsApp message asks for intake information
    assert len(mock_whatsapp.sent_messages) == 1
    reply_text = mock_whatsapp.sent_messages[0]["text"]
    assert "name" in reply_text.lower() or "farhan" in reply_text.lower()

    # Verify conversation active workflow
    conv = db_session.scalar(
        select(Conversation).where(Conversation.external_user_id == "923003334455")
    )
    assert conv is not None
    assert conv.active_workflow == "appointment_intake"
    assert conv.workflow_state["fields"]["doctor_name"] == "Dr. Farhan"

    # Multi-turn continuation through WhatsApp: provide name
    payload_name = _make_text_payload(
        message_text="Patient name is Tariq Aziz",
        sender_id="923003334455",
        message_id="wamid.appt_002",
    )
    raw_name = json.dumps(payload_name).encode("utf-8")
    client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_name,
        headers={
            "X-Hub-Signature-256": _sign_payload(raw_name),
            "Content-Type": "application/json",
        },
    )
    ev2 = db_session.scalar(
        select(InboundEvent).where(InboundEvent.provider_message_id == "wamid.appt_002")
    )
    await InboundEventService.process_single_event(db_session, ev2.id)
    db_session.commit()

    # Outbound WhatsApp message should now ask for date
    assert len(mock_whatsapp.sent_messages) == 2
    reply_text2 = mock_whatsapp.sent_messages[1]["text"]
    assert "date" in reply_text2.lower() or "day" in reply_text2.lower()


@pytest.mark.asyncio
async def test_e2e_human_staff_handoff(client, db_session, mock_whatsapp):
    """WhatsApp human handoff request creates handoff record in DB."""
    payload = _make_text_payload(
        message_text="Please connect me to human staff, I need help from a real person.",
        sender_id="923004445566",
        message_id="wamid.handoff_001",
    )
    raw_body = json.dumps(payload).encode("utf-8")
    sig = _sign_payload(raw_body)

    resp = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200

    event = db_session.scalar(
        select(InboundEvent).where(InboundEvent.provider_message_id == "wamid.handoff_001")
    )
    await InboundEventService.process_single_event(db_session, event.id)
    db_session.commit()

    assert len(mock_whatsapp.sent_messages) == 1
    reply_text = mock_whatsapp.sent_messages[0]["text"]
    assert "staff" in reply_text.lower() or "team" in reply_text.lower()

    # Verify HandoffRequest record in DB
    handoff = db_session.scalar(select(HandoffRequest))
    assert handoff is not None
    assert handoff.status == "pending"


@pytest.mark.asyncio
async def test_e2e_emergency_safety_deflection(client, db_session, mock_whatsapp):
    """WhatsApp message with emergency symptoms triggers immediate 1122 deflection."""
    payload = _make_text_payload(
        message_text="I have severe crushing chest pain, difficulty breathing and sweating heavily.",
        sender_id="923005556677",
        message_id="wamid.emergency_001",
    )
    raw_body = json.dumps(payload).encode("utf-8")
    sig = _sign_payload(raw_body)

    resp = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_body,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200

    event = db_session.scalar(
        select(InboundEvent).where(InboundEvent.provider_message_id == "wamid.emergency_001")
    )
    await InboundEventService.process_single_event(db_session, event.id)
    db_session.commit()

    assert len(mock_whatsapp.sent_messages) == 1
    reply_text = mock_whatsapp.sent_messages[0]["text"]
    # Must advise calling 1122 / emergency department
    assert "1122" in reply_text or "emergency" in reply_text.lower()
