# Architecture Decision Records (ADRs)

> This document tracks key technical decisions, architectural patterns, and structural choices for Aevora AI.

---

## ADR 001: Python + FastAPI Modular Monolith Architecture
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: The project requires high performance, async I/O capability for WhatsApp webhook callbacks, structured API validation, and high testability without the operational overhead of microservices.
- **Decision**: Adopt a modular monolith built with **Python 3.11+** and **FastAPI**. Application domains (`core`, `api`, `ai`, `rag`, `whatsapp`, `voice`, `database`, `services`) are separated into clean internal packages.
- **Consequences**: Enables rapid local development and straightforward deployment while keeping code boundaries clean and maintainable.

---

## ADR 002: Free-First Local Demo Deployment Model
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: The assessment demonstration must be reproducible on local developer machines without introducing billable cloud infrastructure (AWS, Azure, GCP VM instances, paid DBs).
- **Decision**: Deploy the application locally on the workstation and expose the FastAPI webhook listener to Meta's servers using a free temporary **Cloudflare Quick Tunnel** (`cloudflared tunnel --url http://localhost:8000`).
- **Consequences**: Zero hosting expense and instant setup. Webhook URLs are temporary and must be re-registered in the Meta Developer Console when restarted.

---

## ADR 003: Official Meta WhatsApp Cloud API over Browser Automation
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Communicating over WhatsApp can be achieved via official cloud APIs or unofficial browser scraping/Puppeteer libraries.
- **Decision**: Use the **Official Meta WhatsApp Cloud API**.
- **Consequences**: Guarantees reliability, standard HMAC webhook security verification, official media handling, and eliminates ban risks associated with browser automation.

---

## ADR 004: Configurable Gemini Flash Integration
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Generative LLM responses require high speed, strong multilingual capability (Urdu, Roman Urdu, English), and low inference cost.
- **Decision**: Use **Google Gemini Flash** via Google AI Studio API. The exact model identifier (e.g., `gemini-3.8-flash`) is dynamically loaded from application settings rather than hardcoded.
- **Consequences**: Decouples the codebase from specific model deprecations and ensures fast responses suitable for conversational messaging.

---

## ADR 005: SQLite for Local Single-Instance Demo Persistence
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Conversation sessions, appointment requests, and deduplication state must be persisted locally without requiring a dedicated external database service (e.g., PostgreSQL or Redis).
- **Decision**: Use **SQLite** paired with **SQLAlchemy ORM**.
- **Consequences**: Zero infrastructure dependencies, completely self-contained local database file (`aevora.db`), and thread-safe local access.

---

## ADR 006: Custom In-Process Hybrid RAG (FAISS CPU + BM25 + multilingual-e5-small)
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Hosted vector databases (Pinecone, Weaviate) incur recurring costs and external network latency. Frameworks like LangChain add abstraction bloat and breaking dependency churn.
- **Decision**: Implement a custom, lightweight Python RAG pipeline combining:
  1. `PyMuPDF` for PDF document extraction.
  2. `multilingual-e5-small` for localized multilingual dense vector embeddings running on CPU.
  3. `FAISS CPU` for fast vector indexing and top-k retrieval.
  4. `BM25` for keyword search (vital for exact doctor names, room numbers, and medical terms).
  5. Reciprocal Rank Fusion (RRF) to combine dense and sparse rankings.
- **Consequences**: Completely local, cost-free, transparent, reproducible, and runnable on CPU.

---

## ADR 007: WhatsApp as Primary User Interface (No MVP Web Dashboard)
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Clinic patients interact naturally through messaging applications. Building an unvetted web dashboard adds unnecessary frontend complexity and distracts from conversational intelligence.
- **Decision**: Keep WhatsApp as the primary patient-facing interface for the MVP. Any administrative GUI will only be considered as a separate design phase after core backend conversational workflows are stable.
- **Consequences**: Focused engineering effort on the primary conversational experience.

---

## ADR 008: Fictional NovaCare Clinic Corpus for Testing
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Evaluating medical receptionist workflows requires comprehensive clinic data while respecting patient privacy and healthcare regulations.
- **Decision**: Use a synthetic, fictional clinic dataset representing **NovaCare Medical Centre**, maintained in parallel across `NovaCare_Medical_Centre_RAG_Knowledge_Base.pdf` and `NovaCare_RAG_Source_of_Truth.json`.
- **Consequences**: Enables rigorous testing and benchmarking without exposing real-world clinical records.

---

## ADR 009: Canonical JSON Source of Truth with Human-Readable PDF Provenance
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: The clinic corpus is provided as both a structured JSON file and a formatted PDF document. In automated RAG systems, unstructured PDF tables and page breaks can fragment entity attributes.
- **Decision**: Treat `NovaCare_RAG_Source_of_Truth.json` as the canonical structured source of truth for all factual entities (doctors, fees, hours, policies), while extracting `NovaCare_Medical_Centre_RAG_Knowledge_Base.pdf` for page-level human provenance and narrative text. When near-identical text occurs, the canonical JSON chunk absorbs the PDF page provenance to avoid duplicate evidence.
- **Consequences**: Guaranteed factual integrity with zero attribute fragmentation, paired with traceable human-readable PDF citations.

---

## ADR 010: intfloat/multilingual-e5-small Embedding Model with Prefix Convention
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: The assistant must support English, Urdu script, and Roman Urdu. Hosted embedding APIs (OpenAI, Voyage) incur recurring costs and latency.
- **Decision**: Use `intfloat/multilingual-e5-small` via `sentence-transformers`, running locally on CPU. Strictly follow the E5 instruction prefix standard: prepend `passage: ` to index documents and `query: ` to incoming user search queries. Embeddings are L2-normalized during encoding.
- **Consequences**: High-quality multilingual representation across English, Urdu, and Roman Urdu with zero cloud cost and low memory footprint (~470MB model).

---

## ADR 011: FAISS CPU Flat Inner Product on Normalized Vectors
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Approximate nearest neighbor (ANN) indexes (e.g. HNSW or IVF) introduce quantization noise and are unnecessary for small-to-medium corpora (< 100,000 vectors).
- **Decision**: Use `faiss-cpu` with `IndexFlatIP` (Flat Inner Product). Since vectors are L2-normalized, inner product strictly equals cosine similarity. Row IDs are mapped deterministically to chunk IDs via `chunks_metadata.json`.
- **Consequences**: Exact, mathematically optimal nearest-neighbor search with zero recall degradation, instant index build, and CPU compatibility.

---

## ADR 012: Robust BM25Okapi Sparse Retrieval with Multilingual Tokenization & Alias Expansion
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Exact doctor names, numeric fees, and room numbers require lexical matching. Standard tokenizers strip Urdu or produce negative IDFs on small corpora.
- **Decision**: Implement `BM25KeywordSearch` using a Unicode-aware regex tokenizer that preserves Urdu script and Latin alphanumeric terms. Apply a floor IDF clamp (`RobustBM25Okapi`) to eliminate Robertson-Spärck Jones negative term weight anomalies on compact collections. Add a conservative Roman Urdu alias expansion layer (`fees` -> `charges`, `pkr`; `kab` -> `timings`, `hours`).
- **Consequences**: Exceptional exact-match accuracy for doctor names, numbers, and localized keywords across English, Urdu, and Roman Urdu.

---

## ADR 013: Reciprocal Rank Fusion (RRF) Hybrid Search with Evidence Deduplication
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Dense vector similarity scores (cosine in [0, 1]) and sparse BM25 scores (unbounded [0, $\infty$)) operate on incompatible numerical scales and cannot be naively added.
- **Decision**: Combine vector and keyword rankings using Reciprocal Rank Fusion: $RRF(c) = w_{vec} \cdot \frac{1}{60 + r_{vec}} + w_{kw} \cdot \frac{1}{60 + r_{kw}}$, with $w_{vec}=0.5$ and $w_{kw}=0.5$.
- **Consequences**: Robust, scale-invariant rank combination that prevents either search modality from dominating the other.

---

## ADR 014: Independent Versioned Evaluation Benchmark and Threshold Calibration
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: In Phase 03, the LLM receptionist must refuse out-of-domain or unanswerable requests rather than hallucinating clinic facts.
- **Decision**: Maintain a separate 35-query benchmark evaluation dataset (`data/evaluation_queries.json`) spanning English, Urdu, Roman Urdu, Mixed, and Unanswerable queries. Calibrate an evidence sufficiency threshold: queries with top RRF score $< 0.015$ or vector score $< 0.84$ without strong keyword matches trigger `insufficient_evidence=True`.
- **Consequences**: Achieved 100% Recall@5 across all 31 answerable test queries and enabled automated regression testing of retrieval accuracy.

---

## ADR 015: Google GenAI Client with v1beta Developer Instruction & Zero Thinking Budget
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Phase 03 requires generating natural, persona-aligned receptionist answers in English, Urdu, and Roman Urdu. The official Google GenAI SDK (`google.genai`) defaults to API version `v1` which blocks system developer instructions, and default thinking models allocate reasoning tokens from the output token limit causing truncation.
- **Decision**: Use `google.genai.Client` with `http_options={'api_version': 'v1beta'}` to support system instructions. Explicitly configure `thinking_config=types.ThinkingConfig(thinking_budget=0)` to avoid output token starvation and reduce latency to < 3 seconds. Configure `gemini-2.5-flash` with dynamic fallback models.
- **Consequences**: Instantaneous, complete, persona-grounded generation with reliable system prompt adherence across all three languages.

---

## ADR 016: Progressive Appointment Intake State Machine with Explicit Confirmation
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Booking clinic appointments over messaging requires collecting patient name, doctor/specialty, preferred date, preferred time, and callback phone number without clinical integration errors. A virtual receptionist cannot claim an appointment is directly booked into an electronic health record.
- **Decision**: Implement a progressive state machine (`AppointmentService`) in SQLite that collects missing slots turn-by-turn. When all 5 slots are collected, present a full summary and require explicit patient confirmation (`Yes`/`Haan`) before recording. The appointment status is strictly set to `pending_staff_confirmation` (never "booked").
- **Consequences**: Prevents premature or fabricated appointment reservations, avoids patient misunderstandings, and guarantees clinic reception staff oversight.

---

## ADR 017: Deterministic Medical Guardrails & Human Staff Triage APIs
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Healthcare virtual assistants must never provide clinical diagnoses or prescriptions, and acute medical emergencies must be redirected immediately to emergency rescue.
- **Decision**: Implement a deterministic regex-based safety filter (`app/ai/safety.py`) evaluated before LLM generation. Emergencies (chest pain, stroke, unconsciousness) immediately return 1122 redirection and trigger `HandoffRequest` (status: `pending`). Clinical advice requests (medicines, prescriptions, diagnoses) are deflected with an offer to schedule a doctor consultation. Provide staff management endpoints (`/api/v1/staff/handoffs` and `/api/v1/staff/appointments`) for local triage.
- **Consequences**: Patient safety is protected deterministically without relying solely on LLM safety filters, and human clinic staff have visibility into all escalations.

---

## ADR 018: Meta WhatsApp Cloud API Webhook HMAC-SHA256 & Verification Standard
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Meta WhatsApp Business Platform webhooks require cryptographic handshake verification via GET requests and payload integrity verification via POST requests with `X-Hub-Signature-256`. Webhook delivery timeouts from Meta are strict ($\le 5$ seconds), requiring instantaneous 200 OK responses.
- **Decision**: Implement `verify_webhook_token` with constant-time token comparison for GET verification. Implement `validate_signature` computing HMAC-SHA256 over raw bytes with constant-time digest comparison using `hmac.compare_digest`. Ensure the webhook route queues incoming messages immediately into a durable queue and returns 200 OK without blocking on downstream RAG, transcription, or LLM processing.
- **Consequences**: Prevents timing attacks, prevents forged webhook deliveries, and guarantees Meta webhook SLA compliance without timing out.

---

## ADR 019: Durable SQLite Inbound Event Queue & Idempotency
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Meta WhatsApp webhooks guarantee at-least-once delivery; network retries can send identical messages multiple times. In-flight crashes could drop user inquiries. Introducing Redis/Celery would violate the zero-cost local architecture constraint.
- **Decision**: Create an `InboundEvent` model in SQLite with a unique constraint on `provider_message_id`. Incoming events are deduplicated at insertion (`sqlite3.IntegrityError` or unique check). A lightweight in-process asynchronous `EventWorker` polls pending events, executes processing with bounded exponential backoff (up to 5 attempts), transitions events through `pending -> processing -> processed / failed`, and records the last error.
- **Consequences**: Zero infrastructure dependencies, reliable message idempotency, guaranteed persistence across server restarts, and automatic retries for transient failures.

---

## ADR 020: Faster-Whisper & Bundled FFmpeg Architecture with CPU/GPU Auto-Detection
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Incoming WhatsApp voice notes arrive in OGG/Opus format. Faster-Whisper requires 16kHz mono WAV input and CTranslate2 model execution. Users may run on machines with or without CUDA GPUs or system-level FFmpeg installed.
- **Decision**: Use `imageio-ffmpeg` to bundle a pre-compiled FFmpeg executable on Windows/Linux with automatic fallback from system `ffmpeg`. Implement `FasterWhisperTranscriber` with auto device detection: probes CUDA availability and cleanly falls back to CPU `int8` with multi-threading if GPU memory allocation fails. Enforce strict audio file bounds ($\le 16\text{MB}$, $\le 180\text{s}$) and verify Meta CDN host domains (`lookaside.fbsbx.com`, `*.facebook.com`, `*.fbcdn.net`).
- **Consequences**: Complete out-of-the-box local voice note transcription support without requiring external commercial speech APIs or manual FFmpeg binary installation.

---

## ADR 021: Non-Blocking Optional Spoken TTS with Text Fallback
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Receptionist voice notes may optionally be answered with spoken voice messages. However, TTS generation adds network latency and bandwidth overhead, and text messages remain the expected primary WhatsApp format for administrative answers.
- **Decision**: Integrate `edge-tts` behind an explicit opt-in setting `VOICE_REPLY_ENABLED` (default: `False`). If enabled, audio synthesis runs asynchronously and non-blockingly; any TTS failure logs a warning and falls back cleanly to the already-delivered text reply.
- **Consequences**: Zero risk to conversation flow or text delivery reliability while enabling optional high-quality multilingual speech synthesis.

---

## ADR 022: PBKDF2-HMAC-SHA256 Password Hashing & RFC 7519 JWT Staff Authentication
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Clinic staff require administrative access to view patient conversations, update appointment confirmation statuses, and resolve triage handoffs. Passwords must never be stored in plain text, and staff routes must be authenticated without relying on external identity providers (Auth0, Okta, Firebase) to respect the zero-cost requirement.
- **Decision**: Implement password security using Python's standard library `hashlib.pbkdf2_hmac` with SHA-256, 100,000 iterations, and a unique cryptographically random 32-byte salt per user. Implement stateless RFC 7519 session management using PyJWT (`HS256`, 8-hour expiry) backed by a configured `STAFF_JWT_SECRET`. Store credentials in a dedicated `StaffUser` table in SQLite and automatically seed the default admin account on startup if absent.
- **Consequences**: Standard-compliant cryptographic security with zero external paid infrastructure, zero third-party auth services, and stateless Bearer token validation for the staff dashboard UI.

---

## ADR 023: Role-Protected Single-Page Application (SPA) Staff Dashboard with Live Diagnostics
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Clinic reception staff need a clean, responsive web interface to oversee live operations, review multi-turn patient conversations with source citations, manage appointment requests, and action emergency/clinical handoffs. Heavy frontend frameworks (React, Next.js, Node.js) would complicate local single-machine evaluation.
- **Decision**: Build a zero-build vanilla HTML5, CSS3, and ES6 JavaScript Single-Page Application served directly by FastAPI under `/dashboard`. Adhere strictly to the NovaCare healthcare design tokens (Deep Navy `#142B3A`, Primary Teal `#126E75`, Warm Off-White `#F7F6F2`, Pale Mint `#EAF3F1`, Coral `#C96F5D`, Muted Gold `#B89455`). Support native bidirectional RTL rendering for Urdu scripts, live system diagnostics, appointment status confirmation toggles, and handoff resolution.
- **Consequences**: Instantaneous loading, zero npm/Node build toolchains, accessible responsive UI, and seamless integration with the FastAPI backend.

---

## ADR 024: Complete 7-Journey End-to-End Verification and Adversarial Hardening
- **Date**: 2026-11-14
- **Status**: Accepted
- **Context**: Virtual healthcare receptionists face real-world edge cases: multilingual dialect switching (Urdu, Roman Urdu, English), appointment cancellations, emergency triage, dosage/prescription inquiries, webhook forgery, oversized media payloads, and prompt injection attacks.
- **Decision**: Establish automated test coverage for all seven core user journeys (A: Clinic FAQ RAG, B: Multilingual conversation, C: WhatsApp text handling & idempotency, D: Voice note transcription, E: Appointment intake & cancellation, F: Human handoff triage, G: Deterministic medical safety boundaries). Implement adversarial security hardening with phone masking (`mask_phone_number`), strict payload limits (16MB), CDN host whitelisting, and deterministic prompt injection defense in `app/ai/safety.py`.
- **Consequences**: Comprehensive verification guarantee across 105 automated unit and integration tests with zero regressions across Phases 01 through 05.
