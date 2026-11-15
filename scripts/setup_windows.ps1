<#
.SYNOPSIS
    Aevora AI — Automated Windows Setup Script
.DESCRIPTION
    Verifies Python prerequisites, initializes virtual environment,
    installs project dependencies, provisions .env template, and builds RAG index.
#>

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " Aevora AI — Local Windows Environment Provisioning" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Verify Python
Write-Host "`n[1/5] Checking Python installation..." -ForegroundColor Yellow
try {
    $pyVersion = & python --version 2>&1
    Write-Host "Found: $pyVersion" -ForegroundColor Green
} catch {
    Write-Error "Python was not found on PATH. Please install Python 3.11 or 3.12 from python.org."
    exit 1
}

# 2. Virtual Environment
Write-Host "`n[2/5] Setting up virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    Write-Host "Creating fresh virtual environment..."
    & python -m venv .venv
} else {
    Write-Host ".venv directory already exists." -ForegroundColor Green
}

$venvPython = ".\.venv\Scripts\python.exe"
$venvPip = ".\.venv\Scripts\pip.exe"

# 3. Upgrade Pip & Install Dependencies
Write-Host "`n[3/5] Installing project dependencies and tools..." -ForegroundColor Yellow
& $venvPip install --upgrade pip
& $venvPip install -e ".[dev]"

# 4. Safe Configuration Template
Write-Host "`n[4/5] Checking environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "Copying .env.example to .env..."
        Copy-Item ".env.example" ".env"
        Write-Host ".env created with safe development placeholders." -ForegroundColor Green
    }
} else {
    Write-Host ".env already exists. Preserving existing configuration." -ForegroundColor Green
}

# 5. Build Knowledge Base if not present
Write-Host "`n[5/5] Checking clinic knowledge base indexes..." -ForegroundColor Yellow
if (-not (Test-Path "data\vector_store\faiss_index.bin")) {
    Write-Host "FAISS index not found. Building initial knowledge base index..."
    & $venvPython -m scripts.ingest_knowledge_base
} else {
    Write-Host "FAISS index and BM25 corpus already present." -ForegroundColor Green
}

Write-Host "`n==================================================================" -ForegroundColor Green
Write-Host " [SUCCESS] Setup complete! Start Aevora AI using:" -ForegroundColor Green
Write-Host " .\scripts\start_windows.ps1" -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Green
