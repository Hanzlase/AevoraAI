# Aevora AI

<div align="center">

```
    _                              _    ___ 
   / \   _____   _____  _ __ __ _ / \  |_ _|
  / _ \ / _ \ \ / / _ \| '__/ _` / _ \  | | 
 / ___ \  __/\ V / (_) | | | (_|/ ___ \ | | 
/_/   \_\___| \_/ \___/|_|  \__,_/_/   \_\___|
```

### Healthcare conversations, made human.

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Pytest Suite](https://img.shields.io/badge/tests-105%20passed%20%7C%200%20failed-brightgreen.svg)](tests/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Architecture](https://img.shields.io/badge/architecture-modular%20monolith-142B3A.svg)](docs/ARCHITECTURE.md)
[![Meta WhatsApp API](https://img.shields.io/badge/Meta%20WhatsApp-Cloud%20API%20v22.0-25D366.svg)](https://developers.facebook.com/docs/whatsapp/cloud-api)
[![Free Tier Friendly](https://img.shields.io/badge/cost-$0.00%20(zero%20cloud%20bill)-success.svg)](docs/DEPLOYMENT.md)

</div>

---

## 1. Project Introduction & Purpose

**Aevora AI** is an enterprise-grade, multilingual AI clinic receptionist and practice management platform developed for **NovaCare Medical Centre** (a realistic, fictional demo healthcare clinic).

Designed for hiring assessment demonstration, Aevora AI delivers a production-grade patient experience over WhatsApp and a clean administrative interface for clinic personnel, while adhering to a strict **zero-cost, free-tier-friendly local deployment constraint**. The system introduces **no paid cloud hosting (AWS, Azure, GCP)**, no paid vector databases (Pinecone, Weaviate), no paid message brokers (Redis, RabbitMQ), and no commercial messaging wrappers (Twilio).

### Core Design Philosophy
- **Factual Grounding**: Answers administrative questions strictly from approved clinic documents; never hallucinates doctor fees, schedules, or services.
- **True Multilingualism**: Seamlessly converses in English, Urdu script (اردو), and Roman Urdu with automatic dialect and script detection.
- **Deterministic Patient Safety**: Intercepts emergency symptoms (chest pain, stroke, breathing distress) with immediate **1122** redirection before generative LLMs are invoked. Refuses clinical diagnoses and prescriptions deterministically.
- **Staff Control**: Collects appointment requests through a 5-slot state machine with explicit patient confirmation, tracking all bookings as `pending_staff_confirmation` until human staff confirm them via the web dashboard.
- **Local Single-Instance Resilience**: Powered by local SQLite with thread-safe SQLAlchemy 2.0 ORM, local dense/sparse hybrid search (FAISS + BM25), and local speech transcription (Faster-Whisper).

---

## 2. Key Features

- **Multilingual WhatsApp Virtual Receptionist**: Direct integration with the official Meta WhatsApp Business Platform (Cloud API `v22.0`).
- **Hybrid Multilingual RAG**: Dense vector search (`sentence-transformers/multilingual-e5-small` + FAISS) combined with sparse BM25 keyword matching and Reciprocal Rank Fusion (RRF). Tested against 35 benchmark queries with **100% Recall@5 and 0.9839 MRR**.
- **Local Voice-Note Processing**: Inbound WhatsApp voice notes (OGG/Opus) are validated, converted via bundled FFmpeg, and transcribed locally with Faster-Whisper multilingual models with automatic CPU/GPU detection.
- **Progressive Appointment State Machine**: Turn-by-turn collection of Patient Name, Doctor/Specialty, Preferred Date, Preferred Time, and Phone Number. Requires explicit patient confirmation (`Yes`/`Haan`) and supports patient cancellations.
- **Human Receptionist Handoff**: Automatically escalates complex, frustrated, or explicit staff requests to a triage queue with dashboard alerting.
- **Staff Dashboard Single-Page Application (SPA)**: Zero-build web dashboard mounted at `/dashboard`. Features live KPI metrics, conversation viewer with source citations, appointment confirmation toggles, handoff triage workflows, and live system diagnostics.
- **Enterprise Security Hardening**: PBKDF2-HMAC-SHA256 password hashing (100,000 iterations), RFC 7519 JWT session authentication, webhook HMAC-SHA256 signature verification, patient PII phone masking (`mask_phone_number`), and strict cross-sender conversation isolation.

---

## 3. Screenshots & Visual Interface

The Staff Dashboard is styled according to the **NovaCare Healthcare Design System** using six deliberate semantic tokens: Deep Navy (`#142B3A`), Primary Teal (`#126E75`), Warm Off-White (`#F7F6F2`), Pale Mint (`#EAF3F1`), Restrained Coral (`#C96F5D`), and Muted Gold (`#B89455`).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [N] NovaCare Medical Centre | Staff Dashboard                     👤 admin (Reception) │
├───────────────┬────────────────────────────────────────────────────────────────────────┤
│ 📊 Overview   │ Total Conversations: 28 | Messages: 114 | Appointments: 6 | Alerts: 1 │
│ 💬 Chats      ├────────────────────────────────────────────────────────────────────────┤
│ 📅 Bookings   │ [Conversation Inspector]                   [Live Patient Transcript]   │
│ 🚨 Handoffs   │ > +92 300 ****4567 (Urdu Script)           👤 Patient (Voice Note):    │
│ 📚 Knowledge  │   "Dr Bilal ki fee kitni hai?"               "کیا کلینک کل کھلا ہے؟"   │
│ ⚙️ Diagnostics│ > +92 321 ****8901 (English)               🤖 Aevora AI:               │
│               │   "Appointment with Dr Sana"                 "جی ہاں، نووا کیئر کلینک" │
│               │                                              Sources: General Policies │
└───────────────┴────────────────────────────────────────────────────────────────────────┘
```

> **Visual Interface Assets**:
> - Dashboard UI Entry: `http://127.0.0.1:8000/dashboard`
> - Default Admin Credentials: Username: `admin` | Password: `NovaCare2026!`
> - Responsive Breakpoints: Desktop (1280px+), Tablet (768px), and Mobile (375px) with bidirectional RTL support for Urdu typography (`Noto Nastaliq Urdu`).

---

## 4. Technology Stack

| Layer | Component | Description & Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI 0.110+** | High-performance asynchronous REST API framework with native OpenAPI/Swagger docs. |
| **Web Server** | **Uvicorn 0.28+** | ASGI web server running the async event loop on `http://127.0.0.1:8000`. |
| **Language & Runtime** | **Python 3.11 / 3.12** | Strict type hinting, standard `asyncio`, and modern union operators. |
| **Generative LLM** | **Google Gemini Flash** | Official `google-genai` SDK (`v1beta`), `thinking_budget=0`, model fallback hierarchy. |
| **Dense Embeddings** | **Multilingual E5-Small** | Local `sentence-transformers` model generating L2-normalized 384-dimensional embeddings. |
| **Dense Indexing** | **FAISS (faiss-cpu)** | In-process Flat Inner Product vector search with zero external database dependencies. |
| **Sparse Search** | **Rank-BM25** | In-process BM25Okapi keyword search with Roman Urdu alias expansion. |
| **Rank Fusion** | **Reciprocal Rank Fusion** | Custom RRF algorithm combining vector and keyword evidence into calibrated citations. |
| **Speech-to-Text** | **Faster-Whisper** | CTranslate2-based Whisper model auto-detecting CUDA GPU with CPU `int8` fallback. |
| **Audio Conversion** | **Bundled FFmpeg** | Resolves system `ffmpeg` on PATH with fallback to bundled `imageio-ffmpeg` binary. |
| **Messaging Channel** | **Meta WhatsApp Cloud API** | Official Graph API `v22.0` with HMAC-SHA256 signature verification and media download. |
| **Database & ORM** | **SQLite + SQLAlchemy 2.0** | Thread-safe local file persistence (`aevora.db`) with relational integrity and cascade deletes. |
| **Authentication** | **PBKDF2 + PyJWT** | PBKDF2-HMAC-SHA256 password hashing (100k rounds) + RFC 7519 JWT Bearer tokens. |
| **Staff Dashboard** | **Vanilla HTML5/CSS3/ES6** | Zero-build Single-Page Application (SPA) with responsive design and native Urdu RTL. |
| **Testing & Quality** | **Pytest + Ruff** | 105 automated unit and integration tests (100% passing) and zero-warning linter audits. |

---

## 5. Architecture Overview

```
                                  [ Patient Mobile Device ]
                                              │
                                   WhatsApp Cloud API v22.0
                                              │
                                (Cloudflare Quick Tunnel HTTPS)
                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ FastAPI Application (http://127.0.0.1:8000)                                            │
│                                                                                        │
│  ┌───────────────────────┐   ┌──────────────────────────────┐   ┌───────────────────┐  │
│  │ Meta Webhook Listener │   │ Staff Web Dashboard (SPA)    │   │ Chat REST API     │  │
│  │ HMAC-SHA256 Verify    │   │ Navy/Teal/Mint Token UI      │   │ /api/v1/chat      │  │
│  │ Immediate 200 OK      │   │ Bearer JWT Auth (8h expiry)  │   │ /api/v1/health    │  │
│  └──────────┬────────────┘   └──────────────┬───────────────┘   └─────────┬─────────┘  │
│             │ Inbound Event                 │ Admin Actions               │ Direct     │
│             ▼                               ▼                             ▼            │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Core Services Layer                                                              │  │
│  │                                                                                  │  │
│  │  ┌─────────────────────────┐  ┌───────────────────────┐  ┌────────────────────┐  │  │
│  │  │ Inbound Event Queue     │  │ Conversation Service  │  │ Appointment Engine │  │  │
│  │  │ SQLite Deduplication    │  │ Multi-Turn Memory     │  │ 5-Slot State Mach. │  │  │
│  │  │ Async Background Worker │  │ Language Detection    │  │ Confirm / Cancel   │  │  │
│  │  └───────────┬─────────────┘  └───────────┬───────────┘  └─────────┬──────────┘  │  │
│  │              │                            │                        │             │  │
│  │              ▼                            ▼                        ▼             │  │
│  │  ┌─────────────────────────┐  ┌───────────────────────┐  ┌────────────────────┐  │  │
│  │  │ Audio Processing        │  │ Deterministic Safety  │  │ Hybrid RAG Pipeline│  │  │
│  │  │ Faster-Whisper (CPU)    │  │ 1122 Emergency RegEx  │  │ Dense: E5 + FAISS  │  │  │
│  │  │ Bundled FFmpeg          │  │ Prescription Deflect  │  │ Sparse: BM25Okapi  │  │  │
│  │  │ Temp Audio Auto-Cleanup │  │ Injection Shield      │  │ Fusion: RRF Rank   │  │  │
│  │  └─────────────────────────┘  └───────────┬───────────┘  └─────────┬──────────┘  │  │
│  │                                           │                        │             │  │
│  │                                           ▼                        ▼             │  │
│  │                               ┌───────────────────────────────────────────────┐  │  │
│  │                               │ Centralized Gemini Client (Official SDK)      │  │  │
│  │                               │ gemini-2.5-flash (Fallback: gemini-1.5-flash) │  │  │
│  │                               │ Strict Evidence Grounding Persona             │  │  │
│  │                               └───────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┬──────────────────────────────┘  │
│                                                      │ ORM Persistence                 │
│                                                      ▼                                 │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Local SQLite File (`aevora.db`) via SQLAlchemy 2.0                               │  │
│  │ - conversations & messages (with citations) - inbound_events (idempotency queue) │  │
│  │ - appointment_requests (pending confirm)    - handoff_requests (human triage)    │  │
│  │ - staff_users (PBKDF2-HMAC-SHA256 salted)                                        │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Project Folder Structure

```
aevora-ai/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application factory, lifespan & static dashboard
│   ├── api/
│   │   ├── dependencies.py         # Database session & authentication dependencies
│   │   └── routes/
│   │       ├── health.py           # Safe operational health & diagnostic endpoints
│   │       ├── chat.py             # Multilingual patient chat REST API
│   │       ├── whatsapp.py         # Meta WhatsApp webhook verification & listener
│   │       └── staff.py            # Authenticated staff dashboard REST endpoints
│   ├── core/
│   │   ├── auth.py                 # PBKDF2 password hashing & RFC 7519 JWT session handling
│   │   ├── config.py               # Typed Pydantic Settings with SecretStr protection
│   │   ├── logging.py              # Sensitive data filter & phone number masking
│   │   └── exceptions.py           # Centralized exception hierarchy and error handlers
│   ├── ai/
│   │   ├── gemini_client.py        # Official Google GenAI SDK wrapper with fallback
│   │   ├── prompts.py              # Receptionist persona, multilingual rules & prompt templates
│   │   └── safety.py               # Deterministic 1122 emergency & medical safety guardrails
│   ├── rag/
│   │   ├── config.py               # RAG hyperparameters, weights, and thresholds
│   │   ├── pdf_loader.py           # Page-aware PDF document parser (PyMuPDF)
│   │   ├── json_loader.py          # Structured JSON parser preserving doctor & schedule schema
│   │   ├── text_splitter.py        # Semantic chunker with heading and section metadata
│   │   ├── embedder.py             # Multilingual E5-small embedding generator
│   │   ├── vector_store.py         # FAISS FlatIP index management and serialization
│   │   ├── bm25_search.py          # Multilingual BM25Okapi keyword search engine
│   │   └── retriever.py            # Reciprocal Rank Fusion (RRF) hybrid retrieval pipeline
│   ├── whatsapp/
│   │   ├── client.py               # Async HTTPX client for Meta Graph API v22.0
│   │   ├── webhook_parser.py       # Normalizes inbound text and audio payloads
│   │   └── adapter.py              # Routes WhatsApp events into the conversation engine
│   ├── voice/
│   │   ├── audio_processor.py      # Audio validation, bundled FFmpeg conversion & temp file cleanup
│   │   ├── transcription.py        # Faster-Whisper transcriber with CPU/GPU auto-detection
│   │   └── speech_service.py       # Optional non-blocking spoken TTS replies (edge-tts)
│   ├── database/
│   │   └── session.py              # SQLAlchemy engine, session maker, and schema initialization
│   ├── models/
│   │   ├── conversation.py         # Conversation, Message, and Citation ORM models
│   │   ├── appointment.py          # Progressive AppointmentRequest ORM model
│   │   ├── handoff.py              # Human staff HandoffRequest ORM model
│   │   ├── inbound_event.py        # InboundEvent idempotency queue ORM model
│   │   └── user.py                 # StaffUser ORM model with PBKDF2 hash and salt
│   ├── schemas/
│   │   ├── chat.py                 # Chat request, response, and citation schemas
│   │   ├── whatsapp.py             # Normalized WhatsApp event schemas
│   │   └── staff.py                # Staff login, metric, appointment, and handoff schemas
│   ├── services/
│   │   ├── conversation_service.py # Orchestrates RAG, LLM, safety, and conversation memory
│   │   ├── appointment_service.py  # 5-slot progressive appointment state machine
│   │   └── inbound_event_service.py# Deduplicating event queue and background worker
│   └── static/
│       └── dashboard/              # Staff Dashboard Single-Page Application
│           ├── index.html          # Semantic HTML5 accessible dashboard UI
│           ├── styles.css          # Design-system tokens, responsive layout, RTL Urdu styles
│           └── app.js              # Client state, Bearer auth interceptor, live API client
├── data/
│   ├── documents/                  # Clinic source documents (PDF & structured JSON)
│   │   ├── NovaCare_Medical_Centre_RAG_Knowledge_Base.pdf
│   │   └── NovaCare_RAG_Source_of_Truth.json
│   ├── vector_store/               # Persisted vector and keyword search index artifacts
│   │   ├── faiss_index.bin         # L2-normalized FAISS dense index
│   │   ├── bm25_corpus.json        # Tokenized sparse BM25 corpus
│   │   ├── chunks_metadata.json    # Chunk text, section, and page provenance metadata
│   │   └── manifest.json           # Ingestion timestamp, chunk counts, model metadata
│   └── evaluation_queries.json     # 35 benchmark evaluation queries across 4 categories
├── docs/                           # Technical documentation and operational runbooks
│   ├── ARCHITECTURE.md             # Subsystem architecture, Mermaid diagrams, hardware bounds
│   ├── DECISIONS.md                # 24 Architecture Decision Records (ADR 001 through ADR 024)
│   ├── DEMO_GUIDE.md               # 5–10 minute step-by-step employer demo evaluation script
│   ├── DEPLOYMENT.md               # Windows setup guide & cloud host feasibility audit
│   ├── SECURITY_AND_PRIVACY.md     # Secrets, PBKDF2/JWT auth, webhook HMAC, PII phone masking
│   ├── TEST_REPORT.md              # Test execution evidence across all 105 automated tests
│   ├── TROUBLESHOOTING.md          # Diagnostic runbooks for webhooks, audio, RAG, and dashboard
│   └── WHATSAPP_SETUP.md           # Step-by-step Meta Developer Platform and tunnel instructions
├── scripts/                        # Automation and CLI utility scripts
│   ├── setup_windows.ps1           # Automated 1-command Windows environment setup
│   ├── start_windows.ps1           # 1-command local application launch script
│   ├── run_tests.ps1               # Automated test suite and Ruff linter runner
│   ├── build_knowledge_base.ps1    # Automated knowledge base ingestion script
│   ├── ingest_knowledge_base.py    # Python CLI RAG indexing utility
│   ├── evaluate_retrieval.py       # Python CLI retrieval benchmark evaluation runner
│   └── query_knowledge_base.py     # Python CLI interactive retrieval query tool
├── tests/                          # 17 automated test modules (105 tests passing)
├── .env.example                    # Clean environment configuration template
├── .gitignore                      # Strict Git ignore rules for caches, db, credentials, audio
├── pyproject.toml                  # Single source of dependencies, Ruff, and Pytest configuration
├── PROJECT_REQUIREMENTS.md         # Full product specification and non-goals
└── DEVELOPMENT_ROADMAP.md          # 5-phase delivery roadmap and verified criteria gates
```

---

## 7. Windows Prerequisites

Before setting up Aevora AI, ensure your system meets these prerequisites:

1. **Operating System**: Windows 10 or Windows 11 (64-bit).
2. **Python Runtime**: **Python 3.11 or Python 3.12** (64-bit) installed and added to `PATH`.
   - Verify in terminal: `python --version`
3. **PowerShell**: Windows PowerShell 5.1+ or PowerShell 7 Core.
   - Script execution policy must allow running local scripts:
     ```powershell
     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
     ```
4. **Git**: Installed and available on `PATH`.
5. **Google Gemini API Key**: Free tier API key obtained from [Google AI Studio](https://aistudio.google.com/).
6. **Optional (For Live WhatsApp Webhooks)**:
   - Meta Developer Account with WhatsApp Cloud API test app.
   - Cloudflare `cloudflared` executable installed for Quick Tunnels.

---

## 8. Installation & Setup

### Option A: Automated One-Command Setup (Recommended)
Open Windows PowerShell in the project directory and run:

```powershell
.\scripts\setup_windows.ps1
```

This automated script will:
1. Verify Python 3.11+ is installed.
2. Create the virtual environment at `.venv/`.
3. Activate `.venv` and upgrade `pip`.
4. Install all dependencies from `pyproject.toml` in editable mode (`pip install -e .`).
5. Provision `.env` from `.env.example` if not already present.
6. Ingest source documents and build the hybrid RAG knowledge base.

---

### Option B: Manual Step-by-Step Setup

```powershell
# 1. Create isolated virtual environment
python -m venv .venv

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Upgrade pip and build tools
python -m pip install --upgrade pip setuptools wheel

# 4. Install dependencies in editable development mode
pip install -e ".[dev]"

# 5. Provision environment configuration
Copy-Item .env.example .env
```

---

## 9. Environment Variable Configuration

Open the `.env` file in your preferred text editor and configure your settings:

```ini
# ==============================================================================
# Aevora AI — Environment Configuration (.env)
# ==============================================================================

# Application Environment
ENVIRONMENT=development
LOG_LEVEL=INFO

# Google Gemini API Configuration (Required for live AI receptionist)
# Get a free key at https://aistudio.google.com/
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_FALLBACK_MODEL=gemini-1.5-flash

# Meta WhatsApp Cloud API Configuration (Required for live WhatsApp messages)
# From Meta App Dashboard -> WhatsApp -> API Setup
WHATSAPP_API_URL=https://graph.facebook.com/v22.0
WHATSAPP_ACCESS_TOKEN=your_meta_system_user_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_meta_phone_number_id_here
WHATSAPP_BUSINESS_ACCOUNT_ID=your_meta_waba_id_here
META_APP_SECRET=your_meta_app_secret_for_hmac_sha256_here
WEBHOOK_VERIFY_TOKEN=create_a_strong_random_verify_token_here

# Staff Dashboard & Authentication Configuration
# Provide a strong 32+ character secret for JWT tokens
STAFF_JWT_SECRET=super_secret_jwt_signing_key_at_least_32_characters_long
STAFF_TOKEN_EXPIRE_HOURS=8
DEFAULT_STAFF_USERNAME=admin
DEFAULT_STAFF_PASSWORD=NovaCare2026!

# Voice & Speech Configuration
VOICE_TEMP_DIR=temp_audio
WHISPER_MODEL_SIZE=base
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=auto
VOICE_REPLY_ENABLED=False
```

> [!NOTE]
> All secrets are protected using Pydantic's `SecretStr`. They are strictly masked in application logs and diagnostic health checks.

---

## 10. Database and RAG Knowledge-Base Setup

### 1. Database Initialization
Aevora AI uses SQLite with SQLAlchemy 2.0. Database tables (`conversations`, `messages`, `appointment_requests`, `handoff_requests`, `inbound_events`, `staff_users`) are **automatically created on application startup**. On first boot, the system automatically provisions the default staff administrator account (`admin` / `NovaCare2026!`).

### 2. Knowledge Base Ingestion
To build or rebuild the hybrid vector and keyword indexes from `data/documents/`:

```powershell
# Using the PowerShell automation script:
.\scripts\build_knowledge_base.ps1

# Or running the Python CLI module directly:
python -m scripts.ingest_knowledge_base
```

### 3. Verify Hybrid Retrieval
Test retrieval directly from your terminal with multilingual queries:

```powershell
# Roman Urdu query
python -m scripts.query_knowledge_base "Dr Sana Malik ki fee kitni hai?"

# English query
python -m scripts.query_knowledge_base "What are the clinic timings and consultation fees for cardiology?"
```

### 4. Run Retrieval Benchmark Evaluation
Execute the quantitative benchmark against 35 ground-truth test queries:

```powershell
python -m scripts.evaluate_retrieval
```
*Expected Output: **100.0% Recall@5**, **0.9839 MRR**.*

---

## 11. Starting Backend & Staff Dashboard

Launch the application with a single command:

```powershell
.\scripts\start_windows.ps1
```

*(Alternatively: `uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`)*

Once started, the following services are live:

| Surface | URL | Description & Credentials |
| :--- | :--- | :--- |
| **Staff Dashboard** | [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard) | Web interface. Login: `admin` / `NovaCare2026!` |
| **Interactive API Docs** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | OpenAPI / Swagger UI for direct endpoint testing. |
| **Operational Health** | [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health) | Uptime and service health telemetry. |
| **WhatsApp Diagnostics** | [http://127.0.0.1:8000/api/v1/whatsapp/status](http://127.0.0.1:8000/api/v1/whatsapp/status) | Diagnostic check for Meta webhook settings. |

---

## 12. Running Tests & Quality Checks

Run the complete test suite and code quality audits using the PowerShell automation script:

```powershell
.\scripts\run_tests.ps1
```

### Manual Test Execution
```powershell
# Run the complete test suite (105 tests)
pytest

# Run tests with quiet concise output
pytest -q

# Run specific test modules
pytest tests/test_e2e_journeys.py
pytest tests/test_staff_dashboard.py
pytest tests/test_security_and_hardening.py
```

### Linter & Formatting Audits (Ruff)
```powershell
# Run code linting
ruff check .

# Check code formatting compliance
ruff format --check .
```
*Result: **All checks passed! 105 passed in ~31s, 0 failed, 0 warnings. 100% clean.***

---

## 13. WhatsApp Cloud API Configuration

To connect Aevora AI to a real WhatsApp mobile number via Meta's Developer Platform:

1. Log in to [Meta for Developers](https://developers.facebook.com/) and create a **Business** app.
2. Add the **WhatsApp** product to your app.
3. In **API Setup**:
   - Copy your **Phone number ID** into `WHATSAPP_PHONE_NUMBER_ID` in `.env`.
   - Copy your **WhatsApp Business Account ID** into `WHATSAPP_BUSINESS_ACCOUNT_ID` in `.env`.
   - Generate a **System User Access Token** with `whatsapp_business_messaging` permissions and place it in `WHATSAPP_ACCESS_TOKEN`.
4. In **App Settings $\rightarrow$ Basic**:
   - Copy your **App Secret** into `META_APP_SECRET` in `.env` (used for webhook HMAC validation).
5. Choose a random verification token (e.g., `NovacareSecureWebhook2026Token`) and place it in `WEBHOOK_VERIFY_TOKEN` in `.env`.

For a complete walkthrough with screenshots and verification steps, see [docs/WHATSAPP_SETUP.md](docs/WHATSAPP_SETUP.md).

---

## 14. Voice Processing Setup

Aevora AI processes WhatsApp voice notes locally without sending audio to third-party commercial speech APIs:

- **Audio Acquisition**: When a patient sends a WhatsApp voice note, Meta delivers an audio payload event. Aevora verifies the Meta CDN domain (`lookaside.fbsbx.com`, `*.facebook.com`, `*.fbcdn.net`) and downloads the OGG/Opus file to `temp_audio/`.
- **Validation**: Enforces strict payload limits ($\le 16\text{MB}$ and $\le 180\text{ seconds}$).
- **Bundled FFmpeg Conversion**: Resolves system `ffmpeg` on `PATH` with automatic fallback to bundled executable via `imageio-ffmpeg`. Converts audio to 16kHz mono WAV format.
- **Faster-Whisper Transcription**: Executes transcription via Faster-Whisper. Auto-probes CUDA GPU availability; if absent or memory fails, cleanly falls back to CPU `int8` with multi-threading.
- **Lifecycle Cleanup**: Enforces guaranteed deletion of temporary audio files upon processing completion or failure.
- **Optional Spoken TTS**: Spoken voice replies via `edge-tts` are supported behind the `VOICE_REPLY_ENABLED=True` setting. If enabled, audio synthesis runs non-blockingly; if TTS fails, the text response is delivered without disruption.

---

## 15. Cloudflare Quick Tunnel Deployment

To expose your local FastAPI server to Meta's webhooks without public IPs or firewall rules:

1. Download the standalone `cloudflared` executable from [Cloudflare](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/).
2. Start the tunnel in a separate PowerShell window:
   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```
3. Copy the generated temporary HTTPS URL (e.g., `https://random-subdomain.trycloudflare.com`).
4. In the Meta Developer Portal:
   - Navigate to **WhatsApp $\rightarrow$ Configuration $\rightarrow$ Webhook**.
   - Click **Edit**.
   - **Callback URL**: `https://random-subdomain.trycloudflare.com/api/v1/whatsapp/webhook`
   - **Verify Token**: Must match your `WEBHOOK_VERIFY_TOKEN` in `.env`.
   - Click **Verify and Save**.
   - Under **Webhook fields**, click **Subscribe** to `messages`.

> [!TIP]
> Cloudflare Quick Tunnel URLs are temporary. If restarted, update the Callback URL in the Meta Dashboard.

---

## 16. Security & Privacy Notes

- **Zero Secret Exposure**: Passwords, tokens, and keys are strictly excluded from version control via `.gitignore`. The logger redacts tokens and authorization headers via `SensitiveDataSanitizingFilter`.
- **HMAC-SHA256 Webhook Verification**: Every incoming POST webhook payload from Meta is validated against `META_APP_SECRET` using `hmac.compare_digest`. Forged or unsigned webhooks are rejected with HTTP 403 Forbidden.
- **Password Security**: Staff passwords use PBKDF2-HMAC-SHA256 with 100,000 iterations and a unique 32-byte salt per user. Passwords are never stored in plain text.
- **Stateless Staff Authentication**: Dashboard routes require RFC 7519 JWT Bearer tokens signed with `HS256`. Expired or missing tokens return HTTP 401 Unauthorized.
- **Patient PII Phone Masking**: Patient phone numbers are masked across all logs and response payloads (`mask_phone_number`, e.g., `+9230****4567`).
- **Deterministic Medical Boundaries**: Emergency redirection (1122) and prescription/clinical advice deflections are enforced deterministically using regular expressions **before** LLM generation, completely preventing prompt injection or jailbreak bypasses.

For the full security audit and architectural controls, see [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md).

---

## 17. Employer Demo Instructions (5–10 Minutes)

Follow this step-by-step walkthrough to demonstrate Aevora AI's full capabilities to an employer or hiring committee:

| Step | Action | Message / Prompt | Expected Result |
| :---: | :--- | :--- | :--- |
| **1** | **Start Application** | Run `.\scripts\start_windows.ps1` | Launches Uvicorn on `http://127.0.0.1:8000`. |
| **2** | **Open Staff Dashboard** | Open `http://127.0.0.1:8000/dashboard` in browser | Clean login modal appears. Sign in using `admin` / `NovaCare2026!`. |
| **3** | **Clinic FAQ (English)** | Post to `/api/v1/chat` or send WhatsApp message: *"What are the clinic timings and consultation fees for cardiology?"* | Assistant cites Dr. Bilal Ahmad (Cardiology), 1,800 PKR fee, Mon–Fri 9:00 AM–1:00 PM. |
| **4** | **Multilingual (Roman Urdu)** | Send message: *"Dr Sana Malik ki fee kitni hai aur timing kya hai?"* | Assistant replies in Roman Urdu: 2,000 PKR, Mon–Thu 2:00 PM–6:00 PM. |
| **5** | **Multilingual (Urdu Script)** | Send message: *"نووا کیئر کلینک کا پتہ کیا ہے؟"* | Assistant replies in Urdu script with address; dashboard displays RTL typography. |
| **6** | **Appointment Intake** | Send message: *"I want to book an appointment"* | 5-slot state machine collects details turn-by-turn. Prompts for explicit confirmation. Records status as `pending_staff_confirmation`. |
| **7** | **Confirm in Dashboard** | Switch to **Appointments** tab in Dashboard | Request appears with patient details. Click **Confirm** button $\rightarrow$ updates status to `confirmed_by_staff`. |
| **8** | **Human Handoff** | Send message: *"I need to speak to a real person"* | Assistant creates human escalation. Shows under **Handoffs** tab in Dashboard. Staff can click **Resolve**. |
| **9** | **Medical Emergency** | Send message: *"Severe chest pain and difficulty breathing"* | Assistant immediately deflects to **1122 emergency rescue**, flags high-priority escalation in dashboard, and provides zero dangerous medical advice. |
| **10** | **System Diagnostics** | Navigate to **System Health** tab in Dashboard | Live telemetry displays active SQLite connection, RAG index status, and background worker state. |

For detailed conversation transcripts, API curl commands, and offline fallbacks, see [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md).

---

## 18. Known Limitations & Production Boundaries

1. **Demonstration Context**: Aevora AI is built around the fictional NovaCare Medical Centre demo dataset. It is not approved for clinical diagnostic use in live healthcare environments.
2. **Local Single-Instance Lock**: The system uses SQLite for zero-cost local evaluation. Horizontally scaling across multiple servers would require migrating to PostgreSQL and Redis.
3. **Cloudflare Quick Tunnel Lifespan**: Quick Tunnel URLs are temporary. When restarted, the webhook callback URL must be updated in the Meta Developer Console.
4. **Meta 24-Hour Messaging Window**: Meta policy allows incoming WhatsApp replies only within 24 hours of the patient's last inbound message.
5. **Speech Synthesis**: Spoken voice replies require active internet connectivity for `edge-tts` and are disabled by default (`VOICE_REPLY_ENABLED=False`) to prioritize high-speed text messaging.

---

## 19. Documentation Index

Comprehensive technical documentation is maintained in the `docs/` directory:

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — Detailed subsystem architecture, Mermaid sequence diagrams, and hardware requirements.
- [DEMO_GUIDE.md](docs/DEMO_GUIDE.md) — 5–10 minute step-by-step employer walkthrough script with exact prompts and expected outputs.
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — Windows local deployment, Cloudflare tunnel guide, and cloud host feasibility analysis.
- [SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md) — Security audit covering secrets, PBKDF2/JWT auth, webhook HMAC, and PII masking.
- [TEST_REPORT.md](docs/TEST_REPORT.md) — Complete test execution report documenting all 105 automated unit and integration tests.
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — Practical diagnostic runbooks for webhooks, audio, RAG, and dashboard issues.
- [DECISIONS.md](docs/DECISIONS.md) — 24 Architecture Decision Records (ADR 001 through ADR 024) detailing every technical decision.
- [WHATSAPP_SETUP.md](docs/WHATSAPP_SETUP.md) — Step-by-step Meta Developer Platform and Cloudflare Quick Tunnel setup guide.

---

<div align="center">
<strong>Aevora AI</strong> — <em>Healthcare conversations, made human.</em><br>
Crafted with FastAPI, Google Gemini Flash, FAISS, Faster-Whisper, and Meta WhatsApp Cloud API.
</div>
