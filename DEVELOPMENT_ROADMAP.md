# Aevora AI — Revised Development Roadmap

## Roadmap Decision

Keep the current **Phase 01** complete and verified. The development plan is organized into **five focused, milestone-driven implementation phases** (the foundation plus four comprehensive capability phases).

Each phase must be implemented, tested, and documented before moving on. Do not skip acceptance criteria just to finish a phase faster.

---

## Phase Overview

| Phase | Milestone Title | Status | Primary Focus |
| :---: | :--- | :---: | :--- |
| **01** | **Project Foundation** | **COMPLETED** | FastAPI modular monolith, typed Pydantic config, logging, health check, automated tests, and core docs. |
| **02** | **Clinic Knowledge Base, RAG & Multilingual Retrieval** | Pending | PDF/JSON ingestion, chunking, multilingual embeddings, FAISS CPU + BM25, Urdu/Roman Urdu retrieval. |
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
- [ ] The index can be built from a clean checkout and reloaded after restart.
- [ ] Re-running ingestion does not create duplicate chunks.
- [ ] Relevant facts can be retrieved from both PDF and structured source content.
- [ ] English, Urdu-script, Roman Urdu, and mixed-language test queries retrieve useful evidence, including when query and source language differ.
- [ ] Low-confidence or unsupported questions are identified rather than forced to a guessed answer.
- [ ] Retrieval results include source metadata and traceable evidence.

---

## Phase 03 — AI Receptionist, Conversation Memory and Clinic Workflows

**Goal:** Turn retrieval into a natural, safe receptionist that can handle ongoing conversations and basic clinic requests.

**Build**
- Integrate Gemini through a centralized, configurable AI service. Keep the model name configurable rather than hardcoded.
- Build the receptionist persona and response policy: warm, professional, concise, human-sounding without pretending to be a human staff member.
- Ground clinic-specific answers in Phase 02 retrieval. If evidence is missing or conflicting, say so and offer staff handoff; never invent clinic facts.
- Match the user's language and script where practical: English, Urdu, Roman Urdu, or mixed language.
- Add natural follow-up handling, greetings, clarification questions, and bounded conversation context.
- Add SQLite + SQLAlchemy persistence for conversations, messages, appointment requests, handoffs, and processed-event/idempotency records. Keep patient data minimal and isolate every sender's records.
- Support appointment enquiries and requests: collect only necessary details, save a request, and clearly say it is a request rather than a confirmed booking unless a real scheduling integration exists.
- Support appointment request status, cancellation/update of demo requests, and staff handoff records.
- Implement medical-safety behavior: no diagnosis, prescriptions, or unsupported treatment advice; urgent/emergency symptoms should receive clear direction to seek immediate professional/emergency care; route medical questions outside the receptionist's scope to a human professional.
- Add clear error handling, timeouts, bounded retries, and safe fallbacks for AI or database failures.

**Acceptance criteria**
- [ ] Answers to clinic questions are grounded in retrieved evidence and do not fabricate prices, doctors, schedules, policies, or services.
- [ ] Multi-turn conversations retain relevant context without leaking information between senders.
- [ ] Language matching works across the agreed language/script set and is tested, not merely assumed.
- [ ] Appointment requests and handoffs persist correctly and survive application restarts.
- [ ] The assistant distinguishes a received request from a confirmed appointment.
- [ ] Medical boundary and emergency scenarios behave safely.

---

## Phase 04 — WhatsApp Integration and Voice Conversations

**Goal:** Connect the working receptionist to WhatsApp and support voice-note input, with spoken replies where technically reliable.

**Build**
- Integrate the official Meta WhatsApp Cloud API; do not use unofficial WhatsApp Web automation.
- Implement webhook verification, incoming message parsing, sender/conversation mapping, outbound replies, delivery/error handling, duplicate-event protection, and safe webhook logging.
- Validate webhook signatures where supported by the configured Meta app, validate inputs, and handle unsupported message types gracefully.
- Start with Meta's test number and authorized test recipient. Use Cloudflare Quick Tunnel to expose the local FastAPI webhook for development.
- For voice notes: fetch media via Meta's API, validate file type/size, use temporary storage and cleanup, convert formats with FFmpeg, and transcribe using Faster-Whisper.
- Send the transcription through the same receptionist, RAG, and memory pipeline used for text messages.
- Add a spoken-response path using Edge TTS only as a best-effort option. Verify Meta-supported audio formats and actual WhatsApp voice-note behavior. Always retain a text fallback if synthesis, upload, or playback format fails.
- Keep audio processing off the FastAPI event loop using bounded background/thread execution and concurrency limits. Choose Whisper model size based on the machine's actual resources; CPU operation must remain supported.

**Acceptance criteria**
- [ ] A person can message the Meta test number from an authorized personal WhatsApp account and receive a real Aevora response.
- [ ] Duplicate webhook deliveries do not create duplicate replies or appointment requests.
- [ ] Text, media, and unsupported messages are handled safely.
- [ ] English and Urdu voice notes can be transcribed and processed; mixed Urdu-English is tested and known limitations are documented.
- [ ] Voice replies work only when the chosen TTS output is accepted and plays correctly in WhatsApp; otherwise a clear text fallback is sent.
- [ ] Restarting the app does not erase persisted conversations or requests.

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
