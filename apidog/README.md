# Apidog & Newman setup for the CRA Mock API

This folder contains everything you need to test the mock-api with either
**Apidog** (interactive GUI) or **Newman** (CLI). For the full testing
strategy — including pytest — see the [top-level CLAUDE.md](../CLAUDE.md).

## What's here

```
apidog/
├── README.md                          ← you are here
├── openapi.json                       ← OpenAPI 3.0 spec, importable into any API tool
├── environment.json                   ← Apidog-format environment variables
├── environment.postman.json           ← Postman/Newman-format environment
├── cra_mock_api.postman_collection.json  ← 79-test Postman collection (3 scenarios)
├── fixtures/
│   ├── sample_receipt.pdf             ← tiny valid PDF for multipart upload tests
│   └── sample_signature.png           ← 1×1 PNG for signature uploads
├── scenarios/
│   ├── e2e_test_plan.md               ← 14-step Happy Path narrative
│   └── real_world_flow.md             ← 28-step Real World Flow narrative
└── scripts/
    ├── start_server.bat               ← one-click server start (cmd)
    ├── start_server.ps1               ← same, for PowerShell
    ├── fetch_openapi.py               ← grab the live spec from the running server
    └── make_fixtures.py               ← regenerate fixture files (PDF + PNG)
```

## Quick start

### 1. Start the mock-api

Double-click `apidog/scripts/start_server.bat` — or from PowerShell:

```powershell
& "apidog\scripts\start_server.ps1"
```

The server starts on **port 8005**. Sanity-check:

- http://localhost:8005/healthz → `{"status":"ok"}`
- http://localhost:8005/docs → Swagger UI

### 2. Generate the fixture files

```powershell
python apidog\scripts\make_fixtures.py
```

This writes a tiny valid PDF and a 1×1 PNG into `apidog/fixtures/`.

---

## Path A — Newman CLI (recommended for full coverage)

Newman runs the 79-test Postman collection end-to-end in ~8 seconds.

```powershell
# install once
npm install -g newman

# run the full suite
newman run apidog\cra_mock_api.postman_collection.json `
  -e apidog\environment.postman.json
```

The collection has 3 folders:

| Folder | Tests | What it covers |
|---|---|---|
| `01 — Happy Path E2E` | 14 | Login → manage events → submit → sign → expense → filter → cleanup |
| `02 — Real World Flow` | 28 | Full consultant monthly workflow (multi-day, absences, half-days, 3 expense types) |
| `03 — Edge Cases` | 37 | Auth errors, validation errors, all activity/expense types, pagination |

Run just one folder:

```powershell
newman run apidog\cra_mock_api.postman_collection.json `
  -e apidog\environment.postman.json `
  --folder "02 — Real World Flow"
```

---

## Path B — Apidog (interactive GUI)

### 1. Import the OpenAPI spec into Apidog

1. **New Project** → name it `CRA API MOCK`
2. **Settings → Import Data → OpenAPI/Swagger** → pick `apidog/openapi.json`
3. Apidog creates folders matching the OpenAPI tags:
   `auth`, `cra`, `cra-tracking`, `expenses`, `meta` — every endpoint pre-filled.

### 2. Set up the environment

Create a new environment called **`CRA API MOCK DEV ENV`** with these
variables (copy from `environment.json`):

| Variable | Initial value | Notes |
|---|---|---|
| `base_url` | `http://localhost:8005` | Server URL |
| `email` | `demo@cra.local` | Demo user (auto-seeded) |
| `password` | `demo1234` | Demo password |
| `bearerToken` | *(blank)* | Set by login step's post-processor |
| `current_month`, `today`, `month_start`, … | *(blank)* | Set by Step 1 pre-script |
| `event_id_*`, `expense_id_*` | *(blank)* | Set by individual steps |

### 3. Bearer auth is auto-wired by the OpenAPI import

After importing the OpenAPI spec, each folder in Apidog (`auth`, `cra`, …)
has an **Auth** tab where the Bearer token is bound to `{{bearerToken}}`.
You **don't** need to configure project-level auth — the import already did it.

The login step's post-processor extracts the JWT from `$.access_token` and
writes it to the `bearerToken` env variable. Every subsequent step inherits
it automatically.

### 4. Build the test scenario

Two options:

- **Manual** — follow `apidog/scenarios/e2e_test_plan.md` (14 steps) or
  `apidog/scenarios/real_world_flow.md` (28 steps), step by step.
- **Import the Postman collection** — Apidog → Settings → Import Data →
  Postman → pick `cra_mock_api.postman_collection.json`. Apidog merges by
  endpoint URL, so steps end up grouped by HTTP path, not by scenario.
  Most users prefer the manual build for cleaner organization.

### 5. Run it

Click **Run** on the scenario in Apidog.

---

## Refreshing the OpenAPI spec after API changes

When the mock-api code changes, the committed `openapi.json` may drift. To refresh:

```powershell
# 1. with the server running:
python apidog\scripts\fetch_openapi.py

# 2. diff against the committed copy:
git diff apidog\openapi.json apidog\openapi_live.json

# 3. if the live spec is the source of truth now:
copy apidog\openapi_live.json apidog\openapi.json

# 4. re-import into Apidog (it will offer to merge changes)
```

---

## Known caveats

- The seed data already contains 4 past `Validated` months and 2 expenses
  for the demo user. Tests account for this.
- **Re-running scenarios back-to-back**: after Step 9 of the Real World Flow,
  the current month is `Pending`. The mock API allows re-submitting a
  `Pending` month (it stays `Pending`), so most steps still work, but cleanup
  is more reliable if you reset between full runs:
  ```powershell
  # stop the server, then:
  del mock-api\app.db
  # restart — seed runs again, demo user re-created
  ```
