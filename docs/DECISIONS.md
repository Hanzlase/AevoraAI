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
