# Aevora AI — Security & Privacy Architecture

This document outlines the security architecture, credential protection mechanisms, authentication standards, and patient data privacy guardrails implemented in Aevora AI.

---

## 1. Secrets & Credential Management

- **Environment Isolation**: All external tokens, API keys, and credentials are configured via environment variables and loaded into typed Pydantic Settings (`app/core/config.py`).
- **SecretStr Type Enforcement**: Secrets are wrapped in Pydantic's `SecretStr` type. Calling `str(settings.gemini_api_key)` or printing settings returns `**********`, preventing accidental string formatting leaks.
- **Git Repository Audit**:
  - `.env` is strictly excluded in `.gitignore`.
  - `.env.example` contains blank placeholders with zero real tokens or secrets.
  - Tracked source code contains zero embedded API keys, tokens, or live passwords.
- **Frontend Code Protection**: No API keys, app secrets, or server tokens are ever passed to frontend templates or JavaScript code. The staff dashboard operates purely on short-lived JWT bearer tokens.
- **Log Sanitization**: `SensitiveDataSanitizingFilter` (`app/core/logging.py`) intercepts all logging records and scrubs tokens, bearer headers, app secrets, and verify tokens before terminal output.

---

## 2. API & Webhook Security

- **Cryptographic Signature Validation**: All incoming WhatsApp webhook POST requests must supply an `X-Hub-Signature-256` header. The server computes the HMAC-SHA256 digest over the raw request bytes and compares it using `hmac.compare_digest` in constant time, preventing timing attacks.
- **Payload Size Limiting**: Inbound webhooks are strictly bounded by `WHATSAPP_WEBHOOK_MAX_BODY_BYTES` (default 1 MB). Requests exceeding this limit receive an immediate `413 Request Entity Too Large` rejection, protecting against memory exhaustion attacks.
- **Safe Error Responses**: Centralized exception handlers (`app/core/exceptions.py`) intercept unexpected exceptions and return clean JSON error payloads (`{"detail": "..."}`) without exposing internal file paths, stack traces, or library internals.
- **Media Host Whitelisting**: Media downloads for voice notes require HTTPS and enforce a strict domain whitelist (`lookaside.fbsbx.com`, `*.facebook.com`, `*.fbcdn.net`). Untrusted hosts are rejected prior to network download.

---

## 3. Staff Authentication & Access Control

- **Password Hashing**: Passwords are never stored in plaintext. They are hashed using PBKDF2-HMAC-SHA256 with 100,000 iterations and a unique 16-byte cryptographically secure salt generated via `secrets.token_hex(16)`.
- **JWT Bearer Tokens**: Authenticated staff sessions utilize standard RFC 7519 JSON Web Tokens signed with HMAC-SHA256 (`HS256`). Tokens carry user ID, username, role, and an explicit expiration timestamp (default 8 hours).
- **Endpoint Protection**: Administrative endpoints under `/api/v1/staff/...` require valid bearer tokens verified via FastAPI's `get_current_staff` dependency.
- **Session Expiry & Invalidation**: Expired or tampered tokens are rejected with `401 Unauthorized`. The dashboard automatically redirects expired sessions to the authentication modal.

---

## 4. Patient Privacy & Healthcare Safety

- **Fictional Data Boundary**: All clinic entities, doctors, schedules, fees, and patient records pertain to the fictional NovaCare Medical Centre demo dataset.
- **Phone Number Redaction**: Patient phone numbers are masked in logs and summarized displays using `mask_phone_number` (`0300****567`), mitigating shoulder-surfing and log exposure risks.
- **Temporary Audio Lifecycle**: Voice notes downloaded from Meta CDN are stored in `temp_audio/` with randomized filenames. Converted WAV files and source audio are deleted inside `finally` blocks immediately after Whisper transcription completes.
- **Conversation Isolation**: SQLite database records enforce conversation boundaries. Conversation threads are scoped to `(channel, external_user_id)` pairs; patients cannot access or inspect threads from other callers.
- **Data Deletion Rights**: Complete conversation threads, messages, and associated metadata can be purged via `DELETE /api/v1/chat/{conversation_id}`.
- **Medical Disclaimer**: Aevora AI explicitly disclaims clinical authority in prompts and system developer instructions, rejecting prescriptions and redirecting acute emergencies to local emergency services (**1122**).
