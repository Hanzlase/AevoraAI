# WhatsApp Cloud API & Voice Setup Guide

This guide details end-to-end setup for connecting Aevora AI to the official Meta WhatsApp Business Cloud API and configuring local development tunnels and audio transcription.

---

## 1. Prerequisites

- Meta Developer Account: [https://developers.facebook.com](https://developers.facebook.com)
- Python 3.12+ virtual environment with dependencies installed:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  pip install -e .
  ```
- Free Cloudflare Tunnel CLI (`cloudflared`):
  - Download Windows binary from [Cloudflare Releases](https://github.com/cloudflare/cloudflared/releases) or install via `winget install --id Cloudflare.cloudflared`.

---

## 2. Meta Developer Console Setup

1. **Create an App**:
   - Go to [Meta Developer App Dashboard](https://developers.facebook.com/apps).
   - Click **Create App** $\rightarrow$ Select **Other** $\rightarrow$ Select **Business**.
   - Enter App Name: `Aevora AI Demo` and link your Meta Business Account.

2. **Add WhatsApp Product**:
   - In the App Dashboard left sidebar, find **Add products to your app** and add **WhatsApp**.
   - Navigate to **WhatsApp** $\rightarrow$ **API Setup**.

3. **Obtain Credentials**:
   - **Phone Number ID**: Copy the test phone number ID under *Step 1: Select phone numbers*.
   - **WhatsApp Business Account ID (WABA ID)**: Found right below the phone number ID.
   - **Temporary Access Token**: Copy the 24-hour test access token (for local testing) or generate a System User permanent token via Meta Business Manager.
   - **Meta App Secret**: Navigate to **App settings** $\rightarrow$ **Basic** $\rightarrow$ Click *Show* next to **App Secret**.

4. **Define Webhook Verify Token**:
   - Create a strong arbitrary string for subscription handshakes (e.g., `aevora_clinic_verify_tok_2026`).

---

## 3. Configure Local Environment (`.env`)

Add or update the following keys in your `.env` file:

```dotenv
# Meta WhatsApp Cloud API Configuration
WHATSAPP_ENABLED=true
WHATSAPP_PHONE_NUMBER_ID=your_meta_phone_number_id_here
WHATSAPP_WABA_ID=your_meta_waba_id_here
WHATSAPP_ACCESS_TOKEN=your_meta_access_or_system_user_token
WHATSAPP_GRAPH_API_VERSION=v22.0
META_APP_SECRET=your_meta_app_secret_here
WEBHOOK_VERIFY_TOKEN=aevora_clinic_verify_tok_2026
WHATSAPP_WEBHOOK_MAX_BODY_BYTES=1048576

# Durable Inbound Event Processing
WHATSAPP_EVENT_WORKER_ENABLED=true
WHATSAPP_EVENT_POLL_INTERVAL_SECONDS=1.0
WHATSAPP_MAX_EVENT_ATTEMPTS=5

# Voice Note Transcription (Faster-Whisper & FFmpeg)
VOICE_INPUT_ENABLED=true
VOICE_MAX_FILE_SIZE_MB=16
VOICE_MAX_DURATION_SECONDS=180
VOICE_TEMP_DIR=temp_audio
VOICE_ALLOWED_MIME_TYPES=["audio/ogg", "audio/ogg; codecs=opus", "audio/wav", "audio/x-wav", "audio/mp4", "audio/m4a", "audio/aac", "audio/mpeg"]
FFMPEG_BINARY=ffmpeg
VOICE_PROCESSING_TIMEOUT_SECONDS=120
VOICE_MAX_CONCURRENT_JOBS=1
WHISPER_MODEL_SIZE=base
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=auto
WHISPER_CPU_THREADS=4
WHISPER_NUM_WORKERS=1

# Optional Outbound Spoken Audio (TTS)
VOICE_REPLY_ENABLED=false
VOICE_REPLY_PROVIDER=edge_tts
VOICE_REPLY_LANGUAGE_MODE=match_user
VOICE_REPLY_TIMEOUT_SECONDS=30
```

---

## 4. Run Aevora AI Locally

Start the FastAPI application:

```powershell
.\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify the local health and diagnostic endpoints:
- Root Health: `http://localhost:8000/health`
- WhatsApp Status: `http://localhost:8000/api/v1/whatsapp/status`

---

## 5. Expose Webhook via Cloudflare Quick Tunnel

In a separate terminal, launch a free zero-configuration Cloudflare tunnel:

```powershell
cloudflared tunnel --url http://localhost:8000
```

Cloudflare will output a public HTTPS address like:
```text
https://random-subdomain.trycloudflare.com
```

Your Meta webhook URL will be:
```text
https://random-subdomain.trycloudflare.com/api/v1/whatsapp/webhook
```

---

## 6. Configure Webhook in Meta Developer Console

1. In the Meta Developer Dashboard, go to **WhatsApp** $\rightarrow$ **Configuration**.
2. Under **Webhook**, click **Edit**:
   - **Callback URL**: `https://random-subdomain.trycloudflare.com/api/v1/whatsapp/webhook`
   - **Verify Token**: `aevora_clinic_verify_tok_2026` (must match `WEBHOOK_VERIFY_TOKEN` in `.env`)
3. Click **Verify and save**.
   - Meta sends an immediate `GET` handshake with `hub.challenge`.
   - Aevora AI verifies constant-time token equality and returns the challenge.
4. Under **Webhook fields**, click **Manage**:
   - Subscribe to the **`messages`** field.
5. In **API Setup**, add your personal WhatsApp mobile number as a recipient under *To* to send test messages.

---

## 7. Voice Notes & FFmpeg Resolution

Aevora AI automatically handles voice notes:
1. Meta webhook arrives with `type="audio"` and a `media_id`.
2. Aevora calls Meta Graph API to resolve the signed media URL.
3. Media host is verified (`lookaside.fbsbx.com` or `*.facebook.com` / `*.fbcdn.net`).
4. File is authenticated and downloaded to `temp_audio/` within size limit ($\le 16\text{MB}$).
5. FFmpeg converts audio to 16kHz mono WAV:
   - System binary `ffmpeg` on PATH is checked first.
   - If not found, Aevora automatically falls back to bundled `imageio-ffmpeg` binary inside `.venv`.
6. Faster-Whisper transcribes the audio:
   - Probes CUDA / GPU compute capabilities; falls back to CPU `int8` if GPU is unavailable or out of memory.
   - Detects English, Urdu, or Roman Urdu.
7. Transcribed text is processed identically through Phase 03 RAG and Medical Safety policies.
8. Outbound clinic response is sent back to the patient's WhatsApp number.
9. Temporary audio files are cleaned up in a `finally` block on success or failure.

---

## 8. Common Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **Verification Failed (403)** | `hub.verify_token` does not match `WEBHOOK_VERIFY_TOKEN`. | Verify both strings match exactly with no leading/trailing whitespace. |
| **Signature Mismatch (403)** | `X-Hub-Signature-256` HMAC check failed against `META_APP_SECRET`. | Ensure `META_APP_SECRET` from Meta App Basic Settings is copied into `.env`. |
| **413 Payload Too Large** | Request body exceeded `WHATSAPP_WEBHOOK_MAX_BODY_BYTES`. | Normal behavior protecting against denial-of-service payloads. Default is 1 MB. |
| **Token Expired (190)** | Meta 24-hour temporary access token expired. | Regenerate test token in Meta Console or configure a permanent System User token. |
| **Untrusted Media Host** | Meta media download redirected to unauthorized host. | Aevora enforces strict domain whitelist (`*.facebook.com`, `*.fbcdn.net`, `lookaside.fbsbx.com`). |
| **FFmpeg Not Found** | System lacks FFmpeg and `imageio-ffmpeg` is missing. | Run `pip install imageio-ffmpeg` or install FFmpeg via winget: `winget install Gyan.FFmpeg`. |
