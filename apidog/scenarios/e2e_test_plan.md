# E2E Test Scenario — CRA Mock API

This walks through building a single end-to-end test scenario in Apidog that
exercises the full happy path: **login → manage events → submit month →
upload signature → create expense → filter expenses → cleanup**.

Each step lists the request, what to extract from the response (so the next
step has what it needs), and the assertions to add.

## Prerequisites

1. Mock API running: `apidog/scripts/start_server.bat`
2. OpenAPI spec imported into Apidog: `apidog/openapi.json`
3. Environment created in Apidog with these variables:

   | Variable        | Initial value                  |
   |-----------------|--------------------------------|
   | `base_url`      | `http://localhost:8005`        |
   | `email`         | `demo@cra.local`               |
   | `password`      | `demo1234`                     |
   | `bearerToken`   | *(empty — set by Step 1)*      |
   | `current_month` | *(empty — set by Step 1)*      |
   | `event_id`      | *(empty — set by Step 4)*      |
   | `expense_id`    | *(empty — set by Step 8)*      |

4. Bearer auth is already wired up by the OpenAPI import: each folder in
   the APIs section has an **Auth** tab bound to `{{bearerToken}}`. Step 1's
   post-processor writes the JWT into that variable, so every subsequent
   request inherits it automatically.

5. Sample fixture files exist (regenerate if needed):
   ```
   python apidog/scripts/make_fixtures.py
   ```

---

## Scenario steps

> In Apidog: **Testing → Test Scenarios → New Scenario**, name it
> `CRA Mock API — Happy Path`, then add each step below in order.

### Step 1 — Login (form-urlencoded)

- **Request**: `POST {{base_url}}/api/auth/login`
- **Body** (`x-www-form-urlencoded`):
  - `username` = `{{email}}`
  - `password` = `{{password}}`
- **Post-processor — Extract**:
  - `bearerToken` ← JSONPath `$.access_token` → save to env var `bearerToken`
  - `current_month` ← Custom script:
    ```js
    const d = new Date();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    pm.environment.set('current_month', `${d.getFullYear()}-${m}`);
    ```
- **Assertions**:
  - HTTP status code = `200`
  - JSON `$.access_token` exists (string, length > 20)
  - JSON `$.token_type` = `bearer`

### Step 2 — Get current user

- **Request**: `GET {{base_url}}/api/auth/me`
- **Auth**: inherits Bearer from project (uses `{{token}}`)
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.email` = `{{email}}`
  - JSON `$.role` = `member`

### Step 3 — Get reference enums

- **Request**: `GET {{base_url}}/api/enums`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.cra_categories` contains `"Travail"` and `"Absence"`
  - JSON `$.expense_types` contains `"Restaurant"`

### Step 4 — Create a CRA event for today

- **Request**: `POST {{base_url}}/api/cra/events`
- **Body** (raw JSON):
  ```json
  {
    "categorie": "Travail",
    "activity": "Prestation",
    "start_date": "{{today}}",
    "end_date":   "{{today}}",
    "all_day": true,
    "nb": 1.0,
    "description": "E2E test — Prestation client"
  }
  ```
  > Add a pre-script to set `today`:
  > ```js
  > pm.environment.set('today', new Date().toISOString().slice(0, 10));
  > ```
- **Post-processor — Extract**:
  - `event_id` ← JSONPath `$.id`
- **Assertions**:
  - HTTP status = `201`
  - JSON `$.user_id` is a number
  - JSON `$.activity` = `Prestation`
  - JSON `$.month` = `{{current_month}}`

### Step 5 — List events for the current month, expect ours in there

- **Request**: `GET {{base_url}}/api/cra/events?month={{current_month}}`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$` is an array, length ≥ 1
  - JSONPath `$[?(@.id == {{event_id}})]` exists (the event we created is present)

### Step 6 — Update the event description

- **Request**: `PUT {{base_url}}/api/cra/events/{{event_id}}`
- **Body** (raw JSON):
  ```json
  { "description": "E2E test — updated" }
  ```
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.description` = `E2E test — updated`

### Step 7 — Submit the month for validation

- **Request**: `POST {{base_url}}/api/cra/month/{{current_month}}/submit`
- **Body** (raw JSON):
  ```json
  {
    "description_tasks": "Activités du mois (E2E test)",
    "reserve_use_eur": 0,
    "reserve_use_days": 0,
    "reserve_save_eur": 0,
    "reserve_save_days": 0
  }
  ```
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.status` = `Pending`
  - JSON `$.submitted_at` is not null

### Step 8 — Upload signature for the month

- **Request**: `POST {{base_url}}/api/cra/month/{{current_month}}/signature`
- **Body** (`multipart/form-data`):
  - `file` = file upload → `apidog/fixtures/sample_signature.png`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.signature_path` is not null and contains `signatures`

### Step 9 — Create an expense (multipart with receipt)

- **Request**: `POST {{base_url}}/api/expenses`
- **Body** (`multipart/form-data`):
  - `type` = `Restaurant`
  - `month` = `{{current_month}}`
  - `description` = `Repas client (E2E)`
  - `total_amount` = `42.50`
  - `billable_to_client` = `true`
  - `comment` = `Test scenario`
  - `receipt` = file upload → `apidog/fixtures/sample_receipt.pdf`
- **Post-processor — Extract**:
  - `expense_id` ← JSONPath `$.id`
- **Assertions**:
  - HTTP status = `201`
  - JSON `$.type` = `Restaurant`
  - JSON `$.total_amount` = `42.5`
  - JSON `$.status` = `Pending`
  - JSON `$.receipt_path` is not null

### Step 10 — Filter expenses, expect ours in the page

- **Request**: `POST {{base_url}}/api/expenses/filter`
- **Body** (raw JSON):
  ```json
  {
    "year": {{$randomInt}},
    "type": "Restaurant",
    "page": 1,
    "limit": 50
  }
  ```
  > Replace `{{$randomInt}}` with the year extracted from `current_month`:
  > pre-script: `pm.environment.set('current_year', parseInt('{{current_month}}'.slice(0,4)))`
  > then use `"year": {{current_year}}`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.total` ≥ 1
  - JSONPath `$.items[?(@.id == {{expense_id}})]` exists

### Step 11 — List CRA months (tracking page)

- **Request**: `GET {{base_url}}/api/cra-tracking/months?page=1&limit=10`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.items` is an array
  - JSON `$.page` = `1`
  - JSON `$.limit` = `10`
  - JSONPath `$.items[?(@.month == "{{current_month}}")]` exists

### Step 12 — Cleanup: delete the expense

- **Request**: `DELETE {{base_url}}/api/expenses/{{expense_id}}`
- **Assertions**:
  - HTTP status = `204`

### Step 13 — Cleanup: delete the event

- **Request**: `DELETE {{base_url}}/api/cra/events/{{event_id}}`
- **Assertions**:
  - HTTP status = `204`

### Step 14 — Verify cleanup (event no longer in list)

- **Request**: `GET {{base_url}}/api/cra/events?month={{current_month}}`
- **Assertions**:
  - HTTP status = `200`
  - JSONPath `$[?(@.id == {{event_id}})]` does NOT exist

---

## Negative-path scenarios (optional, recommended)

Build these as a separate scenario `CRA Mock API — Edge Cases`:

1. **Login with wrong password** → expect `401`
2. **Access `/me` without token** → expect `401`
3. **Create event with `Absence`/`Prestation` mismatch** → expect `400`
   ```json
   { "categorie": "Absence", "activity": "Prestation",
     "start_date": "2026-05-04", "end_date": "2026-05-04" }
   ```
4. **Create event with `end_date < start_date`** → expect `400`
5. **Create expense without receipt** for type `Restaurant` → expect `400`
6. **Create expense without receipt** for type `Indemnités kilométriques` → expect `201`
7. **Upload file with `.exe` extension** → expect `415`
8. **Filter with invalid month (13)** → expect `422`
9. **Update someone else's event** → expect `404` (need a second user for this)
10. **Delete a Validated expense** → expect `409` (need to manually flip status in DB)

---

## Tips

- Apidog supports **chaining**: extract from one step, use in the next. The
  `event_id`, `expense_id`, and `current_month` extractions above rely on this.
- The Bearer token only needs to be set once (Step 1 stores it, folder-level
  Auth reads `{{bearerToken}}` thereafter).
- If you re-run the scenario back-to-back, Step 7 will fail with `409` because
  the month is now `Pending`. Either delete `mock-api/app.db` between runs, or
  add a Step 0 that calls `/api/cra/events?month={{current_month}}` and deletes
  any pre-existing events from prior runs.
- You can run the whole scenario from the CLI: `apidog test --scenario "CRA Mock API — Happy Path"`
  once you've connected your local Apidog to the project.
