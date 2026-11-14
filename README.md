# Aevora AI

> **Healthcare conversations, made human.**

Aevora AI is an enterprise-grade multilingual WhatsApp clinic receptionist assistant designed for NovaCare Medical Centre (fictional demo clinic). It handles administrative clinic inquiries, provides doctor directory and fee information, collects appointment requests, processes patient voice notes, supports English, Urdu, and Roman Urdu, and safely routes uncertain or emergency scenarios to human staff.

---

## Phase 01: Architecture & Foundation
*Status: COMPLETED*

## Phase 02: Clinic Knowledge Base & Multilingual RAG
*Status: COMPLETED*

## Phase 03: AI Receptionist, Conversation Memory & Clinic Workflows
*Status: COMPLETED & VERIFIED*

## Phase 04: WhatsApp Cloud API & Voice Conversations
*Status: COMPLETED & VERIFIED*

Aevora AI connects directly to the official Meta WhatsApp Business Platform (Cloud API `v22.0`) and supports incoming voice-note transcription via Faster-Whisper.

### Key Capabilities in Phase 04
- **Meta WhatsApp Webhook (`app/api/routes/whatsapp.py`)**:
  - GET verification (`hub.mode`, `hub.verify_token`, `hub.challenge`) with constant-time equality checks.
  - POST HMAC-SHA256 signature validation (`X-Hub-Signature-256`) against `META_APP_SECRET`.
  - Immediate 200 OK response to comply with Meta's tight timeout SLA.
  - Diagnostic status endpoint: `GET /api/v1/whatsapp/status`.
- **Durable Event Queue & Idempotency (`app/services/inbound_event_service.py`, `app/models/inbound_event.py`)**:
  - Deduplicates events using unique `provider_message_id` in SQLite.
  - Asynchronous background worker (`EventWorker`) polls and executes pending events.
  - Bounded exponential retries (up to 5 attempts) with error tracking.
- **Voice Note Processing Pipeline (`app/voice/`)**:
  - Secure Meta CDN media download with host domain whitelist (`lookaside.fbsbx.com`, `*.facebook.com`, `*.fbcdn.net`).
  - Size ($\le 16\text{MB}$) and duration ($\le 180\text{s}$) validation.
  - Temporary audio file lifecycle in `temp_audio/` with guaranteed cleanup.
  - Automatic FFmpeg binary resolution: system `ffmpeg` on PATH with seamless fallback to bundled binary via `imageio-ffmpeg`.
  - Faster-Whisper transcription: auto-probes CUDA GPU with graceful fallback to CPU `int8` with multi-threading.
  - Direct routing into Phase 03 `ConversationService.process_chat(...)` with identical grounding, appointment state machine, and medical safety guardrails.
  - Optional non-blocking spoken TTS replies via `edge-tts` (disabled by default for privacy/control) with automatic text fallback.

For complete setup instructions, Cloudflare Quick Tunnel commands, and Meta Developer App configuration, see [WHATSAPP_SETUP.md](docs/WHATSAPP_SETUP.md).

---

### Key Capabilities in Phase 03
- **Google GenAI Client (`app/ai/gemini_client.py`)**: Uses the official Google GenAI SDK (`google.genai`) configured with `api_version="v1beta"`, `thinking_budget=0` (preventing reasoning token starvation and eliminating response truncation), and model fallback hierarchy (`gemini-2.5-flash`, `gemini-1.5-flash`).
- **Grounded Receptionist Persona (`app/ai/prompts.py`)**: Professional, warm, mobile-optimized, answering strictly from retrieved clinic evidence with zero hallucinations.
- **Deterministic Medical Safety Filter (`app/ai/safety.py`)**: Immediate **1122** redirection for acute medical emergencies across English, Urdu, and Roman Urdu; clinical advice/diagnosis deflection.
- **Conversation Memory (`app/database/`, `app/models/`)**: Thread-safe SQLite persistence using SQLAlchemy 2.0 ORM with cascade deletion and strict sender session isolation.
- **Progressive Appointment Intake State Machine (`app/services/appointment_service.py`)**: Multi-turn collection of patient name, doctor, preferred date, preferred time, and contact number. Requires explicit user confirmation before recording status strictly as `pending_staff_confirmation`.
- **Human Staff Triage APIs (`app/api/routes/staff.py`)**: Endpoints to review escalations (`GET /api/v1/staff/handoffs`), update status (`PATCH /api/v1/staff/handoffs/{id}`), and inspect appointment requests (`GET /api/v1/staff/appointments`).

---

## API Usage & Receptionist Interaction

### 1. Send a Chat Message
```powershell
# English Clinic Inquiry
curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
     -H "Content-Type: application/json" `
     -d '{"message": "What are the clinic timings and consultation fees for cardiology?"}'

# Roman Urdu Inquiry
curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
     -H "Content-Type: application/json" `
     -d '{"message": "Dr Bilal ki timing kya hai aur clinic ka address kahan hai?"}'

# Urdu Script Inquiry
curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
     -H "Content-Type: application/json" `
     -d '{"message": "نووا کیئر کلینک کا پتہ اور فون نمبر کیا ہے؟"}'
```

### 2. Multi-Turn Appointment Intake
```powershell
# Step 1: Initiate booking
curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
     -H "Content-Type: application/json" `
     -d '{"message": "I want to book an appointment with Dr. Bilal"}'

# Step 2: Continue using the returned conversation_id
curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
     -H "Content-Type: application/json" `
     -d '{"conversation_id": "<CONVERSATION_ID>", "message": "The patient is Ali Khan"}'
```

### 3. Review Conversation History & Delete
```powershell
# View full thread history
curl -X GET "http://127.0.0.1:8000/api/v1/chat/<CONVERSATION_ID>/history"

# Delete conversation session
curl -X DELETE "http://127.0.0.1:8000/api/v1/chat/<CONVERSATION_ID>"
```

### 4. Clinic Staff Triage
```powershell
# List pending human escalations
curl -X GET "http://127.0.0.1:8000/api/v1/staff/handoffs?status=pending"

# Update handoff status
curl -X PATCH "http://127.0.0.1:8000/api/v1/staff/handoffs/<HANDOFF_ID>" `
     -H "Content-Type: application/json" `
     -d '{"status": "in_progress"}'

# Review patient appointment requests
curl -X GET "http://127.0.0.1:8000/api/v1/staff/appointments"
```

### Technology Stack (Phase 01)
- **Language**: Python 3.11+ (Tested on Python 3.12.10)
- **Framework**: FastAPI + Uvicorn
- **Configuration**: Pydantic Settings (`pydantic-settings`)
- **Testing**: Pytest + HTTPX ASGI transport
- **Code Quality**: Ruff (linter & formatter)

---

## Getting Started

### Prerequisites
- Python 3.11 or newer (Python 3.12 recommended)
- Git

### 1. Environment Setup

#### Windows PowerShell
```powershell
# Clone or navigate into the project directory
cd f:\Projects\AevoraAI

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install project and development dependencies
pip install -e ".[dev]"
```

#### macOS / Linux
```bash
# Navigate into the project directory
cd aevora-ai

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install project and development dependencies
pip install -e ".[dev]"
```

### 2. Configuration

Copy the example environment configuration:

#### Windows PowerShell
```powershell
Copy-Item .env.example .env
```

#### macOS / Linux
```bash
cp .env.example .env
```

> **Note**: Phase 01 runs completely without real Gemini API keys or Meta WhatsApp credentials. All external integration secrets are optional at this stage.

---

## Running the Application

Start the local FastAPI development server:

```powershell
# Using the virtual environment
.\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running, access:
- **Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health) (or [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health))
- **Interactive OpenAPI Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Redoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Knowledge Base & Multilingual RAG Pipeline (Phase 02)

Aevora AI employs a custom in-process hybrid retrieval pipeline combining:
1. **Canonical Structured JSON Extraction**: Ingests `NovaCare_RAG_Source_of_Truth.json` preserving entity relationships (doctors, schedules, fees, policies, and localized Urdu FAQs).
2. **Page-Aware PDF Extraction**: Extracts `NovaCare_Medical_Centre_RAG_Knowledge_Base.pdf` via PyMuPDF with page provenance tracking and header/footer cleanup.
3. **Dense Vector Search**: Powered by `sentence-transformers` with `intfloat/multilingual-e5-small` (L2-normalized vectors) and `faiss-cpu` (Flat Inner Product). Uses `query: ` and `passage: ` prefixing.
4. **Sparse Keyword Search**: Multilingual `BM25Okapi` with Unicode-aware tokenization and conservative Roman Urdu alias expansion.
5. **Reciprocal Rank Fusion (RRF)**: Combines dense and sparse evidence into unified, ranked citations with duplicate suppression and thresholding for unanswerable queries.

> **Hardware Compatibility**: Runs by default on standard CPU. If a CUDA GPU is present, it can be optionally utilized by configuring `EMBEDDING_DEVICE=cuda` or `auto`.

### Ingesting the Knowledge Base
To parse source documents, generate embeddings, and build the FAISS/BM25 indexes:

```powershell
.\.venv\Scripts\python -m scripts.ingest_knowledge_base
```
*Index artifacts are persisted under `data/vector_store/` (`faiss_index.bin`, `chunks_metadata.json`, `bm25_corpus.json`, `manifest.json`).*

### Testing a Retrieval Query via CLI
To test evidence retrieval for any question in English, Urdu script, Roman Urdu, or Mixed language:

```powershell
.\.venv\Scripts\python -m scripts.query_knowledge_base "Dr Sana Malik ki fee kitni hai?"
```

### Running Retrieval Benchmark Evaluation
Aevora includes an evaluation dataset of 35 diverse benchmark queries (`data/evaluation_queries.json`):

```powershell
.\.venv\Scripts\python -m scripts.evaluate_retrieval
```

---

## Running Tests and Linting

### Run Automated Tests (Pytest)
```powershell
.\.venv\Scripts\pytest
```

### Run Linter and Formatting Checks (Ruff)
```powershell
# Check for lint violations
.\.venv\Scripts\ruff check .

# Check code formatting
.\.venv\Scripts\ruff format --check .
```

---

## Project Structure

```
aevora-ai/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application factory and entry point
│   ├── api/
│   │   ├── dependencies.py      # Dependency injection providers
│   │   └── routes/
│   │       └── health.py        # Safe operational health endpoint
│   ├── core/
│   │   ├── config.py            # Typed Pydantic settings with secret protection
│   │   ├── logging.py           # Structured, PII-safe logging configuration
│   │   └── exceptions.py        # Centralized exception hierarchy and handlers
│   ├── ai/                      # AI orchestration and prompts (Phase 03)
│   ├── rag/                     # Hybrid retrieval-augmented generation (Phase 02)
│   ├── whatsapp/                # Meta Cloud API webhooks & messaging (Phase 04)
│   ├── voice/                   # Faster-Whisper audio processing (Phase 04)
│   ├── database/                # SQLAlchemy & SQLite persistence (Phase 03)
│   ├── models/                  # Domain and ORM models (Phase 03)
│   ├── schemas/                 # Pydantic request/response schemas
│   └── services/                # Business logic services
├── data/
│   ├── documents/               # Clinic source documents (PDF & JSON)
│   └── vector_store/            # Local vector indices (FAISS)
├── docs/
│   └── DECISIONS.md             # Architecture Decision Records (ADRs)
├── scripts/                     # Operational utility scripts
├── tests/                       # Automated test suite
├── .env.example                 # Blank environment template
├── .gitignore                   # Version control ignore rules
├── pyproject.toml               # Single source of dependencies and tool configuration
├── PROJECT_REQUIREMENTS.md      # Full product requirements and scope boundaries
├── DEVELOPMENT_ROADMAP.md       # 5-phase delivery roadmap and criteria gates
├── AGENT_INSTRUCTIONS.md        # Architecture rules for ongoing engineering
└── PROJECT_STATUS.md            # Verified live project status and test logs
```

---

## Medical Disclaimer & Privacy Boundaries
- **Fictional Clinic**: All clinic facts, doctor directories, and pricing refer to the fictional NovaCare Medical Centre demo dataset.
- **No Medical Advice**: Aevora AI provides administrative clinic assistance only and never diagnoses conditions or prescribes treatments.
- **Emergency Escalation**: Immediate guidance is provided to redirect life-threatening emergencies to local emergency services.
- **Zero Secret Exposure**: Operational endpoints and logs never expose tokens, API keys, or patient sensitive information.
