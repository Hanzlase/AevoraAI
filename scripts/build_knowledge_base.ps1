<#
.SYNOPSIS
    Aevora AI — Rebuild Clinic Knowledge Base Indexes
.DESCRIPTION
    Ingests NovaCare canonical JSON and PDF documents, extracts text chunks,
    generates dense E5 embeddings, constructs FAISS vector index and BM25 sparse corpus.
#>

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " Aevora AI — Building Hybrid RAG Knowledge Base" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

& ".\.venv\Scripts\python.exe" -m scripts.ingest_knowledge_base

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] Knowledge base artifacts built under data\vector_store\" -ForegroundColor Green
} else {
    Write-Error "Knowledge base ingestion failed with exit code $LASTEXITCODE"
}
