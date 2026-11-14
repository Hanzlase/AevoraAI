"""Webhook verification and cryptographic signature validation for Meta WhatsApp Cloud API."""

import hashlib
import hmac
import logging

from app.core.config import Settings, get_settings

logger = logging.getLogger("aevora.whatsapp.security")


def verify_webhook_token(
    mode: str | None,
    verify_token: str | None,
    challenge: str | None,
    settings: Settings | None = None,
) -> str | None:
    """Validate Meta's GET verification subscription handshake.

    Args:
        mode: hub.mode parameter (must be "subscribe")
        verify_token: hub.verify_token parameter
        challenge: hub.challenge parameter to return
        settings: Optional custom application settings

    Returns:
        The challenge string if verification succeeds, None otherwise.
    """
    cfg = settings or get_settings()
    configured_token = (
        cfg.webhook_verify_token.get_secret_value() if cfg.webhook_verify_token else None
    )

    if not configured_token:
        logger.warning("Rejecting webhook verification: WEBHOOK_VERIFY_TOKEN is not configured.")
        return None

    if mode != "subscribe":
        logger.warning("Rejecting webhook verification: invalid hub.mode.")
        return None

    if not verify_token or not challenge:
        logger.warning("Rejecting webhook verification: missing token or challenge parameter.")
        return None

    # Constant-time token comparison to prevent timing attacks
    if not hmac.compare_digest(verify_token.strip(), configured_token.strip()):
        logger.warning("Rejecting webhook verification: verify_token mismatch.")
        return None

    logger.info("Meta webhook verification challenge successfully validated.")
    return challenge


def validate_signature(
    raw_body: bytes,
    signature_header: str | None,
    secret: str | None = None,
) -> bool:
    """Validate the X-Hub-Signature-256 header using HMAC-SHA256.

    Args:
        raw_body: The raw unparsed HTTP request body bytes.
        signature_header: The incoming X-Hub-Signature-256 header value.
        secret: The Meta App Secret (loaded from settings if omitted).

    Returns:
        True if the signature is authentic and verified, False otherwise.
    """
    if not signature_header:
        logger.warning("Rejecting webhook notification: missing X-Hub-Signature-256 header.")
        return False

    app_secret = secret
    if not app_secret:
        cfg = get_settings()
        app_secret = cfg.meta_app_secret.get_secret_value() if cfg.meta_app_secret else None

    if not app_secret:
        logger.warning("Rejecting webhook notification: META_APP_SECRET is not configured.")
        return False

    # Signature must be formatted as "sha256=<hex_digest>"
    parts = signature_header.strip().split("=", 1)
    if len(parts) != 2 or parts[0].lower() != "sha256":
        logger.warning("Rejecting webhook notification: malformed X-Hub-Signature-256 format.")
        return False

    received_hash = parts[1].strip()

    expected_hash = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison
    is_valid = hmac.compare_digest(received_hash, expected_hash)
    if not is_valid:
        logger.warning("Rejecting webhook notification: X-Hub-Signature-256 mismatch.")
    return is_valid
