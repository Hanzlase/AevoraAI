"""Meta WhatsApp Cloud API webhook receiver and status routes."""

import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.models.inbound_event import InboundEvent
from app.services.event_worker import get_event_worker
from app.services.inbound_event_service import InboundEventService
from app.whatsapp.parser import parse_webhook_payload
from app.whatsapp.security import validate_signature, verify_webhook_token

logger = logging.getLogger("aevora.api.whatsapp")

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Cloud API"])


@router.get("/webhook", status_code=status.HTTP_200_OK)
def verify_whatsapp_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Handle Meta's GET verification subscription handshake.

    Validates hub.verify_token against configured secret and returns hub.challenge.
    """
    challenge = verify_webhook_token(
        mode=hub_mode,
        verify_token=hub_verify_token,
        challenge=hub_challenge,
        settings=settings,
    )
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook verification failed: invalid token or parameters.",
        )

    return Response(content=challenge, media_type="text/plain", status_code=status.HTTP_200_OK)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def receive_whatsapp_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Receive and validate incoming Meta WhatsApp Cloud API webhook events.

    Verifies HMAC-SHA256 signature, parses supported message types, queues events
    durably for idempotency, and immediately returns 200 OK.
    """
    raw_body = await request.body()

    # Enforce maximum body size
    if len(raw_body) > settings.whatsapp_webhook_max_body_bytes:
        logger.warning(f"Rejected oversized webhook payload ({len(raw_body)} bytes)")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Webhook payload exceeds maximum size limit.",
        )

    # Validate cryptographic signature
    secret = settings.meta_app_secret.get_secret_value() if settings.meta_app_secret else None
    if not validate_signature(
        raw_body=raw_body, signature_header=x_hub_signature_256, secret=secret
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook signature verification failed.",
        )

    # Parse JSON payload
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        logger.warning(f"Failed to decode webhook JSON: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        ) from exc

    # Parse and extract normalized events
    normalized_events = parse_webhook_payload(payload)
    queued_count = 0

    for event in normalized_events:
        _, is_new = InboundEventService.queue_event(db=db, event=event)
        if is_new:
            queued_count += 1

    return {
        "status": "success",
        "received_count": len(normalized_events),
        "newly_queued": queued_count,
    }


@router.get("/status", status_code=status.HTTP_200_OK)
def get_whatsapp_status(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Safe operational diagnostic for WhatsApp Cloud API and background worker."""
    worker = get_event_worker()

    pending_count = (
        db.scalar(select(func.count(InboundEvent.id)).where(InboundEvent.status == "pending")) or 0
    )
    failed_count = (
        db.scalar(select(func.count(InboundEvent.id)).where(InboundEvent.status == "failed")) or 0
    )

    phone_id_preview = (
        f"{settings.whatsapp_phone_number_id[:4]}****"
        if settings.whatsapp_phone_number_id
        else "not_configured"
    )

    return {
        "whatsapp_enabled": settings.whatsapp_enabled,
        "phone_number_id": phone_id_preview,
        "graph_api_version": settings.whatsapp_graph_api_version,
        "worker_running": worker.is_running,
        "voice_input_enabled": settings.voice_input_enabled,
        "whisper_device": settings.whisper_device,
        "whisper_model_size": settings.whisper_model_size,
        "voice_reply_enabled": settings.voice_reply_enabled,
        "pending_events": pending_count,
        "failed_events": failed_count,
    }
