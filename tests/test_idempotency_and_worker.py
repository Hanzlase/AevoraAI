"""Tests for durable webhook event idempotency, deduplication, and worker processing."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.models.inbound_event import InboundEvent
from app.services.event_worker import EventWorker
from app.services.inbound_event_service import InboundEventService
from app.whatsapp.client import MockWhatsAppClient, set_whatsapp_client
from app.whatsapp.parser import NormalizedMessageEvent

engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine_test)
    session = TestingSessionLocal()
    mock_client = MockWhatsAppClient()
    set_whatsapp_client(mock_client)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_test)
        set_whatsapp_client(None)


def test_idempotency_duplicate_provider_message_id(db):
    ev1 = NormalizedMessageEvent(
        provider_message_id="wamid.test_unique_101",
        sender_id="923001234567",
        sender_name="Ali",
        event_type="text",
        payload={"body": "Hello"},
    )

    # First delivery
    record1, is_new1 = InboundEventService.queue_event(db, ev1)
    db.commit()
    assert is_new1 is True
    assert record1.status == "pending"

    # Second delivery of same message ID (Meta retry)
    record2, is_new2 = InboundEventService.queue_event(db, ev1)
    db.commit()
    assert is_new2 is False
    assert record2.id == record1.id

    # Verify only one event in DB
    all_events = list(db.scalars(select(InboundEvent)).all())
    assert len(all_events) == 1


@pytest.mark.asyncio
async def test_event_processing_lifecycle(db):
    ev = NormalizedMessageEvent(
        provider_message_id="wamid.test_lifecycle_202",
        sender_id="923001234567",
        sender_name="Fatima",
        event_type="text",
        payload={"body": "What are the clinic timings?"},
    )
    record, is_new = InboundEventService.queue_event(db, ev)
    db.commit()

    processed_record = await InboundEventService.process_single_event(db, record.id)
    db.commit()

    assert processed_record.status == "processed"
    assert processed_record.processed_at is not None
    assert processed_record.attempts == 1


@pytest.mark.asyncio
async def test_bounded_retries_and_failure(db):
    # Event with an invalid payload to force an error
    record = InboundEvent(
        provider_message_id="wamid.error_test_303",
        channel="whatsapp",
        sender_id="923001234567",
        event_type="audio",
        payload={},  # Missing media_id
        status="pending",
        attempts=4,
        max_attempts=5,
    )
    db.add(record)
    db.commit()

    # 5th attempt fails -> transitions to "failed"
    processed = await InboundEventService.process_single_event(db, record.id)
    db.commit()

    assert processed.status == "failed"
    assert processed.attempts == 5
    assert processed.last_error is not None


@pytest.mark.asyncio
async def test_worker_lifecycle():
    worker = EventWorker()
    assert not worker.is_running
    worker.start()
    assert worker.is_running
    await worker.stop()
    assert not worker.is_running
