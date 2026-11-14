"""Durable webhook event processing, idempotency, and background worker queue."""

import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.inbound_event import InboundEvent
from app.schemas.chat import ChatRequest
from app.services.conversation_service import ConversationService
from app.voice.audio_processor import AudioProcessor
from app.voice.transcription import get_transcriber
from app.voice.tts import generate_speech
from app.whatsapp.client import get_whatsapp_client
from app.whatsapp.parser import NormalizedMessageEvent

logger = logging.getLogger("aevora.services.inbound_event")


class InboundEventService:
    """Manages idempotent queuing and execution of incoming WhatsApp events."""

    @staticmethod
    def queue_event(
        db: Session,
        event: NormalizedMessageEvent,
    ) -> tuple[InboundEvent, bool]:
        """Record an inbound webhook event. Enforces idempotency via provider_message_id.

        Returns:
            Tuple of (InboundEvent, is_created_bool).
        """
        # Idempotency check: if provider_message_id already exists, return existing
        if event.provider_message_id:
            existing = db.scalar(
                select(InboundEvent).where(
                    InboundEvent.provider_message_id == event.provider_message_id
                )
            )
            if existing:
                logger.info(
                    f"Idempotency hit: event {event.provider_message_id} already queued with status '{existing.status}'."
                )
                return existing, False

        inbound_event = InboundEvent(
            provider_message_id=event.provider_message_id,
            channel="whatsapp",
            sender_id=event.sender_id,
            event_type=event.event_type,
            payload=event.payload,
            status="pending",
        )
        db.add(inbound_event)
        db.flush()
        logger.info(
            f"Queued inbound event {inbound_event.id} ({event.event_type}) from sender {event.sender_id[:4]}****"
        )
        return inbound_event, True

    @classmethod
    async def process_single_event(
        cls,
        db: Session,
        event_id: str,
        settings: Settings | None = None,
    ) -> InboundEvent | None:
        """Execute a single queued inbound event."""
        cfg = settings or get_settings()
        event = db.get(InboundEvent, event_id)
        if not event or event.status not in ("pending", "processing"):
            return event

        event.status = "processing"
        event.attempts += 1
        db.flush()

        client = get_whatsapp_client()

        try:
            # 1. Text Message Event
            if event.event_type == "text":
                body = (event.payload.get("body") or "").strip()
                if body:
                    chat_req = ChatRequest(
                        message=body,
                        channel="whatsapp",
                        external_user_id=event.sender_id,
                    )
                    chat_resp = await ConversationService.process_chat(db=db, request=chat_req)
                    await client.send_text_message(event.sender_id, chat_resp.response)

                    # Optional non-blocking TTS
                    if cfg.voice_reply_enabled:
                        await generate_speech(
                            text=chat_resp.response,
                            language=chat_resp.language,
                            settings=cfg,
                        )

            # 2. Audio / Voice Note Message Event
            elif event.event_type == "audio":
                media_id = event.payload.get("media_id")
                if not media_id:
                    raise ValueError("Audio event missing media_id in payload.")

                processor = AudioProcessor(cfg)
                temp_in: Path | None = None
                temp_wav: Path | None = None

                try:
                    # Fetch media metadata & download URL
                    media_meta = await client.get_media_url(media_id)
                    download_url = media_meta.get("url")
                    mime_type = media_meta.get(
                        "mime_type", event.payload.get("mime_type", "audio/ogg")
                    )
                    file_size = media_meta.get("file_size", 0)

                    if not download_url:
                        raise ValueError(
                            f"No download URL returned by Meta for media_id {media_id}"
                        )

                    # Validate size & mime
                    processor.validate_audio_metadata(file_size, mime_type)

                    # Download media bytes
                    audio_bytes = await client.download_media(download_url)
                    temp_in = processor.save_temp_bytes(audio_bytes)

                    # Convert to 16kHz WAV
                    temp_wav = await processor.convert_to_wav(temp_in)

                    # Transcribe using Faster-Whisper
                    transcriber = get_transcriber()
                    transcription = await transcriber.transcribe(temp_wav)
                    transcribed_text = transcription.text.strip()

                    if not transcribed_text:
                        # Audio was silent or unintelligible
                        clarify_msg = (
                            "We received your voice note, but could not hear a clear message. "
                            "Please try resending your voice note or typing your question."
                        )
                        await client.send_text_message(event.sender_id, clarify_msg)
                    else:
                        logger.info(
                            f"Voice note transcribed ({len(transcribed_text)} chars, lang={transcription.language})"
                        )
                        chat_req = ChatRequest(
                            message=transcribed_text,
                            channel="whatsapp",
                            external_user_id=event.sender_id,
                        )
                        chat_resp = await ConversationService.process_chat(db=db, request=chat_req)
                        await client.send_text_message(event.sender_id, chat_resp.response)

                        if cfg.voice_reply_enabled:
                            await generate_speech(
                                text=chat_resp.response,
                                language=chat_resp.language,
                                settings=cfg,
                            )
                finally:
                    processor.cleanup_file(temp_in)
                    processor.cleanup_file(temp_wav)

            # 3. Status Notification (delivery/read)
            elif event.event_type == "status":
                logger.debug(
                    f"Acknowledged WhatsApp delivery status: {event.payload.get('status')} for msg {event.provider_message_id}"
                )

            # 4. Unsupported Event Type
            elif event.event_type == "unsupported":
                unsupported_type = event.payload.get("unsupported_type", "message")
                explainer = (
                    f"Thank you for contacting NovaCare Medical Centre. Our virtual receptionist "
                    f"currently supports text and voice notes (received {unsupported_type}). "
                    f"Please send your inquiry as a text message or voice note."
                )
                await client.send_text_message(event.sender_id, explainer)

            event.status = "processed"
            event.processed_at = datetime.now(UTC)
            event.last_error = None
            db.flush()
            logger.info(f"Successfully processed inbound event {event.id}")
            return event

        except Exception as exc:
            logger.error(f"Error processing inbound event {event.id}: {exc}", exc_info=True)
            event.last_error = str(exc)[:500]
            if event.attempts >= event.max_attempts:
                event.status = "failed"
                logger.error(
                    f"Event {event.id} permanently failed after {event.attempts} attempts."
                )
            else:
                event.status = "pending"  # Requeue for retry
            db.flush()
            return event
