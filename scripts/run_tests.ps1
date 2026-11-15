<#
.SYNOPSIS
    Aevora AI — Run Comprehensive Test Suite and Linters
.DESCRIPTION
    Executes Ruff formatting/linting audits and full Pytest verification across
    RAG, AI receptionist, WhatsApp webhooks, voice pipelines, and staff dashboard.
#>

$ErrorActionPreference = "Continue"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " Aevora AI — Code Quality and Automated Test Runner" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Lint and Format Check
Write-Host "`n[1/2] Running Ruff Linter & Formatter..." -ForegroundColor Yellow
& ".\.venv\Scripts\ruff.exe" check .
$lintExit = $LASTEXITCODE

& ".\.venv\Scripts\ruff.exe" format --check .
$fmtExit = $LASTEXITCODE

if ($lintExit -ne 0 -or $fmtExit -ne 0) {
    Write-Warning "Ruff checks detected issues. Run 'ruff check --fix .' to auto-resolve."
} else {
    Write-Host "Ruff code audit 100% clean!" -ForegroundColor Green
}

# 2. Pytest Execution
Write-Host "`n[2/2] Running Pytest Suite..." -ForegroundColor Yellow
& ".\.venv\Scripts\pytest.exe" -v
$testExit = $LASTEXITCODE

Write-Host "`n==================================================================" -ForegroundColor Cyan
if ($testExit -eq 0) {
    Write-Host " [SUCCESS] All automated test journeys passed!" -ForegroundColor Green
} else {
    Write-Host " [FAILURE] One or more tests failed (Exit Code: $testExit)" -ForegroundColor Red
}
Write-Host "==================================================================" -ForegroundColor Cyan

exit $testExit
