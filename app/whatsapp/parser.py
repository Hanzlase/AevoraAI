"""Defensive parser for Meta WhatsApp Cloud API webhook event batches."""

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("aevora.whatsapp.parser")


@dataclass
class NormalizedMessageEvent:
    """Standardized internal representation of an incoming WhatsApp event."""

    provider_message_id: str
    sender_id: str
    sender_name: str | None
    event_type: str  # text, audio, status, unsupported
    payload: dict = field(default_factory=dict)
    timestamp: int = field(default_factory=lambda: int(time.time()))


def parse_webhook_payload(payload: dict) -> list[NormalizedMessageEvent]:
    """Parse raw Meta WhatsApp webhook JSON payload into a list of normalized events.

    Args:
        payload: Parsed JSON dictionary received from Meta.

    Returns:
        List of NormalizedMessageEvent objects to be queued or processed.
    """
    normalized_events: list[NormalizedMessageEvent] = []

    if not isinstance(payload, dict):
        logger.warning("Invalid webhook payload format: expected dict.")
        return normalized_events

    entries = payload.get("entry", [])
    if not isinstance(entries, list):
        return normalized_events

    for entry in entries:
        changes = entry.get("changes", [])
        if not isinstance(changes, list):
            continue

        for change in changes:
            value = change.get("value", {})
            if not isinstance(value, dict):
                continue

            # Extract sender profile names map if available
            contacts = value.get("contacts", [])
            contact_names: dict[str, str] = {}
            if isinstance(contacts, list):
                for contact in contacts:
                    wa_id = str(contact.get("wa_id", ""))
                    name = contact.get("profile", {}).get("name")
                    if wa_id and name:
                        contact_names[wa_id] = name

            # 1. Parse Status Updates (delivery, read, sent, failed)
            statuses = value.get("statuses", [])
            if isinstance(statuses, list):
                for status in statuses:
                    status_id = str(status.get("id", ""))
                    recipient_id = str(status.get("recipient_id", ""))
                    status_val = str(status.get("status", "unknown"))
                    if status_id:
                        normalized_events.append(
                            NormalizedMessageEvent(
                                provider_message_id=status_id,
                                sender_id=recipient_id,
                                sender_name=None,
                                event_type="status",
                                payload={
                                    "status": status_val,
                                    "timestamp": status.get("timestamp"),
                                    "errors": status.get("errors"),
                                },
                            )
                        )

            # 2. Parse Incoming Messages
            messages = value.get("messages", [])
            if isinstance(messages, list):
                for msg in messages:
                    msg_id = str(msg.get("id", ""))
                    sender_id = str(msg.get("from", ""))
                    msg_type = str(msg.get("type", "unknown"))
                    sender_name = contact_names.get(sender_id)
                    ts = int(msg.get("timestamp", time.time()))

                    if not msg_id or not sender_id:
                        continue

                    if msg_type == "text":
                        text_body = msg.get("text", {}).get("body", "").strip()
                        normalized_events.append(
                            NormalizedMessageEvent(
                                provider_message_id=msg_id,
                                sender_id=sender_id,
                                sender_name=sender_name,
                                event_type="text",
                                payload={"body": text_body},
                                timestamp=ts,
                            )
                        )
                    elif msg_type in ("audio", "voice"):
                        audio_data = msg.get(msg_type, {})
                        normalized_events.append(
                            NormalizedMessageEvent(
                                provider_message_id=msg_id,
                                sender_id=sender_id,
                                sender_name=sender_name,
                                event_type="audio",
                                payload={
                                    "media_id": str(audio_data.get("id", "")),
                                    "mime_type": str(audio_data.get("mime_type", "")),
                                    "sha256": audio_data.get("sha256"),
                                    "voice": audio_data.get("voice", False),
                                },
                                timestamp=ts,
                            )
                        )
                    else:
                        # Unsupported types (image, video, document, location, etc.)
                        normalized_events.append(
                            NormalizedMessageEvent(
                                provider_message_id=msg_id,
                                sender_id=sender_id,
                                sender_name=sender_name,
                                event_type="unsupported",
                                payload={
                                    "unsupported_type": msg_type,
                                    "raw": msg.get(msg_type),
                                },
                                timestamp=ts,
                            )
                        )

    return normalized_events
