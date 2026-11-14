# Aevora AI

> **Healthcare conversations, made human.**

Aevora AI is an enterprise-grade multilingual WhatsApp clinic receptionist assistant designed for NovaCare Medical Centre (fictional demo clinic). It handles administrative clinic inquiries, provides doctor directory and fee information, collects appointment requests, processes patient voice notes, supports English, Urdu, and Roman Urdu, and safely routes uncertain or emergency scenarios to human staff.

---

## Phase 01: Architecture & Foundation

This repository is currently in **Phase 01: Foundation**. Phase 01 establishes a production-grade, testable FastAPI modular monolith, typed Pydantic configuration, structured logging, safe centralized error handling, and baseline test suites without prematurely adding external AI or Meta dependencies.

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
