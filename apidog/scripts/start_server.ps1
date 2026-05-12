# ============================================================
#   CRA Mock API - one-click dev server start (PowerShell)
# ============================================================

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$apiDir   = Join-Path $repoRoot "mock-api"

Set-Location $apiDir

Write-Host ""
Write-Host "=== CRA Mock API ===" -ForegroundColor Cyan
Write-Host "Working dir : $apiDir"
Write-Host "URL         : http://localhost:8000"
Write-Host "Swagger UI  : http://localhost:8000/docs"
Write-Host "OpenAPI JSON: http://localhost:8000/openapi.json"
Write-Host ""
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
