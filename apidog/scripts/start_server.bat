@echo off
REM ============================================================
REM   CRA Mock API - one-click dev server start
REM   Run from the repo root or from anywhere - paths are relative
REM   to this file's location.
REM ============================================================

setlocal
cd /d "%~dp0\..\..\mock-api"

echo.
echo === CRA Mock API ===
echo Working dir : %CD%
echo URL         : http://localhost:8000
echo Swagger UI  : http://localhost:8000/docs
echo OpenAPI JSON: http://localhost:8000/openapi.json
echo.
echo Press Ctrl+C to stop.
echo.

REM Sync deps (idempotent, fast on subsequent runs)
uv sync

REM Run the server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

endlocal
