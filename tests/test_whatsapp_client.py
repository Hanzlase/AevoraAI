"""Tests for Meta WhatsApp Cloud API client, outbound formatting, and media host security."""

import pytest

from app.core.config import Settings
from app.whatsapp.client import (
    MetaWhatsAppClient,
    MockWhatsAppClient,
    _is_trusted_media_host,
)


def test_trusted_media_host_validation():
    assert (
        _is_trusted_media_host("https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=123")
        is True
    )
    assert _is_trusted_media_host("https://graph.facebook.com/v22.0/123") is True
    assert _is_trusted_media_host("https://scontent.whatsapp.net.fbcdn.net/v/t39/123.ogg") is True

    # Insecure or untrusted hosts must be rejected
    assert _is_trusted_media_host("http://lookaside.fbsbx.com/insecure") is False
    assert _is_trusted_media_host("https://malicious-site.com/audio.ogg") is False
    assert _is_trusted_media_host("https://attacker.facebook.com.evil.org/payload") is False


def test_meta_client_missing_credentials_raises_runtime_error():
    dummy_settings = Settings(
        whatsapp_access_token=None,
        whatsapp_phone_number_id=None,
    )
    client = MetaWhatsAppClient(settings=dummy_settings)

    with pytest.raises(RuntimeError, match="WHATSAPP_PHONE_NUMBER_ID is not configured"):
        import asyncio

        asyncio.run(client.send_text_message("923001234567", "Hello"))


@pytest.mark.asyncio
async def test_mock_whatsapp_client():
    mock = MockWhatsAppClient()
    resp = await mock.send_text_message("923001234567", "Test greeting")
    assert resp["messaging_product"] == "whatsapp"
    assert len(mock.sent_messages) == 1
    assert mock.sent_messages[0]["to"] == "923001234567"
    assert mock.sent_messages[0]["text"] == "Test greeting"

    media_info = await mock.get_media_url("med_123")
    assert "lookaside.fbsbx.com" in media_info["url"]

    downloaded = await mock.download_media(media_info["url"])
    assert len(downloaded) > 0
