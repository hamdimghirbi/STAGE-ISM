# Apidog setup for the CRA Mock API

This folder contains everything you need to test the mock-api with Apidog.

## What's here

```
apidog/
├── README.md                 ← you are here
├── openapi.json              ← full OpenAPI 3.0 spec, import this into Apidog
├── environment.json          ← environment variables (base_url, demo creds, etc.)
├── fixtures/
│   └── sample_receipt.pdf    ← tiny valid PDF for multipart upload tests
├── scenarios/
│   └── e2e_test_plan.md      ← step-by-step E2E scenario to build in Apidog
└── scripts/
    ├── start_server.bat      ← one-click server start (Windows cmd)
    ├── start_server.ps1      ← same, for PowerShell
    ├── fetch_openapi.py      ← grab the live spec from the running server
    └── make_fixtures.py      ← regenerate the fixture files (PDF + PNG)
```

## Quick start

### 1. Start the mock-api

Double-click `apidog/scripts/start_server.bat` — or run it from a terminal:

```cmd
apidog\scripts\start_server.bat
```

You should see Uvicorn boot on `http://localhost:8000`. Sanity-check with:

- http://localhost:8000/healthz → `{"status":"ok"}`
- http://localhost:8000/docs → Swagger UI

### 2. Generate the fixture files

```cmd
python apidog\scripts\make_fixtures.py
```

This writes a tiny valid PDF and a 1×1 PNG into `apidog/fixtures/`.

### 3. Import into Apidog

In the Apidog desktop app:

1. **New Project** → name it `CRA Mock API`
2. **Settings → Import Data → OpenAPI/Swagger** → pick `apidog/openapi.json`
3. Apidog will create folders matching the OpenAPI tags:
   `auth`, `cra`, `cra-tracking`, `expenses`, `meta` — every endpoint pre-filled
   with example bodies, schemas, and response definitions.

### 4. Set up the environment

Two options:

**Easier**: in Apidog, create a new env called `Local` and copy the variables
listed in `environment.json` (or in the env table inside `scenarios/e2e_test_plan.md`).

**Direct import**: Apidog's import for environment files varies by version —
look for **Settings → Environments → Import** and try the `environment.json`
file. If it doesn't accept the format, fall back to entering the variables
manually (it's only 9 of them).

### 5. Set the project-level Bearer auth

**Project Settings → Authorization → Bearer Token**, value: `{{token}}`.

The login step (Step 1 of the E2E scenario) writes the JWT into `{{token}}`,
and every subsequent request inherits it automatically.

### 6. Build the E2E test scenario

Follow `apidog/scenarios/e2e_test_plan.md` step by step. The scenario covers:

```
login → /me → /enums → create event → list events → update event
      → submit month → upload signature → create expense
      → filter expenses → list tracking months → cleanup
```

with assertions on every step and chained variable extraction between steps.

### 7. Run it

In Apidog, click **Run** on the scenario. You should see all 14 steps go green.

To run from the command line:

```cmd
apidog test --scenario "CRA Mock API — Happy Path"
```

(requires Apidog CLI to be installed and the project linked).

## Refreshing after API changes

When the mock-api code changes, the committed `openapi.json` may drift. To
refresh:

```cmd
REM 1. with the server running:
python apidog\scripts\fetch_openapi.py

REM 2. diff against the committed copy:
git diff apidog\openapi.json apidog\openapi_live.json

REM 3. if the live spec is the source of truth now:
copy apidog\openapi_live.json apidog\openapi.json

REM 4. re-import into Apidog (it will offer to merge changes)
```

## Known caveats

- The seed data already contains 4 past `Validated` months and 2 expenses for
  the demo user. Step 5 (list events) and Step 11 (list months) account for
  this — assertions check that *our* item is present, not that it's the only one.
- Re-running the scenario back-to-back: month becomes `Pending` after Step 7,
  blocking event create/update on the second run with `409`. Either delete
  `mock-api/app.db` between runs, or add a teardown step that resets state.
