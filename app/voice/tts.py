"""Optional text-to-speech module (disabled by default for patient privacy & cost control)."""

import logging

from app.core.config import Settings, get_settings

logger = logging.getLogger("aevora.voice.tts")

VOICE_MAP = {
    "ur": "ur-PK-UzmaNeural",
    "roman_ur": "ur-PK-UzmaNeural",
    "en": "en-US-JennyNeural",
}


async def generate_speech(
    text: str,
    language: str = "en",
    settings: Settings | None = None,
) -> bytes | None:
    """Generate audio speech bytes from text using edge-tts if explicitly enabled.

    Returns None if TTS is disabled or if generation fails, ensuring text replies are never blocked.
    """
    cfg = settings or get_settings()
    if not cfg.voice_reply_enabled:
        return None

    try:
        import edge_tts

        voice = VOICE_MAP.get(language, "en-US-JennyNeural")
        communicate = edge_tts.Communicate(text, voice)
        audio_chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        return b"".join(audio_chunks)
    except Exception as exc:
        logger.warning(f"Optional TTS generation failed (non-blocking): {exc}")
        return None
