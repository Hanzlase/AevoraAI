"""Meta WhatsApp Cloud API HTTP client with timeouts, retries, and media download."""

import abc
import asyncio
import logging
from urllib.parse import urlparse

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger("aevora.whatsapp.client")

ALLOWED_META_MEDIA_HOSTS = {
    "lookaside.fbsbx.com",
    "graph.facebook.com",
}


def _is_trusted_media_host(url: str) -> bool:
    """Validate that media download URL is HTTPS and belongs to Meta infrastructure."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    if host in ALLOWED_META_MEDIA_HOSTS:
        return True
    if host.endswith(".facebook.com") or host.endswith(".fbcdn.net"):
        return True
    return False


class BaseWhatsAppClient(abc.ABC):
    """Abstract interface for Meta WhatsApp Cloud API client."""

    @abc.abstractmethod
    async def send_text_message(self, to: str, text: str) -> dict:
        """Send outbound text message to a WhatsApp recipient."""
        pass

    @abc.abstractmethod
    async def get_media_url(self, media_id: str) -> dict:
        """Retrieve media metadata and download URL from Meta Graph API."""
        pass

    @abc.abstractmethod
    async def download_media(self, download_url: str) -> bytes:
        """Download raw audio media bytes from verified Meta CDN URL."""
        pass


class MetaWhatsAppClient(BaseWhatsAppClient):
    """Concrete Meta Graph API client for production and live development testing."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.version = self.settings.whatsapp_graph_api_version
        self.phone_number_id = self.settings.whatsapp_phone_number_id
        self.base_url = f"https://graph.facebook.com/{self.version}"

    def _get_token(self) -> str:
        token = (
            self.settings.whatsapp_access_token.get_secret_value()
            if self.settings.whatsapp_access_token
            else None
        )
        if not token:
            raise RuntimeError(
                "WhatsApp access token is not configured (WHATSAPP_ACCESS_TOKEN is missing)."
            )
        return token

    async def send_text_message(self, to: str, text: str) -> dict:
        """Send outbound text reply to user through Meta WhatsApp Cloud API."""
        if not self.phone_number_id:
            raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID is not configured in settings.")

        token = self._get_token()
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to.strip().replace("+", ""),
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text,
            },
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        timeout = float(self.settings.whatsapp_api_timeout_seconds)
        max_retries = self.settings.whatsapp_max_retries

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, max_retries + 2):
                try:
                    logger.debug(f"Sending WhatsApp message to {to[:4]}**** (attempt {attempt})")
                    resp = await client.post(url, json=payload, headers=headers)
                    resp_data = resp.json() if resp.content else {}

                    if resp.is_success:
                        msg_id = resp_data.get("messages", [{}])[0].get("id", "unknown")
                        logger.info(f"Outbound WhatsApp message sent successfully (id: {msg_id})")
                        return resp_data

                    # If client error (4xx), do not retry (e.g. invalid recipient or expired token)
                    if 400 <= resp.status_code < 500:
                        err_msg = resp_data.get("error", {}).get("message", resp.text)
                        logger.error(
                            f"WhatsApp Graph API client error ({resp.status_code}): {err_msg}"
                        )
                        resp.raise_for_status()

                    resp.raise_for_status()
                except httpx.HTTPStatusError as err:
                    if err.response.status_code < 500 or attempt > max_retries:
                        raise
                    logger.warning(
                        f"Transient Graph API error ({err.response.status_code}). Retrying in {attempt}s..."
                    )
                    await asyncio.sleep(attempt)
                except httpx.RequestError as err:
                    if attempt > max_retries:
                        raise
                    logger.warning(
                        f"Network error calling Graph API: {err}. Retrying in {attempt}s..."
                    )
                    await asyncio.sleep(attempt)

        raise RuntimeError(f"Failed to send WhatsApp message after {max_retries + 1} attempts.")

    async def get_media_url(self, media_id: str) -> dict:
        """Fetch media URL and metadata using Graph API media ID."""
        token = self._get_token()
        url = f"{self.base_url}/{media_id}"
        headers = {"Authorization": f"Bearer {token}"}
        timeout = float(self.settings.whatsapp_api_timeout_seconds)

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            logger.debug(f"Fetched metadata for media_id {media_id}")
            return data

    async def download_media(self, download_url: str) -> bytes:
        """Download raw audio bytes from Meta's authenticated media URL."""
        if not _is_trusted_media_host(download_url):
            raise ValueError(
                f"Untrusted or insecure media host: '{download_url}'. Download refused."
            )

        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "AevoraAI/0.1.0",
        }
        timeout = float(self.settings.whatsapp_api_timeout_seconds)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(download_url, headers=headers)
            resp.raise_for_status()
            return resp.content


class MockWhatsAppClient(BaseWhatsAppClient):
    """Deterministic mock client for offline tests."""

    def __init__(self) -> None:
        self.sent_messages: list[dict] = []
        self.mock_media_data: dict[str, dict] = {}
        self.mock_audio_bytes: bytes = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

    async def send_text_message(self, to: str, text: str) -> dict:
        self.sent_messages.append({"to": to, "text": text})
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": to, "wa_id": to}],
            "messages": [{"id": f"wamid.mock.{len(self.sent_messages)}"}],
        }

    async def get_media_url(self, media_id: str) -> dict:
        if media_id in self.mock_media_data:
            return self.mock_media_data[media_id]
        return {
            "url": f"https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid={media_id}",
            "mime_type": "audio/ogg; codecs=opus",
            "sha256": "mock_sha256",
            "file_size": 1024,
            "id": media_id,
        }

    async def download_media(self, download_url: str) -> bytes:
        if not _is_trusted_media_host(download_url):
            raise ValueError(f"Untrusted media host: '{download_url}'")
        return self.mock_audio_bytes


_whatsapp_client_instance: BaseWhatsAppClient | None = None


def get_whatsapp_client() -> BaseWhatsAppClient:
    """Get active WhatsApp client instance."""
    global _whatsapp_client_instance
    if _whatsapp_client_instance is None:
        settings = get_settings()
        if settings.whatsapp_enabled and settings.whatsapp_access_token:
            _whatsapp_client_instance = MetaWhatsAppClient(settings)
        else:
            _whatsapp_client_instance = MockWhatsAppClient()
    return _whatsapp_client_instance


def set_whatsapp_client(client: BaseWhatsAppClient | None) -> None:
    """Override WhatsApp client for testing."""
    global _whatsapp_client_instance
    _whatsapp_client_instance = client
