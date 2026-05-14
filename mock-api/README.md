# CRA Mock API

A simplified **FastAPI** backend that simulates the front-end behaviour of three pages of the Cooptalite portal:

- **CRA** (activity calendar) — \`/apps/calendar\`
- **My Expenses** — \`/pages/mymanagementfees\`
- **My CRA Tracking** — \`/pages/list-cra-user\`

It exposes a small REST API with JWT auth, SQLite persistence (via SQLModel) and file uploads. Project is managed with [\`uv\`](https://docs.astral.sh/uv/).

## Stack

- FastAPI + Uvicorn
- SQLModel on SQLite
- python-jose + passlib[bcrypt] (JWT auth)
- python-multipart (file uploads)
- pydantic-settings

## Quickstart

\`\`\`bash
# 1. install uv: https://docs.astral.sh/uv/
cd mock-api

# 2. install dependencies
uv sync

# 3. configure env
cp .env.example .env

# 4. run dev server
uv run uvicorn app.main:app --reload
\`\`\`

Open http://localhost:8000/docs for the interactive Swagger UI.

A demo user is auto-seeded on first run:

- **email**: demo@cra.local
- **password**: demo1234

## Endpoints (high level)

| Group | Method | Path | Purpose |
|---|---|---|---|
| Auth | POST | /api/auth/login | Get JWT |
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
| Expenses | POST | /api/expenses | Create (multipart) |
| Expenses | PUT | /api/expenses/{id} | Update |
| Expenses | DELETE | /api/expenses/{id} | Delete |
| Ref | GET | /api/enums | All dropdown values |

## Project layout

\`\`\`
mock-api/
├── pyproject.toml
├── .python-version
├── .env.example
├── README.md
└── app/
    ├── main.py
    ├── config.py
    ├── db.py
    ├── models.py
    ├── schemas.py
    ├── enums.py
    ├── auth.py
    ├── files.py
    ├── seed.py
    └── routers/
        ├── auth.py
        ├── cra.py
        ├── cra_tracking.py
        └── expenses.py
\`\`\`

## Notes

This is a mock backend intended for development and integration testing of the front-end flows. Reference data (CRA categories/activities, expense types, statuses) is hard-coded in \`app/enums.py\`. There is no XLSX/ZIP export, no OCR, and no PDF generation in this simplified version.
