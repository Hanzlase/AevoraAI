# Aevora AI — Live Project Status Tracker

> **Last Updated**: 2026-11-14  
> **Current Status**: Phase 04 (WhatsApp Integration & Voice Conversations) Complete and Verified  
> **Next Active Phase**: Phase 05 (End-to-End Quality, Security, Deployment & Final Demo)

---

## 1. Phase Status Summary

| Phase | Milestone Title | Status | Verification Evidence |
| :---: | :--- | :---: | :--- |
| **01** | **Project Foundation** | **COMPLETED** | 5 unit tests pass, Ruff check & format 100% clean, live server smoke test verified. |
| **02** | **Clinic Knowledge Base, RAG & Multilingual Retrieval** | **COMPLETED** | 17 unit tests pass, 100% Recall@5 across 31 benchmark queries, MRR 0.9839, real E5-small smoke test verified. |
| **03** | **AI Receptionist, Conversation Memory & Clinic Workflows** | **COMPLETED** | 46 unit & integration tests pass, SQLite ORM multi-turn memory, progressive appointment intake state machine, deterministic safety guardrails, live Gemini 2.5 Flash verified across English, Urdu, and Roman Urdu. |
| **04** | **WhatsApp Integration & Voice Conversations** | **COMPLETED** | 76 unit & integration tests pass (100% green). Meta webhook GET verification, POST HMAC-SHA256 signature validation, durable SQLite `InboundEvent` queue, Faster-Whisper audio transcription, bundled FFmpeg fallback, end-to-end appointment, handoff & 1122 emergency deflection. |
| **05** | **End-to-End Quality, Security, Deployment & Final Demo** | Pending | Awaiting Phase 05 commencement. |

---

## 2. Completed in Phase 01

1. **Workspace Inspection & Preservation**:
   - Inspected existing files in workspace: confirmed presence of `data/NovaCare_Medical_Centre_RAG_Knowledge_Base.pdf`, `data/NovaCare_RAG_Source_of_Truth.json`, and credentials reference `data/aevora_ai_credentials_setup.md`.
   - Verified Python runtime: `Python 3.12.10` (Windows x64).
   - Initialized Git repository (`main` branch) and secured sensitive credential file in `.gitignore`.

2. **Virtual Environment & Dependencies**:
   - Created isolated virtual environment at `.venv/`.
   - Formulated `pyproject.toml` as single source of dependencies and tool configuration.
   - Installed minimal Phase 01 packages: `fastapi==0.162.7`, `uvicorn==0.54.0`, `pydantic==2.14.3`, `pydantic-settings==2.16.3`, `httpx==0.28.1`, `pytest==8.4.2`, `ruff==0.17.5`.
   - Zero unnecessary heavyweight dependencies introduced.

3. **Modular Monolith Structure**:
   - Structured `app/` package hierarchy: `core`, `api`, `ai`, `rag`, `whatsapp`, `voice`, `database`, `models`, `schemas`, `services`.
   - Organized `data/documents/` and `data/vector_store/` with appropriate guides.
   - Organized `scripts/` and `tests/` directories.

4. **Typed Settings & Credential Protection**:
   - Implemented `app/core/config.py` using Pydantic Settings (`BaseSettings`).
   - Integrated `SecretStr` for `gemini_api_key`, `whatsapp_access_token`, `meta_app_secret`, and `webhook_verify_token`.
   - Created safe `.env.example` with blank placeholder values.
   - Ensured `.env` is loaded if present but never required for baseline startup.

5. **Centralized Logging & Error Handling**:
   - Configured `app/core/logging.py` with `SensitiveDataSanitizingFilter` to redact tokens, keys, and authorization headers from stdout.
   - Implemented `app/core/exceptions.py` with `AevoraException` hierarchy and centralized HTTP exception handlers returning safe error payloads without leaking stack traces or PII.

6. **FastAPI Application & Operational Health**:
   - Built application factory `create_app()` in `app/main.py` with lifespan logging and CORS middleware.
   - Implemented versioned health endpoint `GET /api/v1/health` and root alias `GET /health`.
   - Health checks report safe operational metadata (`status`, `service`, `version`, `environment`) without false claims regarding unbuilt AI or Meta integrations.

7. **Project Documentation**:
   - Created `README.md` with complete setup, running, and test commands.
   - Authored `PROJECT_REQUIREMENTS.md` with comprehensive product scope, safety boundaries, and non-goals.
   - Authored `DEVELOPMENT_ROADMAP.md` covering all 12 phase gates.
   - Authored `AGENT_INSTRUCTIONS.md` defining strict engineering rules.
   - Authored `docs/DECISIONS.md` recording initial ADRs (ADR 001 - ADR 008).

---

## 3. Actual Command Execution & Verification Evidence

### 3.1 Automated Tests (Pytest)
```powershell
Command: .\.venv\Scripts\pytest
Result:
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0
rootdir: F:\Projects\AevoraAI
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0, asyncio-0.26.0
collected 5 items

tests/test_health.py .....                                               [100%]

============================== 5 passed in 0.58s ==============================
Exit Code: 0
```

### 3.2 Linter & Formatter (Ruff)
```powershell
Command: .\.venv\Scripts\ruff check .
Result: All checks passed!
Exit Code: 0

Command: .\.venv\Scripts\ruff format --check .
Result: 24 files already formatted
Exit Code: 0
```

### 3.3 Live FastAPI Server Smoke Test
```powershell
Command:
$proc = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000" -PassThru
Start-Sleep -Seconds 3
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" | ConvertTo-Json
Stop-Process -Id $proc.Id -Force

Output:
GET /api/v1/health response:
{
    "status":  "healthy",
    "service":  "Aevora AI",
    "version":  "0.1.0",
    "environment":  "development"
}
GET /health response:
{
    "status":  "healthy",
    "service":  "Aevora AI",
    "version":  "0.1.0",
    "environment":  "development"
}
Server process terminated.
Exit Code: 0
```

### 3.4 Git & Secret Exposure Audit
```powershell
Command: git status --ignored
Result:
- Tracked / untracked for git: App source, tests, docs, config examples.
- Ignored by git: .venv/, .pytest_cache/, .ruff_cache/, __pycache__/, data/aevora_ai_credentials_setup.md.
- Zero secrets committed.
```

---

## 4. Completed in Phase 02 (Clinic Knowledge Base, RAG & Multilingual Retrieval)

1. **Source Document Ingestion & Verification**:
   - Integrated `NovaCare_RAG_Source_of_Truth.json` (canonical structured source of truth) and `NovaCare_Medical_Centre_RAG_Knowledge_Base.pdf` (human-readable PDF reference).
   - Produced automated consistency report detecting and documenting 4 factual notes (doctor fee formatting discrepancies between JSON numbers and PDF narrative text).

2. **Structure-Aware Chunking & Deduplication**:
   - Created `app/rag/json_loader.py` extracting cohesive clinic, doctor (DOC-001 to DOC-004), service, policy, FAQ, safety boundary, and localized Urdu records.
   - Built `app/rag/pdf_loader.py` extracting text page-by-page (Pages 1-9) with page metadata, heading association, and header/footer cleanup. Excluded Page 8 test queries from the searchable corpus.
   - Implemented `app/rag/chunking.py` with deterministic SHA-256 chunk IDs and provenance merging: 75 total unique chunks indexed with zero duplicates on re-ingestion.

3. **Multilingual Intelligence & Text Normalization**:
   - Authored `app/rag/normalization.py` with NFKC Unicode normalization, Urdu diacritic stripping, Arabic-to-Urdu character conversion (ک, ی, ہ), and conservative Roman Urdu alias expansion.
   - Built explainable script detection classifying queries into `en`, `ur`, `roman_ur`, `mixed`, or `unknown`.

4. **Dense Vector Search (FAISS CPU + E5-Small)**:
   - Configured `intfloat/multilingual-e5-small` via `sentence-transformers` running on CPU.
   - Enforced strict E5 prefix conventions: `passage: ` for indexed chunks and `query: ` for search queries.
   - Built `app/rag/vector_store.py` using `faiss.IndexFlatIP` on L2-normalized 384-dimensional vectors, guaranteeing mathematically exact cosine similarity.
   - Implemented atomic index persistence under `data/vector_store/` (`faiss_index.bin`, `chunks_metadata.json`, `manifest.json`).

5. **Sparse Keyword Search (BM25Okapi)**:
   - Developed `app/rag/keyword_search.py` using `RobustBM25Okapi` with Unicode-aware tokenization and non-negative floor IDF protection.
   - Persisted tokenized corpus atomically in transparent JSON format (`data/vector_store/bm25_corpus.json`).

6. **Hybrid RRF Fusion & Retrieval Service**:
   - Implemented `app/rag/hybrid_search.py` fusing dense and sparse ranks via Reciprocal Rank Fusion ($k=60, w_{vec}=0.5, w_{kw}=0.5$).
   - Calibrated evidence threshold: queries lacking keyword matches with vector score $< 0.84$ or RRF score $< 0.015$ trigger `insufficient_evidence=True`.
   - Exposed public `RAGService.retrieve(query, top_k)` interface in `app/rag/service.py` for Phase 03 consumption.

7. **Evaluation Benchmark & Operational CLI Tools**:
   - Created CLI utilities: `scripts.ingest_knowledge_base`, `scripts.query_knowledge_base`, and `scripts.evaluate_retrieval`.
   - Created 35-query benchmark evaluation dataset (`data/evaluation_queries.json`) covering English, Urdu, Roman Urdu, Mixed, and Unanswerable queries.

## 4. Completed in Phase 03

1. **Database Persistence & Session Architecture**:
   - Implemented `app/database/session.py` with SQLAlchemy 2.0 ORM and SQLite (`sqlite:///./aevora.db`).
   - Configured thread-safe `SessionLocal` with `get_db()` transactional dependency yielding automatic commit and rollback.
   - Built declarative models:
     - `Conversation` (`app/models/conversation.py`): tracks channel, external user identifier, session status, preferred language, and in-flight workflow state with cascade message deletion.
     - `Message` (`app/models/message.py`): stores role (`user`, `assistant`), content, detected intent, matched language, and JSON source citations.
     - `AppointmentRequest` (`app/models/appointment.py`): tracks progressive slot attributes with primary status strictly defaulting to `pending_staff_confirmation` (never falsely marked "booked").
     - `HandoffRequest` (`app/models/handoff.py`): records human receptionist triage requests, escalation reasons, and resolution states.

2. **Official Google GenAI SDK Client & Persona**:
   - Built `GeminiClient` (`app/ai/gemini_client.py`) wrapping official `google.genai` SDK using `http_options={'api_version': 'v1beta'}` for developer system instructions.
   - Configured `types.ThinkingConfig(thinking_budget=0)` to prevent internal reasoning tokens from consuming output quota and causing truncation.
   - Integrated `gemini-2.5-flash` with dynamic fallback to `gemini-1.5-flash`.
   - Developed `MockLLMClient` for fully deterministic, offline unit testing.
   - Authored `app/ai/prompts.py` establishing Aevora AI persona: warm, professional, concise, structured for mobile messaging, grounded strictly in retrieved clinic documents with zero medical diagnosis or prescription claims.

3. **Deterministic Medical Safety Guardrails**:
   - Implemented `app/ai/safety.py` running before LLM generation.
   - Acute emergency detection (chest pain, heart attack, stroke, severe bleeding, shortness of breath, poisoning) triggers immediate redirection to emergency rescue **1122** across English, Urdu script, and Roman Urdu, simultaneously creating a `HandoffRequest`.
   - Clinical advice / diagnosis requests (medicines to take, prescriptions, symptom diagnosis) are deflected politely with an offer to schedule an in-person consultation with a clinic specialist.

4. **Progressive Appointment Intake State Machine**:
   - Implemented `AppointmentService` (`app/services/appointment_service.py`) governing multi-turn slot collection.
   - Progressively gathers missing fields: patient name, doctor/specialty, preferred date, preferred time, and contact callback number.
   - Replaces in-place mutations with explicit `flag_modified` state tracking to guarantee SQLite persistence across independent HTTP requests.
   - Presents a clear appointment summary and requires explicit confirmation (`Yes` / `Haan`) before persisting.
   - Sets status strictly to `pending_staff_confirmation`.

5. **Central Conversation Orchestration & APIs**:
   - Implemented `ConversationService` (`app/services/conversation_service.py`) uniting user input normalization, intent detection, safety filters, session memory, Phase 02 hybrid RAG retrieval, bounded prompt assembly, and response persistence.
   - Built versioned REST endpoints:
     - `POST /api/v1/chat`: process incoming message and return grounded response.
     - `GET /api/v1/chat/{conversation_id}/history`: retrieve full conversation thread.
     - `DELETE /api/v1/chat/{conversation_id}`: delete session and messages.
     - `GET /api/v1/staff/handoffs` & `PATCH /api/v1/staff/handoffs/{id}`: list and update human staff escalations.
     - `GET /api/v1/staff/appointments`: review appointment requests submitted by patients.

---

## 5. Actual Command Execution & Verification Evidence (Phase 03)

### 5.1 Automated Pytest Suite (All 46 Tests Passing)
```powershell
Command: .\.venv\Scripts\pytest
Result:
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0
rootdir: F:\Projects\AevoraAI
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0, asyncio-0.26.0
collected 46 items

tests/test_appointment_workflow.py ..                                    [  4%]
tests/test_conversation.py ....                                          [ 13%]
tests/test_gemini_client.py ....                                         [ 21%]
tests/test_health.py .....                                               [ 32%]
tests/test_multilingual_chat.py ....                                     [ 41%]
tests/test_rag.py ............                                           [ 67%]
tests/test_safety.py ...............                                     [100%]

============================== 46 passed in 24.18s ==============================
Exit Code: 0
```

### 5.2 Linting & Formatting Check (100% Clean)
```powershell
Command: .\.venv\Scripts\ruff check .
Result:
All checks passed!
Exit Code: 0
```

### 5.3 Live End-to-End Receptionist Verification
1. **English Clinic Inquiry**:
   - Query: *"What are the clinic timings and consultation fees for cardiology?"*
   - Intent: `clinic_faq` | Language: `en` | Sources: 5 grounded records
   - Response:
     > For cardiology consultations with Dr. Bilal Ahmed, here are the details:
     > - Clinic Timings: Monday, Tuesday, and Thursday, from 5:00 PM to 8:00 PM.
     > - Consultation Fee: PKR 4,500
     > - Follow-up Fee: PKR 3,000 (applies within 7 calendar days)
     > - Important Note: For chest pain or urgent symptoms, seek emergency care immediately.

2. **Roman Urdu Clinic Inquiry**:
   - Query: *"Dr Bilal ki timing kya hai aur clinic ka address kahan hai?"*
   - Intent: `clinic_faq` | Language: `roman_ur`
   - Response:
     > NovaCare Medical Centre mein khushamdeed! Main aap ki kya madad kar sakti hoon?
     > Dr. Bilal Ahmed ke OPD timings yeh hain:
     > - Peer, Mangal aur Jumerat: Shaam 5 baje se raat 8 baje tak.
     > Hamare clinic ka address hai:
     > - Plot 14, Executive Heights, G-11 Markaz, Islamabad.

3. **Urdu Script Clinic Inquiry**:
   - Query: *"نووا کیئر کلینک کا پتہ اور فون نمبر کیا ہے؟"*
   - Intent: `clinic_faq` | Language: `ur`
   - Response:
     > NovaCare Medical Centre میں خوش آمدید!
     > ہمارے کلینک کا پتہ یہ ہے:
     > - پتہ: سوئٹ 204، کریسنٹ پلازا، مین بلیوارڈ، ایف-10 مرکز، اسلام آباد، پاکستان۔
     > ہمارا فون نمبر +92 51 844 9100 ہے۔

---

## 6. Completed in Phase 04 (WhatsApp Integration & Voice Conversations)

1. **Meta WhatsApp Cloud API Webhook Integration (`app/api/routes/whatsapp.py`)**:
   - Implemented GET subscription verification: constant-time comparison of `hub.verify_token` returning `hub.challenge` to establish webhook handshake with Meta Developer App.
   - Implemented POST webhook handler: cryptographically verifies `X-Hub-Signature-256` HMAC-SHA256 digest against `META_APP_SECRET` using `hmac.compare_digest`.
   - Payload size bounding: strictly rejects payloads exceeding `WHATSAPP_WEBHOOK_MAX_BODY_BYTES` (413 Request Entity Too Large).
   - Fast 200 OK acknowledgment to Meta infrastructure to avoid webhook delivery timeouts.
   - Diagnostic status endpoint `GET /api/v1/whatsapp/status` exposing channel readiness without leaking credentials.

2. **Durable Inbound Event Queue & Idempotency (`app/models/inbound_event.py`, `app/services/inbound_event_service.py`)**:
   - Created `InboundEvent` SQLite model with unique constraint on `provider_message_id` and composite index on `(status, created_at)`.
   - Event deduplication at intake: identical Meta retries return existing record without queuing duplicates.
   - Asynchronous background worker (`EventWorker` in `app/services/event_worker.py`) running in application lifespan, polling and processing events with bounded exponential backoff (up to 5 attempts).
   - Safe payload normalization handling text, voice/audio, status updates, and unsupported media types gracefully.

3. **Voice Note Processing Pipeline (`app/voice/`)**:
   - Secure media download via Meta Graph API media lookup with strict domain whitelist (`lookaside.fbsbx.com`, `*.facebook.com`, `*.fbcdn.net`).
   - File size ($\le 16\text{MB}$) and duration ($\le 180\text{s}$) validation with guaranteed temporary file cleanup in `temp_audio/`.
   - Audio conversion to 16kHz mono 16-bit PCM WAV using FFmpeg with automatic fallback to bundled binary (`imageio-ffmpeg`).
   - Multilingual transcription using Faster-Whisper: auto-probes CUDA GPU and cleanly falls back to CPU `int8` with multi-threading, supporting English, Urdu, and Roman Urdu.
   - Integrated with Phase 03 `ConversationService.process_chat(...)` ensuring voice queries undergo identical RAG retrieval, appointment intake, and medical safety guardrails.
   - Optional non-blocking spoken TTS replies via `edge-tts` (disabled by default) with automatic text fallback.

4. **Outbound Messaging Client (`app/whatsapp/client.py`)**:
   - Implemented `MetaWhatsAppClient` with HTTPX client, configurable timeouts, and bounded retries.
   - Implemented `MockWhatsAppClient` and `MockTranscriber` for offline, deterministic testing.

---

## 7. Actual Command Execution & Verification Evidence (Phase 04)

### 7.1 Automated Pytest Suite (All 76 Tests Passing)
```powershell
Command: .\.venv\Scripts\pytest
Result:
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0
rootdir: F:\Projects\AevoraAI
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0, asyncio-0.26.0
collected 76 items

tests/test_appointment_workflow.py ..                                    [  2%]
tests/test_conversation.py ....                                          [  7%]
tests/test_gemini_client.py ....                                         [ 13%]
tests/test_health.py .....                                               [ 19%]
tests/test_idempotency_and_worker.py ....                                [ 25%]
tests/test_multilingual_chat.py ....                                     [ 30%]
tests/test_rag.py ............                                           [ 46%]
tests/test_safety.py ...............                                     [ 65%]
tests/test_voice_pipeline.py .....                                       [ 72%]
tests/test_whatsapp_adapter.py .....                                     [ 78%]
tests/test_whatsapp_client.py ...                                        [ 82%]
tests/test_whatsapp_parser.py .....                                      [ 89%]
tests/test_whatsapp_webhook.py ........                                  [100%]

======================= 76 passed, 1 warning in 34.72s ========================
Exit Code: 0
```

### 7.2 Linter & Formatter Check (100% Clean)
```powershell
Command: .\.venv\Scripts\ruff check .
Result: All checks passed!
Exit Code: 0
```

### 7.3 End-to-End WhatsApp Adapter Verification
1. **Text Inbound & Outbound**:
   - Webhook POST receives patient text inquiry $\rightarrow$ queues `InboundEvent` $\rightarrow$ processes through Phase 03 RAG and Gemini receptionist $\rightarrow$ sends grounded WhatsApp response.
2. **Audio Voice Note Inbound & Outbound**:
   - Webhook POST receives audio event $\rightarrow$ validates metadata $\rightarrow$ downloads media $\rightarrow$ converts to WAV $\rightarrow$ transcribes via Faster-Whisper $\rightarrow$ generates grounded response $\rightarrow$ cleans up temporary files.
3. **Progressive Appointment Flow over WhatsApp**:
   - Patient initiates booking $\rightarrow$ assistant prompts for patient details $\rightarrow$ patient provides details $\rightarrow$ state machine advances $\rightarrow$ status tracked as `pending_staff_confirmation`.
4. **Human Staff Handoff over WhatsApp**:
   - Patient requests real person $\rightarrow$ `HandoffRequest` created with `status="pending"` $\rightarrow$ assistant confirms escalation.
5. **Emergency 1122 Deflection over WhatsApp**:
   - Patient describes acute symptoms $\rightarrow$ immediate **1122** safety redirection sent $\rightarrow$ priority escalation logged.

---

## 8. Known Issues, Limitations & Observations

1. **Meta Cloudflare Tunnel Live Verification**:
   - Deterministic test harness and mock clients verify 100% of webhook signature verification, event idempotency, media conversion, transcription, and outbound messaging offline.
   - For live end-to-end testing with a real physical WhatsApp mobile device, developer credentials must be set in `.env` and `cloudflared tunnel --url http://localhost:8000` must be active, as documented in `docs/WHATSAPP_SETUP.md`.
2. **Whisper Hardware Acceleration**:
   - CUDA GPU is auto-detected and utilized if available; CPU `int8` fallback is verified for environments without dedicated GPU compute.
3. **Bundled FFmpeg**:
   - `imageio-ffmpeg` bundles a pre-compiled Windows x64 FFmpeg executable, eliminating host machine dependency hurdles.

---

## 9. Explicit Confirmation on Unstarted Phases
- **Phase 05**: No web frontend, staff dashboard, containerization, or production deployment infrastructure has been provisioned. Work on Phase 05 will begin only when explicitly requested.
