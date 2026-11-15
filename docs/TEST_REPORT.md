# Aevora AI — Final Verification & Automated Test Report

> **Generated**: November 14, 2026  
> **Test Framework**: Pytest 8.4.2 + HTTPX ASGI Transport  
> **Code Audit**: Ruff 0.17.5  
> **Total Test Count**: 105 passed, 0 failed, 0 skipped (100% Green)

---

## 1. Executive Summary

Aevora AI has undergone comprehensive verification across all five roadmap phases. Every critical patient workflow, RAG retrieval mechanism, Gemini prompt grounding constraint, WhatsApp webhook parser, audio transcription pipeline, and staff management interface has automated test coverage.

| Category | Test Modules | Tests | Status |
| :--- | :--- | :---: | :---: |
| **Phase 01: Project Foundation** | `test_health.py` | 5 | **PASSED** |
| **Phase 02: Hybrid RAG & Retrieval** | `test_rag.py` | 12 | **PASSED** |
| **Phase 03: AI Receptionist Core** | `test_gemini_client.py`, `test_safety.py`, `test_multilingual_chat.py`, `test_conversation.py`, `test_appointment_workflow.py` | 29 | **PASSED** |
| **Phase 04: WhatsApp & Voice Adapter** | `test_whatsapp_webhook.py`, `test_whatsapp_parser.py`, `test_whatsapp_client.py`, `test_idempotency_and_worker.py`, `test_voice_pipeline.py`, `test_whatsapp_adapter.py` | 30 | **PASSED** |
| **Phase 05: Dashboard, Security & E2E** | `test_staff_dashboard.py`, `test_e2e_journeys.py`, `test_security_and_hardening.py`, `test_voice_edge_cases.py` | 29 | **PASSED** |
| **Total** | **17 Test Modules** | **105** | **100% Passed** |

---

## 2. Granular Module Breakdown

### 2.1 Project Foundation (`tests/test_health.py`) — 5 Tests
- Root `/health` alias and versioned `/api/v1/health` responses.
- Environment reporting and CORS headers.
- Safe operational metadata without false claims.

### 2.2 Clinic Knowledge Base & RAG Retrieval (`tests/test_rag.py`) — 12 Tests
- PDF header/footer cleaning and Page 8 test query exclusion.
- Canonical JSON extraction preserving fee numbers and doctor OPD schedules.
- FAISS dense vector search with E5 prefixing (`passage: ` and `query: `).
- BM25Okapi sparse keyword retrieval and Roman Urdu alias expansion.
- Reciprocal Rank Fusion ($k=60$) score calculation and threshold filtering.
- Automated consistency reporting on 4 fee notes between JSON and PDF.

### 2.3 AI Receptionist Core & Guardrails — 29 Tests
- `test_gemini_client.py` (4 tests): Client initialization, system prompt configuration via `v1beta`, zero thinking budget, mock LLM client.
- `test_safety.py` (15 tests): Acute emergency detection (1122 redirection across English, Urdu, Roman Urdu), clinical advice deflection (medications, diagnosis), safe query passthrough.
- `test_multilingual_chat.py` (4 tests): Multi-turn language matching across English, Urdu script, Roman Urdu, and mixed queries.
- `test_conversation.py` (4 tests): Session isolation, persistent message history, cascade deletion, staff handoff creation.
- `test_appointment_workflow.py` (2 tests): Progressive multi-turn appointment intake state machine, explicit confirmation requirement, patient cancellation.

### 2.4 WhatsApp Cloud API & Voice Integration — 30 Tests
- `test_whatsapp_webhook.py` (8 tests): GET subscription challenge verification, POST HMAC-SHA256 signature validation, oversized body rejection (413), malformed JSON handling.
- `test_whatsapp_parser.py` (5 tests): Parsing of incoming text, voice notes, status receipts, unsupported message types.
- `test_whatsapp_client.py` (3 tests): Meta CDN domain whitelist enforcement, outbound Graph API payload format, mock client.
- `test_idempotency_and_worker.py` (4 tests): Duplicate message ID deduplication in SQLite, background event worker lifecycle, bounded exponential retries.
- `test_voice_pipeline.py` (5 tests): Audio size/MIME validation, FFmpeg binary resolution, Faster-Whisper CPU fallback, TTS disabled by default.
- `test_whatsapp_adapter.py` (5 tests): End-to-end integration: text webhook $\rightarrow$ queue $\rightarrow$ RAG $\rightarrow$ outbound WhatsApp message; voice note webhook $\rightarrow$ transcribe $\rightarrow$ reply; appointment intake via WhatsApp; handoff via WhatsApp; emergency deflection via WhatsApp.

### 2.5 Staff Dashboard, Security Hardening & End-to-End Journeys — 29 Tests
- `test_staff_dashboard.py` (10 tests): Staff login with valid credentials, 401 on invalid password/user, profile retrieval, clinic overview metrics, conversation list and detail with citations, appointment status updates (`confirmed_by_staff`, `cancelled`), system and KB diagnostics, dashboard static files.
- `test_e2e_journeys.py` (7 tests): Complete verification of Journeys A through G (Clinic FAQ, Multilingual, WhatsApp Text, Voice Notes, Appointments, Staff Handoffs, Medical Guardrails).
- `test_security_and_hardening.py` (7 tests): Unauthenticated browser request rejection (401), expired JWT token rejection (401), forged webhook signature rejection (403), oversized webhook rejection (413), phone number masking, conversation isolation, adversarial prompt injection deflection.
- `test_voice_edge_cases.py` (5 tests): Trusted Meta CDN validation, file size bounds, temporary audio cleanup on corrupt audio, silence handling, CPU fallback parameters.

---

## 3. Test Execution Verification Log

```powershell
Command: .\.venv\Scripts\pytest -q
Output:
........................................................................ [ 68%]
.................................                                        [100%]
============================== warnings summary ===============================
tests/test_idempotency_and_worker.py::test_event_processing_lifecycle
  DeprecationWarning: Inheritance class AiohttpClientSession from ClientSession is discouraged

======================= 105 passed, 1 warning in 31.25s =======================
Exit Code: 0
```

---

## 4. Code Quality Audit (Ruff)

```powershell
Command: .\.venv\Scripts\ruff check .
Output: All checks passed!

Command: .\.venv\Scripts\ruff format --check .
Output: 84 files already formatted
```

---

## 5. Distinction Between Mock and Live Testing

| Capability | Automated Mock Test | Live Manual Integration | Status |
| :--- | :---: | :---: | :--- |
| **RAG Ingestion & Hybrid Search** | Real FAISS + BM25 | Real FAISS + BM25 | **Verified live & automated** |
| **Gemini AI Generation** | Deterministic Mock LLM | Live `gemini-2.5-flash` API | **Verified live & automated** |
| **WhatsApp Webhook Ingress** | Signed HTTP POST harness | Cloudflare Quick Tunnel | **Verified live & automated** |
| **WhatsApp Outbound Send** | Deterministic Mock Client | Meta Graph API test number | **Verified with mock; live requires active token** |
| **Faster-Whisper Transcription** | Deterministic Mock Transcriber | Real CTranslate2 CPU model | **Verified live & automated** |
| **Staff Dashboard UI** | TestClient API assertions | Chrome Browser live manual inspection | **Verified live & automated** |
