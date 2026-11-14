"""Automated tests for health check endpoints and configuration security."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a test client configured with isolated test settings."""
    test_settings = Settings(
        app_name="Aevora AI Test Service",
        environment="testing",
        version="0.1.0",
        gemini_api_key=None,
        whatsapp_access_token=None,
        meta_app_secret=None,
    )
    app = create_app(settings=test_settings)
    return TestClient(app)


def test_api_v1_health_endpoint(client: TestClient) -> None:
    """Verify that GET /api/v1/health returns 200 and safe operational metadata."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "Aevora AI Test Service"
    assert payload["version"] == "0.1.0"
    assert payload["environment"] == "testing"


def test_root_health_alias(client: TestClient) -> None:
    """Verify that root GET /health alias responds consistently with operational info."""
    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "Aevora AI Test Service"


def test_health_endpoint_does_not_expose_secrets_or_unbuilt_claims(client: TestClient) -> None:
    """Ensure health endpoint does not leak secrets or claim unbuilt subsystems are healthy."""
    response = client.get("/api/v1/health")
    payload = response.json()

    # Must only contain the approved keys
    allowed_keys = {"status", "service", "version", "environment"}
    assert set(payload.keys()) == allowed_keys

    # Must not contain any credential-like names
    forbidden_terms = [
        "key",
        "secret",
        "token",
        "database",
        "gemini",
        "whatsapp",
        "rag",
        "whisper",
    ]
    for key in payload:
        for term in forbidden_terms:
            assert term not in key.lower()


def test_settings_load_safely_without_credentials() -> None:
    """Ensure Settings initializes properly without external API keys or credentials."""
    settings = Settings(
        gemini_api_key=None,
        whatsapp_access_token=None,
        meta_app_secret=None,
        webhook_verify_token=None,
    )
    assert settings.app_name == "Aevora AI"
    assert settings.gemini_api_key is None
    assert settings.whatsapp_access_token is None


def test_settings_secrets_are_masked() -> None:
    """Ensure sensitive SecretStr values are never exposed through repr or str."""
    from pydantic import SecretStr

    settings = Settings(
        gemini_api_key=SecretStr("super_secret_gemini_key_12345"),
        whatsapp_access_token=SecretStr("super_secret_whatsapp_token_67890"),
        meta_app_secret=SecretStr("super_secret_meta_app_secret"),
    )

    # String representation must mask secret values
    settings_repr = repr(settings)
    assert "super_secret_gemini_key_12345" not in settings_repr
    assert "super_secret_whatsapp_token_67890" not in settings_repr
    assert "super_secret_meta_app_secret" not in settings_repr
    assert "**********" in settings_repr
