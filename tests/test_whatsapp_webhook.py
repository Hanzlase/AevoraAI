"""Tests for Meta WhatsApp Cloud API webhook GET verification and POST signature validation."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
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
def test_settings():
    return Settings(
        webhook_verify_token="test_secret_token_123",
        meta_app_secret="test_app_secret_456",
        whatsapp_enabled=True,
        whatsapp_event_worker_enabled=False,  # Worker tested separately
        whatsapp_webhook_max_body_bytes=1000,
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


def test_get_webhook_verification_success(client):
    response = client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test_secret_token_123",
            "hub.challenge": "challenge_code_999",
        },
    )
    assert response.status_code == 200
    assert response.text == "challenge_code_999"


def test_get_webhook_verification_invalid_token(client):
    response = client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "challenge_code_999",
        },
    )
    assert response.status_code == 403
    assert "verification failed" in response.json()["detail"].lower()


def test_get_webhook_verification_missing_params(client):
    response = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe"},
    )
    assert response.status_code == 403


def test_post_webhook_valid_signature_success(client, test_settings):
    payload = {
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
                                    "from": "923001234567",
                                    "id": "wamid.test_001",
                                    "type": "text",
                                    "text": {"body": "Hello clinic"},
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
    secret = test_settings.meta_app_secret.get_secret_value()
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    response = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_body,
        headers={
            "X-Hub-Signature-256": f"sha256={sig}",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["received_count"] == 1
    assert data["newly_queued"] == 1


def test_post_webhook_invalid_signature_rejected(client):
    raw_body = b'{"object": "test"}'
    response = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_body,
        headers={"X-Hub-Signature-256": "sha256=invalid_hex_signature"},
    )
    assert response.status_code == 403
    assert "signature verification failed" in response.json()["detail"].lower()


def test_post_webhook_missing_signature_rejected(client):
    raw_body = b'{"object": "test"}'
    response = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_body,
    )
    assert response.status_code == 403


def test_post_webhook_oversized_payload_rejected(client, test_settings):
    # Setting has max 1000 bytes
    large_body = b"A" * 2000
    response = client.post(
        "/api/v1/whatsapp/webhook",
        content=large_body,
        headers={"X-Hub-Signature-256": "sha256=dummy"},
    )
    assert response.status_code == 413


def test_post_webhook_malformed_json_rejected(client, test_settings):
    raw_body = b"Not valid json {{"
    secret = test_settings.meta_app_secret.get_secret_value()
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    response = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw_body,
        headers={"X-Hub-Signature-256": f"sha256={sig}"},
    )
    assert response.status_code == 400
    assert "invalid json" in response.json()["detail"].lower()
