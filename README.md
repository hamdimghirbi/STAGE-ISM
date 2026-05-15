# CRA-Expenses-AI-Connector (`STAGE-ISM`)

> 8-week internship project — building an **MCP server** that lets a Claude
> assistant automate the monthly filing of expense reports and timesheets for
> consultants on the Cooptalite/Portalite portal.

📘 **New here?** Read [`CLAUDE.md`](CLAUDE.md) — the project map with architecture
diagrams, domain model, and a full comparison of the three testing strategies.

## What's in this repo

```
STAGE-ISM/
├── README.md                     ← you are here
├── CLAUDE.md                     ← project map: architecture, domain, testing
│
├── mock-api/                     ← FastAPI backend simulating the Cooptalite portal
│   ├── README.md                 ← quickstart
│   ├── docs/
│   │   └── API.md                ← canonical API reference
│   ├── app/
│   │   ├── main.py
│   │   └── routers/{auth,cra,cra_tracking,expenses}.py
│   └── tests/                    ← 116 pytest tests, 100% line coverage
│       ├── unit/
│       ├── edge_cases/
│       └── scenarios/
│
└── apidog/                       ← Apidog + Newman test setup
    ├── README.md                 ← Apidog + Newman setup
    ├── openapi.json
    ├── environment.json                          ← Apidog env
    ├── environment.postman.json                  ← Newman env
    ├── cra_mock_api.postman_collection.json      ← 79-test Postman collection
    ├── fixtures/                 ← sample PDF/PNG for upload tests
    ├── scenarios/
    │   ├── e2e_test_plan.md      ← 14-step happy path
    │   └── real_world_flow.md    ← 28-step consultant monthly workflow
    └── scripts/                  ← server start, openapi fetch, fixture generator
```

The MCP server itself (FastMCP, six MCP tools, Playwright) will be added
during Phase 2 of the project. Until then, the mock-api is the target the
MCP server will be developed against.

## Quickstart

### Start the mock-api

```bash
# from the repo root
cd mock-api
uv sync
uv run uvicorn app.main:app --reload --port 8005
```

Or on Windows: `& "apidog\scripts\start_server.ps1"`

Then:

- Swagger UI: http://localhost:8005/docs
- OpenAPI JSON: http://localhost:8005/openapi.json
- Health check: http://localhost:8005/healthz

Demo credentials (auto-seeded on first run):

| | |
|---|---|
| email    | `demo@cra.local` |
| password | `demo1234` |

### Run tests

| Tool | Command | Speed | Tests |
|---|---|---|---|
| pytest | `cd mock-api && uv run pytest` | ~50s | 116 (100% coverage) |
| Newman | `newman run apidog/cra_mock_api.postman_collection.json -e apidog/environment.postman.json` | ~8s | 79 |
| Apidog | open the desktop app, import `openapi.json` | interactive | 0 (build manually) |

Full comparison and decision guide in [`CLAUDE.md` §7](CLAUDE.md#7-testing-strategies).

## Documentation map

| File | What it covers |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | **Project map** — architecture, domain, testing strategies (start here) |
| [`mock-api/README.md`](mock-api/README.md) | Mock backend quickstart, project layout, testing commands |
| [`mock-api/docs/API.md`](mock-api/docs/API.md) | **Canonical API reference** — every endpoint, schema, status code |
| [`mock-api/docs/WALKTHROUGH.md`](mock-api/docs/WALKTHROUGH.md) | **Hands-on runbook** — 28-step consultant flow with curl + DB verification |
| [`apidog/README.md`](apidog/README.md) | Apidog + Newman setup |
| [`apidog/scenarios/e2e_test_plan.md`](apidog/scenarios/e2e_test_plan.md) | 14-step happy-path scenario walkthrough |
| [`apidog/scenarios/real_world_flow.md`](apidog/scenarios/real_world_flow.md) | 28-step consultant monthly workflow |

## Stack (target, full project)

- **Language**: Python 3.12+
- **Mock backend**: FastAPI, SQLModel, JWT (`python-jose` + `passlib[bcrypt]`),
  SQLite, multipart uploads — managed with `uv`
- **MCP server** (upcoming): FastMCP, Anthropic API, Pydantic, Playwright
- **Testing**: pytest (116 tests, 100% coverage), Newman CLI, Apidog
- **Tooling**: Git, Ruff
- **Project management**: Plane (workspace `app.plane.so`)

## Project context

This work is part of a strategic effort by **Portalite** to modernise the
administrative experience for consultants — turning a recurring 1.5–2h/month
manual chore into a conversational interaction with an AI assistant, while
keeping the consultant in the loop (HITL) for every submission.

**Encadrant**: [Hamdi Mghirbi](https://www.linkedin.com/in/mghirbihamdi)
**Stagiaire**: Neda Khelifi
**Période**: 13 avril → 7 juin 2026
