# Aevora AI — Agent Engineering Instructions

> **Permanent Operational & Architectural Rules for Coding Assistants**  
> These instructions govern all AI agent interactions and engineering modifications within the `aevora-ai` repository. Every rule must be honored across all phases.

---

## 1. Phase-Gate Discipline
1. **One Phase at a Time**: Work strictly within the current active phase. Never jump ahead or build components intended for future phases unless explicitly authorized.
2. **Criteria Before Progression**: Do not declare a phase complete until all automated tests pass, code passes Ruff linting/formatting, manual checks succeed, and `PROJECT_STATUS.md` is updated.
3. **No Hallucinated Progress**: Never claim a test passed, server started, or API responded unless the corresponding command was executed in the workspace and output verified.

---

## 2. Codebase Preservation & Inspection
1. **Inspect Before Modifying**: Always check existing directory structure, installed dependencies, Python version, and git status prior to modifying files.
2. **Preserve User Code**: Never delete, overwrite, or reset existing files without clear architectural necessity and user concurrence. Never run destructive git reset or clean commands.
3. **Explain Commands**: When instructing the repository owner, provide clear, copy-paste-ready commands formatted for Windows PowerShell (and Unix/macOS where appropriate).

---

## 3. Security, Credentials & Privacy
1. **Zero Hardcoded Secrets**: Never write API keys, access tokens, webhook verify tokens, or application secrets into code or version-controlled files.
2. **Secret Masking**: Use Pydantic's `SecretStr` for all sensitive settings to prevent accidental exposure via logging, string conversion, or exceptions.
3. **Never Log Sensitive Data**: Sanitize log records to exclude credentials, authorization headers, full conversation transcripts, and patient PII.
4. **Environment Isolation**: Always maintain `.env` in `.gitignore`. Ensure `.env.example` contains only blank, safe placeholder values.

---

## 4. Architectural Integrity & Minimalism
1. **Modular Monolith**: Maintain strict package boundaries (`core`, `api`, `ai`, `rag`, `whatsapp`, `voice`, `database`, `models`, `schemas`, `services`).
2. **Minimal Dependencies**: Only introduce new dependencies when strictly required for the active phase. Do not add heavyweight libraries (e.g., LangChain, Celery, Redis, Docker) merely because they are common.
3. **Record Architectural Decisions**: Document any significant technical choice, library selection, or structural modification in `docs/DECISIONS.md`.
4. **No Fake Integrations**: Avoid mock stubs that pretend to perform real external actions while returning fake successful data. If a module is pending implementation, raise `NotImplementedError` or clearly mark its status.

---

## 5. Testing & Code Quality
1. **Test Alongside Features**: Every new feature or endpoint must be accompanied by comprehensive Pytest tests.
2. **Ruff Compliance**: All code must conform to the Ruff configuration defined in `pyproject.toml` (100 character line length, clean imports, Python 3.11+ modern syntax).
3. **Offline Testability**: Unit and integration tests must run without requiring live external network access, valid API keys, or active Meta accounts.

---

## 6. Fictional Clinic Data Notice
1. **NovaCare Medical Centre is Fictional**: All doctor profiles, charges, clinic policies, and contact information are synthetic data created strictly for hiring assessment demonstration.
2. **Keep Synchronized**: Whenever updates are made to clinic data, verify that `NovaCare_Medical_Centre_RAG_Knowledge_Base.pdf` and `NovaCare_RAG_Source_of_Truth.json` remain identical in factual content.
