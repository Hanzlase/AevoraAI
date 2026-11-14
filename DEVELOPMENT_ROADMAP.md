# Aevora AI — Revised Development Roadmap

## Roadmap Decision

Keep the current **Phase 01** complete and verified. The development plan is organized into **five focused, milestone-driven implementation phases** (the foundation plus four comprehensive capability phases).

Each phase must be implemented, tested, and documented before moving on. Do not skip acceptance criteria just to finish a phase faster.

---

## Phase Overview

| Phase | Milestone Title | Status | Primary Focus |
| :---: | :--- | :---: | :--- |
| **01** | **Project Foundation** | **COMPLETED** | FastAPI modular monolith, typed Pydantic config, logging, health check, automated tests, and core docs. |
| **02** | **Clinic Knowledge Base, RAG & Multilingual Retrieval** | **COMPLETED** | PDF/JSON ingestion, chunking, multilingual embeddings, FAISS CPU + BM25, Urdu/Roman Urdu retrieval. |
| **03** | **AI Receptionist, Conversation Memory & Clinic Workflows** | Pending | Configurable Gemini Flash, grounded persona, SQLite memory, appointment requests, triage & safety boundaries. |
| **04** | **WhatsApp Integration & Voice Conversations** | Pending | Meta Cloud API webhooks, Cloudflare tunnel, Faster-Whisper CPU audio transcription, optional Edge TTS. |
| **05** | **End-to-End Quality, Security, Deployment & Final Demo** | Pending | 50+ evaluation scenarios, security audit, tunnel guide, employer demo checklist, optional refined GUI. |

---

## Phase 01 — Project Foundation

**Status: COMPLETED & VERIFIED**

Set up the Python/FastAPI project, modular structure, configuration and `.env.example`, secret handling, logging, health endpoint, tests, README, and project-control documents.

**Acceptance criteria**
- [x] The application starts locally using documented commands.
- [x] The health endpoint returns a successful response.
- [x] Configuration validation reports missing required settings clearly without exposing secrets.
- [x] Initial tests pass (5/5 tests passing in pytest).
- [x] The architecture and remaining roadmap are documented.

---

## Phase 02 — Clinic Knowledge Base, RAG and Multilingual Retrieval

**Status: COMPLETED & VERIFIED**

**Goal:** Make Aevora reliably find the correct clinic information from the supplied fictional NovaCare dataset.

**Build**
- Use `NovaCare_Medical_Centre_RAG_Knowledge_Base.pdf` and `NovaCare_RAG_Source_of_Truth.json` as the initial fictional demo data.
- Treat the JSON source of truth as the canonical structured source; retain the PDF as a realistic document-ingestion source and human-readable clinic reference.
- Add PDF/text extraction, cleaning, metadata, chunking and overlap, source/page tracking, and repeatable re-indexing.
- Implement multilingual embeddings, FAISS CPU vector search, BM25 keyword search, and hybrid retrieval/ranking.
- Support English, Urdu script, Roman Urdu, and mixed-language questions. Normalize common Urdu/Roman Urdu spelling variants where useful.
- Preserve source references so later answers can identify which clinic document supports a response.
- Add a small, repeatable retrieval evaluation set containing direct questions, follow-ups, misspellings, cross-language queries, and unanswerable questions.

**Acceptance criteria**
- [x] The index can be built from a clean checkout and reloaded after restart.
- [x] Re-running ingestion does not create duplicate chunks.
- [x] Relevant facts can be retrieved from both PDF and structured source content.
- [x] English, Urdu-script, Roman Urdu, and mixed-language test queries retrieve useful evidence, including when query and source language differ.
- [x] Low-confidence or unsupported questions are identified rather than forced to a guessed answer.
- [x] Retrieval results include source metadata and traceable evidence.

---

## Phase 03 — AI Receptionist, Conversation Memory and Clinic Workflows

**Status: COMPLETED & VERIFIED**

**Goal:** Turn retrieval into a natural, safe receptionist that can handle ongoing conversations and basic clinic requests.

**Build**
- Integrated Gemini Flash through a centralized, configurable AI service (`app/ai/gemini_client.py`) using official `google.genai` SDK with `v1beta` API version, zero thinking budget (`thinking_budget=0`), and model fallback hierarchy.
- Built Aevora AI receptionist persona: warm, professional, concise, virtual assistant, strictly grounded in retrieved evidence.
- Language matching across English, Urdu script, and Roman Urdu.
- Multi-turn conversation persistence in SQLite using SQLAlchemy 2.0 ORM (`app/models/` and `app/database/`). Sender and thread session isolation guaranteed.
- Progressive appointment intake state machine (`app/services/appointment_service.py`): collects missing slots turn-by-turn, presents full summary, requires explicit patient confirmation, and records with status `pending_staff_confirmation` (never "booked").
- Medical safety filter (`app/ai/safety.py`): immediate 1122 emergency redirection and clinical diagnosis/prescription deflection.
- Local staff triage management endpoints (`GET /api/v1/staff/handoffs`, `PATCH /api/v1/staff/handoffs/{id}`, `GET /api/v1/staff/appointments`).
- Complete test suite: 46 automated passing tests across project foundation, RAG retrieval, safety, appointment workflows, and multilingual conversation.

**Acceptance criteria**
- [x] Answers to clinic questions are grounded in retrieved evidence and do not fabricate prices, doctors, schedules, policies, or services.
- [x] Multi-turn conversations retain relevant context without leaking information between senders.
- [x] Language matching works across the agreed language/script set and is tested, not merely assumed.
- [x] Appointment requests and handoffs persist correctly and survive application restarts.
- [x] The assistant distinguishes a received request from a confirmed appointment.
- [x] Medical boundary and emergency scenarios behave safely.

---

## Phase 04 — WhatsApp Integration and Voice Conversations

**Status: Completed & Verified (November 14, 2026)**

**Goal:** Connect the working receptionist to WhatsApp and support voice-note input, with spoken replies where technically reliable.

**Build**
- Integrated the official Meta WhatsApp Cloud API (Graph API `v22.0`); no unofficial browser scraping or WhatsApp Web automation.
- Implemented webhook verification (`hub.mode`, `hub.verify_token`, `hub.challenge`), HMAC-SHA256 signature validation (`X-Hub-Signature-256`), and payload parsing producing `NormalizedMessageEvent`.
- Implemented durable `InboundEvent` queue in SQLite with unique `provider_message_id` constraint, transactional processing, and background `EventWorker` with bounded retries and exponential backoff.
- Outbound messages sent via HTTPX Graph API client to recipient numbers within customer service window.
- Voice note processing: Graph API media URL lookup, trusted Meta CDN domain validation (`lookaside.fbsbx.com`, `*.facebook.com`, `*.fbcdn.net`), authenticated download to `temp_audio/` within 16MB/180s limits, and guaranteed cleanup on success and error.
- Audio conversion to 16kHz mono WAV using FFmpeg with automatic fallback to bundled binary (`imageio-ffmpeg`).
- Faster-Whisper transcription using multilingual model, auto-probing CUDA GPU with graceful CPU `int8` fallback, and thread-pool offloading.
- Full end-to-end routing: transcribed voice notes and text messages feed directly into Phase 03 `ConversationService.process_chat(...)` with identical RAG grounding, appointment state machine, and medical safety guardrails.
- Spoken voice replies supported via `edge-tts` (disabled by default for control and privacy), with guaranteed non-blocking fallback to text.
- Full automated test suite: 76 passing tests with zero skipped or failing tests.

**Acceptance criteria**
- [x] A person can message the Meta test number from an authorized personal WhatsApp account and receive a real Aevora response.
- [x] Duplicate webhook deliveries do not create duplicate replies or appointment requests.
- [x] Text, media, and unsupported messages are handled safely.
- [x] English and Urdu voice notes can be transcribed and processed; mixed Urdu-English is tested and known limitations are documented.
- [x] Voice replies work only when the chosen TTS output is accepted and plays correctly in WhatsApp; otherwise a clear text fallback is sent.
- [x] Restarting the app does not erase persisted conversations or requests.

---

## Phase 05 — End-to-End Quality, Security, Deployment and Final Demo

**Goal:** Make the complete demo dependable, presentable, and easy for an employer to run and evaluate.

**Build**
- Add integration and end-to-end tests across RAG, language handling, Gemini, memory, appointments, handoff, WhatsApp webhooks, and voice.
- Test at least 50 realistic scenarios, including unknown facts, conflicting or missing evidence, follow-ups, Roman Urdu spelling variation, language switching, multiple senders, duplicate webhooks, corrupt audio, AI/API outages, appointment updates, and medical-safety boundaries.
- Review security: secrets only in environment configuration, no secrets in Git/logs, sender isolation, rate limits, request validation, webhook verification, upload limits, temporary-file cleanup, redacted logs, and documented retention/deletion behavior.
- Add resilience checks for Gemini, Meta, database, retrieval, and voice failures. Ensure CPU-only operation is supported; GPU acceleration may be added only as an optional optimization if appropriate hardware is available, never as a requirement.
- Optimize only after measuring: cache/load embedding models efficiently, persist the index, bound history and concurrency, avoid unnecessary model calls, and prevent blocking speech workloads from stalling API requests.
- Prepare local demo startup/shutdown scripts and a clear setup guide. The no-cost demo path is local FastAPI + local SQLite/FAISS + Gemini API free tier where available + Cloudflare Quick Tunnel.
- Document that the local machine must stay on, a Quick Tunnel URL is temporary, and this single-instance local setup is for demonstration rather than multi-instance production.
- Prepare the final README, architecture overview, API notes, configuration instructions, Meta setup guide, test report, known limitations, and employer demo walkthrough.
- **GUI is optional and should not delay the WhatsApp MVP.** If a staff dashboard is included, implement it only after the backend workflows are stable. It must have a deliberate visual system, excellent spacing and typography, responsive behavior, accessible contrast, polished states, and meaningful information hierarchy. Preferred palette: deep navy `#142B3A`, teal `#126E75`, warm off-white `#F7F6F2`, pale mint `#EAF3F1`, restrained coral `#C96F5D`, and muted gold `#B89455`.

**Acceptance criteria**
- [ ] Critical unit, integration, and end-to-end tests pass; failures and skipped tests are explicitly reported.
- [ ] No known critical sender-isolation, secret-leakage, duplicate-processing, or unsafe medical-response issue remains.
- [ ] The complete demo can be started from documented instructions on the target computer without AWS/Azure or paid hosting.
- [ ] Meta test-number webhook flow works through the documented tunnel setup.
- [ ] The final demo checklist, test evidence, and limitations are available in the repository.
- [ ] Any GUI included is tested at desktop and mobile widths and reviewed for visual consistency; no GUI is claimed complete based on screenshots alone.

---

## Rules for Antigravity Across All Phases

1. Work on one phase at a time. Do not begin the next phase until the current phase's acceptance criteria have been checked.
2. Inspect the current repository and preserve working code. Do not recreate or overwrite Phase 01 work.
3. Do not use fake data paths, stub functions, mocked success responses, or placeholder implementations to claim a feature is complete. Mocks are allowed in isolated tests when clearly labelled.
4. Write tests alongside implementation. Run the relevant test suite and show actual command output or a factual summary of it.
5. Never hardcode API keys, access tokens, secrets, or personal patient data. Keep `.env` out of version control.
6. Update `PROJECT_STATUS.md`, the README, and `DEVELOPMENT_ROADMAP.md` as the implementation changes.
7. Record architecture decisions and trade-offs in `docs/DECISIONS.md`.
8. Document unresolved issues, external account requirements, free-tier limitations, and any feature that could not be verified.
9. Do not claim a WhatsApp, voice, deployment, or GUI feature works until it has been tested through the real integration path appropriate to the demo.
10. Prefer a maintainable modular monolith. Do not add paid services, cloud infrastructure, microservices, or complex orchestration without a demonstrated need.
