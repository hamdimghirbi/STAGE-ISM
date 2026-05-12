# CRA-Expenses-AI-Connector (`STAGE-ISM`)

> 8-week internship project — building an **MCP server** that lets a Claude
> assistant automate the monthly filing of expense reports and timesheets for
> consultants on the Cooptalite/Portalite portal.

The full requirements and project plan are in [`cahier_des_charges.pdf`](cahier_des_charges.pdf).

## What's in this repo today

```
STAGE-ISM/
├── README.md            ← you are here
├── cahier_des_charges.pdf
├── mock-api/            ← FastAPI backend simulating the Cooptalite portal
│   ├── README.md
│   ├── docs/
│   │   └── API.md       ← canonical API reference
│   └── app/
│       ├── main.py
│       └── routers/{auth,cra,cra_tracking,expenses}.py
└── apidog/              ← Apidog test setup for the mock-api
    ├── README.md
    ├── openapi.json
    ├── environment.json
    ├── fixtures/
    ├── scenarios/
    │   └── e2e_test_plan.md
    └── scripts/         ← server start, openapi fetch, fixture generator
```

The MCP server itself (FastMCP, six MCP tools, Claude Vision, Playwright)
will be added during Phase 2 of the project. Until then, the mock-api is the
target the MCP server will be developed against.

## Start the mock-api

```bash
# from the repo root
cd mock-api
uv sync
uv run uvicorn app.main:app --reload
```

Or on Windows, double-click `apidog/scripts/start_server.bat`.

Then:

- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json
- Health check: http://localhost:8000/healthz

Demo credentials (auto-seeded on first run):

| | |
|---|---|
| email    | `demo@cra.local` |
| password | `demo1234` |

## Documentation

| File | What it covers |
|---|---|
| [`mock-api/README.md`](mock-api/README.md) | Mock backend quickstart & dependencies |
| [`mock-api/docs/API.md`](mock-api/docs/API.md) | **Canonical API reference** — every endpoint, schema, status code, gotcha |
| [`apidog/README.md`](apidog/README.md) | How to import the API into Apidog and wire up tests |
| [`apidog/scenarios/e2e_test_plan.md`](apidog/scenarios/e2e_test_plan.md) | Step-by-step happy-path E2E scenario |
| [`cahier_des_charges.pdf`](cahier_des_charges.pdf) | Full project plan (FR) — context, objectives, 8-week schedule |

## Stack (target, full project)

- **Language**: Python 3.12+
- **Mock backend**: FastAPI, SQLModel, JWT (`python-jose` + `passlib[bcrypt]`),
  SQLite, multipart uploads — managed with `uv`
- **MCP server** (upcoming): FastMCP, Anthropic API (Claude Vision), Pydantic,
  Playwright
- **Tooling**: Git, Apidog (API testing), pytest, Ruff
- **Project management**: Plane (workspace `app.plane.so`)

## Project context

This work is part of a strategic effort by **Portalite** to modernise the
administrative experience for consultants — turning a recurring 1.5–2h/month
manual chore into a conversational interaction with an AI assistant, while
keeping the consultant in the loop (HITL) for every submission.

**Encadrant**: [Hamdi Mghirbi](https://www.linkedin.com/in/mghirbihamdi)
**Stagiaire**: Neda Khelifi
**Période**: 13 avril → 7 juin 2026
