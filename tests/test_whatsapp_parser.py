"""Tests for defensive parsing of Meta WhatsApp Cloud API webhook payloads."""

from app.whatsapp.parser import parse_webhook_payload


def test_parse_text_message():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_001",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [
                                {
                                    "profile": {"name": "Tariq Mahmood"},
                                    "wa_id": "923001112233",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "923001112233",
                                    "id": "wamid.HBgL12345",
                                    "timestamp": "1710000000",
                                    "type": "text",
                                    "text": {"body": "Clinic fees for Dr Bilal?"},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }
    events = parse_webhook_payload(payload)
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "text"
    assert ev.provider_message_id == "wamid.HBgL12345"
    assert ev.sender_id == "923001112233"
    assert ev.sender_name == "Tariq Mahmood"
    assert ev.payload["body"] == "Clinic fees for Dr Bilal?"


def test_parse_audio_voice_note_message():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "923335557788",
                                    "id": "wamid.audio_999",
                                    "timestamp": "1710000100",
                                    "type": "audio",
                                    "audio": {
                                        "id": "media_id_abc123",
                                        "mime_type": "audio/ogg; codecs=opus",
                                        "sha256": "checksum_hex",
                                        "voice": True,
                                    },
                                }
                            ]
                        }
                    }
                ]
            }
        ],
    }
    events = parse_webhook_payload(payload)
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "audio"
    assert ev.provider_message_id == "wamid.audio_999"
    assert ev.sender_id == "923335557788"
    assert ev.payload["media_id"] == "media_id_abc123"
    assert ev.payload["mime_type"] == "audio/ogg; codecs=opus"
    assert ev.payload["voice"] is True


def test_parse_status_notification():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {
                                    "id": "wamid.outbound_777",
                                    "status": "delivered",
                                    "timestamp": "1710000200",
                                    "recipient_id": "923001112233",
                                }
                            ]
                        }
                    }
                ]
            }
        ],
    }
    events = parse_webhook_payload(payload)
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "status"
    assert ev.provider_message_id == "wamid.outbound_777"
    assert ev.payload["status"] == "delivered"


def test_parse_unsupported_message_type():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "923001112233",
                                    "id": "wamid.img_111",
                                    "type": "image",
                                    "image": {"id": "img_id_000"},
                                }
                            ]
                        }
                    }
                ]
            }
        ],
    }
    events = parse_webhook_payload(payload)
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "unsupported"
    assert ev.payload["unsupported_type"] == "image"


def test_parse_empty_and_malformed_payloads():
    assert parse_webhook_payload({}) == []
    assert parse_webhook_payload({"entry": []}) == []
    assert parse_webhook_payload({"entry": [{"changes": []}]}) == []
