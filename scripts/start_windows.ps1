<#
.SYNOPSIS
    Aevora AI — Start Local Application Server
.DESCRIPTION
    Launches Uvicorn FastAPI backend on http://127.0.0.1:8000 with live reload.
    Serves both the API routes (/api/v1/...) and the Staff Dashboard (/dashboard).
#>

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\uvicorn.exe")) {
    Write-Error "Virtual environment not found. Please run .\scripts\setup_windows.ps1 first."
    exit 1
}

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " Starting Aevora AI — NovaCare Medical Centre Reception Server" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " Staff Dashboard:    http://127.0.0.1:8000/dashboard" -ForegroundColor Green
Write-Host " API Documentation:  http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host " Health Check:       http://127.0.0.1:8000/health" -ForegroundColor Green
Write-Host " WhatsApp Webhook:   http://127.0.0.1:8000/api/v1/whatsapp/webhook" -ForegroundColor Green
Write-Host "------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host " Cloudflare Tunnel:  cloudflared tunnel --url http://localhost:8000" -ForegroundColor Yellow
Write-Host "==================================================================`n" -ForegroundColor Cyan

& ".\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8000 --reload
