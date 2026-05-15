# Real-World Consultant Flow — CRA Mock API

Full monthly workflow as a consultant would actually use the portal:
login → fill CRA (work days, absences, half-day) → submit → sign →
fill expenses (multiple types) → update expense → check tracking → import client CRA → cleanup.

## Environment variables used

| Variable | Set by | Description |
|---|---|---|
| `bearerToken` | Step 1 post-processor | JWT from login |
| `current_month` | Step 1 pre-script | `YYYY-MM` of today |
| `today` | Step 1 pre-script | `YYYY-MM-DD` |
| `month_start` | Step 1 pre-script | First day of current month |
| `month_day_3` | Step 1 pre-script | 3rd day of current month |
| `month_day_5` | Step 1 pre-script | 5th day of current month |
| `event_id_1` | Step 3 | Single-day Prestation |
| `event_id_2` | Step 4 | Multi-day Prestation |
| `event_id_3` | Step 5 | Absence/CP |
| `event_id_4` | Step 6 | Half-day Prestation |
| `expense_id_1` | Step 11 | Restaurant expense |
| `expense_id_2` | Step 12 | Indemnités kilométriques |
| `expense_id_3` | Step 13 | Titre de transport |

---

## Phase 1 — Login

### Step 1 — Login

- **Request**: `POST {{base_url}}/api/auth/login`
- **Body** (`x-www-form-urlencoded`):
  - `username` = `{{email}}`
  - `password` = `{{password}}`
- **Pre-script**:
  ```js
  const d = new Date();
  const pad = n => String(n).padStart(2, '0');
  const y = d.getFullYear();
  const m = pad(d.getMonth() + 1);
  pm.environment.set('current_month', `${y}-${m}`);
  pm.environment.set('today', `${y}-${m}-${pad(d.getDate())}`);
  pm.environment.set('month_start', `${y}-${m}-01`);
  pm.environment.set('month_day_3', `${y}-${m}-03`);
  pm.environment.set('month_day_5', `${y}-${m}-05`);
  ```
- **Post-processor — Extract**:
  - `bearerToken` ← JSONPath `$.access_token` → Environment Variables
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.access_token` exists

---

## Phase 2 — Fill the CRA

### Step 2 — Get reference enums (bootstrap dropdowns)

- **Request**: `GET {{base_url}}/api/enums`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.cra_categories` contains `"Travail"` and `"Absence"`
  - JSON `$.cra_activities.Travail` contains `"Prestation"`
  - JSON `$.cra_activities.Absence` contains `"CP"`

### Step 3 — Create a single work day (Travail / Prestation)

- **Request**: `POST {{base_url}}/api/cra/events`
- **Body** (JSON):
  ```json
  {
    "categorie": "Travail",
    "activity": "Prestation",
    "start_date": "{{today}}",
    "end_date": "{{today}}",
    "all_day": true,
    "nb": 1.0,
    "description": "Client on-site — real world flow"
  }
  ```
- **Post-processor — Extract**: `event_id_1` ← `$.id`
- **Assertions**:
  - HTTP status = `201`
  - JSON `$.categorie` = `Travail`
  - JSON `$.activity` = `Prestation`
  - JSON `$.nb` = `1.0`
  - JSON `$.month` = `{{current_month}}`

### Step 4 — Create a multi-day work range (days 1–3 of the month)

- **Request**: `POST {{base_url}}/api/cra/events`
- **Body** (JSON):
  ```json
  {
    "categorie": "Travail",
    "activity": "Prestation",
    "start_date": "{{month_start}}",
    "end_date": "{{month_day_3}}",
    "all_day": true,
    "nb": 1.0,
    "description": "Sprint delivery — 3 days"
  }
  ```
- **Post-processor — Extract**: `event_id_2` ← `$.id`
- **Assertions**:
  - HTTP status = `201`
  - JSON `$.start_date` = `{{month_start}}`
  - JSON `$.end_date` = `{{month_day_3}}`

### Step 5 — Create an absence day (Absence / CP)

- **Request**: `POST {{base_url}}/api/cra/events`
- **Body** (JSON):
  ```json
  {
    "categorie": "Absence",
    "activity": "CP",
    "start_date": "{{month_day_5}}",
    "end_date": "{{month_day_5}}",
    "all_day": true,
    "nb": 1.0,
    "description": "Paid leave"
  }
  ```
- **Post-processor — Extract**: `event_id_3` ← `$.id`
- **Assertions**:
  - HTTP status = `201`
  - JSON `$.categorie` = `Absence`
  - JSON `$.activity` = `CP`

### Step 6 — Create a half-day (nb = 0.5)

- **Request**: `POST {{base_url}}/api/cra/events`
- **Body** (JSON):
  ```json
  {
    "categorie": "Travail",
    "activity": "Prestation",
    "start_date": "{{today}}",
    "end_date": "{{today}}",
    "all_day": false,
    "nb": 0.5,
    "description": "Morning only — afternoon internal meeting"
  }
  ```
- **Post-processor — Extract**: `event_id_4` ← `$.id`
- **Assertions**:
  - HTTP status = `201`
  - JSON `$.nb` = `0.5`
  - JSON `$.all_day` = `false`

### Step 7 — List events for current month (verify all 4 are present)

- **Request**: `GET {{base_url}}/api/cra/events?month={{current_month}}`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$` is array, length ≥ 4
  - JSONPath `$[?(@.id == {{event_id_1}})]` exists
  - JSONPath `$[?(@.id == {{event_id_2}})]` exists
  - JSONPath `$[?(@.id == {{event_id_3}})]` exists
  - JSONPath `$[?(@.id == {{event_id_4}})]` exists

### Step 8 — Update one event (fix description on the half-day)

- **Request**: `PUT {{base_url}}/api/cra/events/{{event_id_4}}`
- **Body** (JSON):
  ```json
  {
    "description": "Morning Prestation — updated",
    "nb": 0.5
  }
  ```
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.description` = `Morning Prestation — updated`
  - JSON `$.nb` = `0.5`

---

## Phase 3 — Submit and Sign the month

### Step 9 — Submit month for validation (Draft → Pending)

- **Request**: `POST {{base_url}}/api/cra/month/{{current_month}}/submit`
- **Body** (JSON):
  ```json
  {
    "description_tasks": "Prestation client + 1 CP — real world flow test",
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
  - JSON `$.month` = `{{current_month}}`

### Step 10 — Upload consultant signature (PNG)

- **Request**: `POST {{base_url}}/api/cra/month/{{current_month}}/signature`
- **Body** (`multipart/form-data`):
  - `file` = `apidog/fixtures/sample_signature.png`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.signature_path` is not null
  - JSON `$.signature_path` contains `signatures`

---

## Phase 4 — Expenses

### Step 11 — Create Restaurant expense (receipt required)

- **Request**: `POST {{base_url}}/api/expenses`
- **Body** (`multipart/form-data`):
  - `type` = `Restaurant`
  - `month` = `{{current_month}}`
  - `description` = `Team lunch`
  - `total_amount` = `38.50`
  - `billable_to_client` = `true`
  - `comment` = `Project kickoff lunch`
  - `receipt` = `apidog/fixtures/sample_receipt.pdf`
- **Post-processor — Extract**: `expense_id_1` ← `$.id`
- **Assertions**:
  - HTTP status = `201`
  - JSON `$.type` = `Restaurant`
  - JSON `$.total_amount` = `38.5`
  - JSON `$.billable_to_client` = `true`
  - JSON `$.receipt_path` is not null
  - JSON `$.status` = `Pending`

### Step 12 — Create Indemnités kilométriques (no receipt needed)

- **Request**: `POST {{base_url}}/api/expenses`
- **Body** (`multipart/form-data`):
  - `type` = `Indemnités kilométriques`
  - `month` = `{{current_month}}`
  - `description` = `Paris → Lyon 450km`
  - `total_amount` = `202.50`
  - `billable_to_client` = `false`
  - `comment` = `Client site visit`
  > No `receipt` field — this type does not require one.
- **Post-processor — Extract**: `expense_id_2` ← `$.id`
- **Assertions**:
  - HTTP status = `201`
  - JSON `$.type` = `Indemnités kilométriques`
  - JSON `$.receipt_path` = null
  - JSON `$.status` = `Pending`

### Step 13 — Create Titre de transport expense (receipt required)

- **Request**: `POST {{base_url}}/api/expenses`
- **Body** (`multipart/form-data`):
  - `type` = `Titre de transport`
  - `month` = `{{current_month}}`
  - `description` = `Train Paris-Lyon`
  - `total_amount` = `89.00`
  - `billable_to_client` = `true`
  - `receipt` = `apidog/fixtures/sample_receipt.pdf`
- **Post-processor — Extract**: `expense_id_3` ← `$.id`
- **Assertions**:
  - HTTP status = `201`
  - JSON `$.type` = `Titre de transport`
  - JSON `$.receipt_path` is not null

### Step 14 — Update Restaurant expense (correct the amount)

- **Request**: `PUT {{base_url}}/api/expenses/{{expense_id_1}}`
- **Body** (JSON):
  ```json
  {
    "total_amount": 42.00,
    "comment": "Updated after checking the receipt"
  }
  ```
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.total_amount` = `42.0`
  - JSON `$.comment` = `Updated after checking the receipt`
  - JSON `$.type` = `Restaurant`

### Step 15 — Filter expenses — verify all 3 are present

- **Request**: `POST {{base_url}}/api/expenses/filter`
- **Body** (JSON):
  ```json
  {
    "year": {{current_year}},
    "page": 1,
    "limit": 50
  }
  ```
  > Pre-script: `pm.environment.set('current_year', parseInt('{{current_month}}'.slice(0, 4)));`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.total` ≥ 3
  - JSONPath `$.items[?(@.id == {{expense_id_1}})]` exists
  - JSONPath `$.items[?(@.id == {{expense_id_2}})]` exists
  - JSONPath `$.items[?(@.id == {{expense_id_3}})]` exists

### Step 16 — Filter expenses by type (Restaurant only)

- **Request**: `POST {{base_url}}/api/expenses/filter`
- **Body** (JSON):
  ```json
  {
    "year": {{current_year}},
    "type": "Restaurant",
    "page": 1,
    "limit": 10
  }
  ```
- **Assertions**:
  - HTTP status = `200`
  - All `$.items[*].type` = `Restaurant`
  - JSONPath `$.items[?(@.id == {{expense_id_1}})]` exists
  - JSONPath `$.items[?(@.id == {{expense_id_2}})]` does NOT exist (it's km, not restaurant)

### Step 17 — Delete the transport expense

- **Request**: `DELETE {{base_url}}/api/expenses/{{expense_id_3}}`
- **Assertions**:
  - HTTP status = `204`

### Step 18 — Verify transport expense is gone

- **Request**: `POST {{base_url}}/api/expenses/filter`
- **Body** (JSON):
  ```json
  {
    "year": {{current_year}},
    "page": 1,
    "limit": 50
  }
  ```
- **Assertions**:
  - HTTP status = `200`
  - JSONPath `$.items[?(@.id == {{expense_id_3}})]` does NOT exist
  - JSONPath `$.items[?(@.id == {{expense_id_1}})]` exists
  - JSONPath `$.items[?(@.id == {{expense_id_2}})]` exists

---

## Phase 5 — CRA Tracking

### Step 19 — Check CRA tracking (month should be Pending)

- **Request**: `GET {{base_url}}/api/cra-tracking/months?page=1&limit=10`
- **Assertions**:
  - HTTP status = `200`
  - JSONPath `$.items[?(@.month == "{{current_month}}")]` exists
  - JSONPath `$.items[?(@.month == "{{current_month}}") && (@.status == "Pending")]` exists
  - JSON `$.items[?(@.month == "{{current_month}}")].signature_path` is not null

### Step 20 — Import signed client CRA PDF

- **Request**: `POST {{base_url}}/api/cra-tracking/months/{{current_month}}/import-client-cra`
- **Body** (`multipart/form-data`):
  - `file` = `apidog/fixtures/sample_receipt.pdf`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.client_cra_path` is not null
  - JSON `$.client_cra_path` contains `client-cra`
  - JSON `$.month` = `{{current_month}}`

### Step 21 — Verify client CRA path is stored in tracking list

- **Request**: `GET {{base_url}}/api/cra-tracking/months?page=1&limit=10`
- **Assertions**:
  - HTTP status = `200`
  - JSONPath `$.items[?(@.month == "{{current_month}}")].client_cra_path` is not null

---

## Phase 6 — Cleanup

### Step 22 — Delete Restaurant expense

- **Request**: `DELETE {{base_url}}/api/expenses/{{expense_id_1}}`
- **Assertions**: HTTP status = `204`

### Step 23 — Delete km expense

- **Request**: `DELETE {{base_url}}/api/expenses/{{expense_id_2}}`
- **Assertions**: HTTP status = `204`

### Step 24 — Delete half-day event

- **Request**: `DELETE {{base_url}}/api/cra/events/{{event_id_4}}`
- **Assertions**: HTTP status = `204`

### Step 25 — Delete absence event

- **Request**: `DELETE {{base_url}}/api/cra/events/{{event_id_3}}`
- **Assertions**: HTTP status = `204`

### Step 26 — Delete multi-day event

- **Request**: `DELETE {{base_url}}/api/cra/events/{{event_id_2}}`
- **Assertions**: HTTP status = `204`

### Step 27 — Delete single-day event

- **Request**: `DELETE {{base_url}}/api/cra/events/{{event_id_1}}`
- **Assertions**: HTTP status = `204`

### Step 28 — Final verify: event list is empty for this month

- **Request**: `GET {{base_url}}/api/cra/events?month={{current_month}}`
- **Assertions**:
  - HTTP status = `200`
  - JSONPath `$[?(@.id == {{event_id_1}})]` does NOT exist
  - JSONPath `$[?(@.id == {{event_id_3}})]` does NOT exist

---

## Notes

- **Re-running**: the month stays `Pending` after Step 9. Delete `mock-api/app.db`
  and restart the server to get a clean state between full runs.
- **Dates**: Steps 3–6 use dynamic dates — if today is the 1st, 3rd, or 5th of the
  month, events may overlap. The server doesn't block overlapping events so it
  will still pass, but be aware.
- **add to environment**: add `event_id_1`, `event_id_2`, `event_id_3`, `event_id_4`,
  `expense_id_1`, `expense_id_2`, `expense_id_3` as empty variables in `CRA API MOCK DEV ENV`.
