# CRA Mock API

A simplified **FastAPI** backend that simulates the front-end behaviour of three pages of the Cooptalite/Portalite portal:

- **CRA** (activity calendar) — `/apps/calendar`
- **My Expenses** — `/pages/mymanagementfees`
- **My CRA Tracking** — `/pages/list-cra-user`

It exposes a small REST API with JWT auth, SQLite persistence (via SQLModel) and file uploads. Project is managed with [`uv`](https://docs.astral.sh/uv/).

> 📖 **Full API reference**: see [`docs/API.md`](docs/API.md) for every endpoint,
> schema, status code, and gotcha. The auto-generated Swagger UI lives at
> http://localhost:8005/docs once the server is running.
>
> 🛠️ **Want to actually use it?** See [`docs/WALKTHROUGH.md`](docs/WALKTHROUGH.md) —
> the consultant monthly workflow with concrete curl requests, sample responses,
> and DB / filesystem verification steps.

## Stack

- FastAPI + Uvicorn
- SQLModel on SQLite
- python-jose + passlib[bcrypt] (JWT auth)
- python-multipart (file uploads)
- pydantic-settings

## Quickstart

```bash
# 1. install uv: https://docs.astral.sh/uv/
cd mock-api

# 2. install dependencies
uv sync

# 3. configure env
cp .env.example .env

# 4. run dev server (port 8005 — canonical across this repo)
uv run uvicorn app.main:app --reload --port 8005
```

Open http://localhost:8005/docs for the interactive Swagger UI.

A demo user is auto-seeded on first run:

- **email**: demo@cra.local
- **password**: demo1234

To reset state, stop the server and `del app.db` (Windows) / `rm app.db` (Unix).

## Endpoints (high level)

For full details (request bodies, responses, status codes, edge cases) see
[`docs/API.md`](docs/API.md).

| Group | Method | Path | Purpose |
|---|---|---|---|
| Auth | POST | /api/auth/login | Get JWT (OAuth2 password flow) |
| Auth | GET | /api/auth/me | Current user |
| CRA | GET | /api/cra/events?month=YYYY-MM | List events |
| CRA | POST | /api/cra/events | Create event |
| CRA | PUT | /api/cra/events/{id} | Update event |
| CRA | DELETE | /api/cra/events/{id} | Delete event |
| CRA | POST | /api/cra/month/{month}/submit | Request validation |
| CRA | POST | /api/cra/month/{month}/signature | Upload signature |
| Tracking | GET | /api/cra-tracking/months | Paginated CRA list |
| Tracking | POST | /api/cra-tracking/months/{month}/import-client-cra | Upload signed PDF |
| Expenses | POST | /api/expenses/filter | List with filters |
| Expenses | POST | /api/expenses | Create (multipart with receipt) |
| Expenses | PUT | /api/expenses/{id} | Update |
| Expenses | DELETE | /api/expenses/{id} | Delete |
| Meta | GET | /healthz | Liveness probe |
| Meta | GET | /api/enums | All dropdown values |

## Testing

Three independent test strategies — see the
[top-level CLAUDE.md](../CLAUDE.md) for a full comparison.

### 1. pytest (canonical — 116 tests, 100% line coverage)

```bash
cd mock-api
uv sync --dev
uv run pytest                                 # all tests, ~50s
uv run pytest tests/unit/                     # just unit tests
uv run pytest tests/scenarios/                # just the real-world flow
uv run pytest --cov=app --cov-report=term     # with coverage
```

Tests use an isolated tmp SQLite DB per test, so they don't touch `app.db`.

### 2. Newman CLI (Postman runner — 79 tests, 8s)

Black-box regression against a running server. See
[`../apidog/cra_mock_api.postman_collection.json`](../apidog/cra_mock_api.postman_collection.json):

```bash
newman run apidog/cra_mock_api.postman_collection.json \
  -e apidog/environment.postman.json
```

### 3. Apidog (interactive / exploratory)

OpenAPI spec, environment, fixtures, and scenarios live in
[`../apidog/`](../apidog/). Best for one-off requests and visual debugging.

## Project layout

```
mock-api/
├── pyproject.toml
├── .python-version
├── .env.example
├── README.md
├── docs/
│   └── API.md                ← canonical API reference
├── app/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── schemas.py
│   ├── enums.py
│   ├── auth.py
│   ├── files.py
│   ├── seed.py
│   └── routers/
│       ├── auth.py
│       ├── cra.py
│       ├── cra_tracking.py
│       └── expenses.py
└── tests/                    ← 116 pytest tests, 100% line coverage
    ├── conftest.py           ← shared fixtures (isolated tmp DB per test)
    ├── _helpers.py           ← reusable verbs for scenario tests
    ├── unit/                 ← per-router tests
    ├── edge_cases/           ← parametrized negatives + conflicts + JWT
    └── scenarios/            ← real-world consultant flow
```

## Notes

This is a mock backend intended for development and integration testing of
the front-end flows (and, in this project, the MCP server that will drive
those flows on behalf of the consultant). Reference data — CRA
categories/activities, expense types, statuses — is hard-coded in
`app/enums.py`. There is no XLSX/ZIP export, no OCR, and no PDF generation
in this simplified version.
