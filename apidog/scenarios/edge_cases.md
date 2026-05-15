# Edge Cases & Negative Tests — CRA Mock API

All scenarios that should return errors or enforce business rules.
Run these against a **clean database** (`del mock-api\app.db`, restart server).

---

## Scenario A — Authentication errors

### A-1 — Login with wrong password → 401
- **Request**: `POST {{base_url}}/api/auth/login`
- **Body** (`x-www-form-urlencoded`): `username={{email}}`, `password=wrongpassword`
- **Assertions**: HTTP status = `401`

### A-2 — Login with unknown email → 401
- **Request**: `POST {{base_url}}/api/auth/login`
- **Body**: `username=nobody@nowhere.com`, `password=demo1234`
- **Assertions**: HTTP status = `401`

### A-3 — Access protected endpoint without token → 401
- **Request**: `GET {{base_url}}/api/auth/me`
- **Auth**: None (remove Bearer header)
- **Assertions**: HTTP status = `401`

### A-4 — Access protected endpoint with malformed token → 401
- **Request**: `GET {{base_url}}/api/auth/me`
- **Auth**: `Bearer not-a-valid-jwt`
- **Assertions**: HTTP status = `401`

---

## Scenario B — CRA Event validation errors

> Pre-condition: login first and store `bearerToken`.

### B-1 — Category / activity mismatch → 400
- **Request**: `POST {{base_url}}/api/cra/events`
- **Body**:
  ```json
  {
    "categorie": "Absence",
    "activity": "Prestation",
    "start_date": "{{today}}",
    "end_date": "{{today}}",
    "all_day": true,
    "nb": 1.0
  }
  ```
- **Assertions**:
  - HTTP status = `400`
  - JSON `$.detail` contains `not allowed`

### B-2 — Travail activity in Absence category → 400
- **Request**: `POST {{base_url}}/api/cra/events`
- **Body**:
  ```json
  {
    "categorie": "Travail",
    "activity": "CP",
    "start_date": "{{today}}",
    "end_date": "{{today}}",
    "all_day": true,
    "nb": 1.0
  }
  ```
- **Assertions**: HTTP status = `400`

### B-3 — end_date before start_date → 400
- **Request**: `POST {{base_url}}/api/cra/events`
- **Body**:
  ```json
  {
    "categorie": "Travail",
    "activity": "Prestation",
    "start_date": "{{today}}",
    "end_date": "{{month_start}}",
    "all_day": true,
    "nb": 1.0
  }
  ```
  > Pre-script: ensure `today` > `month_start` (skip if today is the 1st).
- **Assertions**: HTTP status = `400`

### B-4 — Malformed month query param → 422
- **Request**: `GET {{base_url}}/api/cra/events?month=2026-13`
- **Assertions**:
  - HTTP status = `422`
  - JSON `$.detail[0].msg` contains `pattern`

### B-5 — Missing required field (no categorie) → 422
- **Request**: `POST {{base_url}}/api/cra/events`
- **Body**:
  ```json
  {
    "activity": "Prestation",
    "start_date": "{{today}}",
    "end_date": "{{today}}"
  }
  ```
- **Assertions**: HTTP status = `422`

### B-6 — GET events for a month with no events → empty array
- **Request**: `GET {{base_url}}/api/cra/events?month=2000-01`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$` is array, length = `0`

### B-7 — Update non-existent event → 404
- **Request**: `PUT {{base_url}}/api/cra/events/999999`
- **Body**: `{ "description": "ghost" }`
- **Assertions**: HTTP status = `404`

### B-8 — Update event — set end_date before start_date → 400
> Pre-condition: create an event first, store `event_id_temp`.
- **Request**: `PUT {{base_url}}/api/cra/events/{{event_id_temp}}`
- **Body**:
  ```json
  {
    "start_date": "{{today}}",
    "end_date": "{{month_start}}"
  }
  ```
  > Pre-script: ensure `today` > `month_start`.
- **Assertions**: HTTP status = `400`

### B-9 — Update event — introduce category/activity mismatch → 400
> Pre-condition: same event from B-8 (Travail/Prestation).
- **Request**: `PUT {{base_url}}/api/cra/events/{{event_id_temp}}`
- **Body**: `{ "activity": "CP" }`
- **Assertions**: HTTP status = `400`

### B-10 — Delete non-existent event → 404
- **Request**: `DELETE {{base_url}}/api/cra/events/999999`
- **Assertions**: HTTP status = `404`

### B-11 — Create event on a Validated month → 409
> Pre-condition: the seeded demo data already has validated months (e.g. `2026-01`).
> Check `/api/cra-tracking/months` to find a validated month and store it in `validated_month`.
- **Request**: `POST {{base_url}}/api/cra/events`
- **Body**:
  ```json
  {
    "categorie": "Travail",
    "activity": "Prestation",
    "start_date": "{{validated_month}}-15",
    "end_date": "{{validated_month}}-15",
    "all_day": true,
    "nb": 1.0
  }
  ```
- **Assertions**: HTTP status = `409`

---

## Scenario C — CRA Month errors

### C-1 — Submit already Validated month → 409
> Pre-condition: find a validated month from seed data.
- **Request**: `POST {{base_url}}/api/cra/month/{{validated_month}}/submit`
- **Body**: `{ "description_tasks": "should fail" }`
- **Assertions**: HTTP status = `409`

### C-2 — Submit with malformed month path param → 422
- **Request**: `POST {{base_url}}/api/cra/month/2026-13/submit`
- **Body**: `{ "description_tasks": "bad month" }`
- **Assertions**: HTTP status = `422`

### C-3 — Upload signature with unsupported file type → 415
- **Request**: `POST {{base_url}}/api/cra/month/{{current_month}}/signature`
- **Body** (`multipart/form-data`): `file` = any `.txt` or `.exe` file
- **Assertions**: HTTP status = `415`

### C-4 — Re-submit a Pending month (allowed — re-stamps submitted_at)
> This is a behavior check, not an error.
> Pre-condition: submit a month once (it becomes Pending), then submit again.
- **Request**: `POST {{base_url}}/api/cra/month/{{current_month}}/submit`
- **Body**: `{ "description_tasks": "second submission" }`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.status` = `Pending`
  - JSON `$.description_tasks` = `second submission`

---

## Scenario D — Expense validation errors

### D-1 — Create Restaurant expense without receipt → 400
- **Request**: `POST {{base_url}}/api/expenses`
- **Body** (`multipart/form-data`):
  - `type` = `Restaurant`
  - `month` = `{{current_month}}`
  - `description` = `no receipt`
  - `total_amount` = `20.00`
  > No `receipt` field.
- **Assertions**:
  - HTTP status = `400`
  - JSON `$.detail` contains `receipt`

### D-2 — Create Indemnités kilométriques without receipt → 201 (receipt optional)
- **Request**: `POST {{base_url}}/api/expenses`
- **Body** (`multipart/form-data`):
  - `type` = `Indemnités kilométriques`
  - `month` = `{{current_month}}`
  - `description` = `no receipt needed`
  - `total_amount` = `50.00`
  > No `receipt` field — should succeed.
- **Assertions**:
  - HTTP status = `201`
  - JSON `$.receipt_path` = null

### D-3 — Upload receipt with unsupported extension → 415
- **Request**: `POST {{base_url}}/api/expenses`
- **Body** (`multipart/form-data`):
  - `type` = `Restaurant`
  - `month` = `{{current_month}}`
  - `total_amount` = `15.00`
  - `receipt` = a `.txt` file (rename `sample_receipt.pdf` to `.txt` or use any text file)
- **Assertions**: HTTP status = `415`

### D-4 — Create expense with zero amount → 422
- **Request**: `POST {{base_url}}/api/expenses`
- **Body** (`multipart/form-data`):
  - `type` = `Restaurant`
  - `month` = `{{current_month}}`
  - `total_amount` = `0`
  - `receipt` = `apidog/fixtures/sample_receipt.pdf`
- **Assertions**: HTTP status = `422`

### D-5 — Update non-existent expense → 404
- **Request**: `PUT {{base_url}}/api/expenses/999999`
- **Body**: `{ "total_amount": 10.0 }`
- **Assertions**: HTTP status = `404`

### D-6 — Delete non-existent expense → 404
- **Request**: `DELETE {{base_url}}/api/expenses/999999`
- **Assertions**: HTTP status = `404`

### D-7 — Filter expenses with invalid month value → 422
- **Request**: `POST {{base_url}}/api/expenses/filter`
- **Body**: `{ "year": 2026, "month": 13 }`
- **Assertions**: HTTP status = `422`

### D-8 — Filter expenses with missing year → 422
- **Request**: `POST {{base_url}}/api/expenses/filter`
- **Body**: `{ "month": 5 }`
- **Assertions**: HTTP status = `422`

---

## Scenario E — Extended coverage (pagination & filters)

### E-1 — CRA tracking: filter by year
- **Request**: `GET {{base_url}}/api/cra-tracking/months?year={{current_year}}&page=1&limit=10`
- **Assertions**:
  - HTTP status = `200`
  - All `$.items[*].month` start with `{{current_year}}`

### E-2 — CRA tracking: filter by month number
- **Request**: `GET {{base_url}}/api/cra-tracking/months?month=1&page=1&limit=10`
- **Assertions**:
  - HTTP status = `200`
  - All `$.items[*].month` end with `-01`

### E-3 — CRA tracking: page beyond results → empty items
- **Request**: `GET {{base_url}}/api/cra-tracking/months?page=9999&limit=10`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.items` is empty array
  - JSON `$.total` ≥ 0

### E-4 — Expenses filter: billable only
- **Request**: `POST {{base_url}}/api/expenses/filter`
- **Body**: `{ "year": {{current_year}}, "billable": true, "page": 1, "limit": 10 }`
- **Assertions**:
  - HTTP status = `200`
  - All `$.items[*].billable_to_client` = `true`

### E-5 — Expenses filter: by status (Pending)
- **Request**: `POST {{base_url}}/api/expenses/filter`
- **Body**: `{ "year": {{current_year}}, "status": "Pending", "page": 1, "limit": 10 }`
- **Assertions**:
  - HTTP status = `200`
  - All `$.items[*].status` = `Pending`

### E-6 — Expenses pagination: limit=1 returns exactly 1 item
> Pre-condition: at least 2 expenses exist.
- **Request**: `POST {{base_url}}/api/expenses/filter`
- **Body**: `{ "year": {{current_year}}, "page": 1, "limit": 1 }`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.items` length = `1`
  - JSON `$.limit` = `1`
  - JSON `$.pages` ≥ `1`

### E-7 — All Travail activities are accepted
Run one create event per activity: `Prestation`, `HNO`, `Astreinte`.
Each should return `201` with the correct `activity` echoed back.

| activity | expected |
|---|---|
| `Prestation` | `201` |
| `HNO` | `201` |
| `Astreinte` | `201` |

### E-8 — All Absence activities are accepted
Run one create event per activity: `CP`, `RTT`, `Maladie`, `Sans solde`, `Autre`.

| activity | expected |
|---|---|
| `CP` | `201` |
| `RTT` | `201` |
| `Maladie` | `201` |
| `Sans solde` | `201` |
| `Autre` | `201` |

### E-9 — All expense types that require a receipt
Run one create expense per type with a valid receipt.

| type | receipt required | expected |
|---|---|---|
| `Restaurant` | yes | `201` |
| `Titre de transport` | yes | `201` |
| `Telephonie` | yes | `201` |
| `Teletravail` | yes | `201` |
| `Materiel` | yes | `201` |
| `Autre` | yes | `201` |
| `Indemnités kilométriques` | no | `201` |

### E-10 — Healthz is always reachable (no auth)
- **Request**: `GET {{base_url}}/healthz`
- **Assertions**:
  - HTTP status = `200`
  - JSON `$.status` = `ok`

---

## Notes

- Scenarios B-8, B-9 share `event_id_temp`. Create one event at the start of
  Scenario B (a helper step) and clean it up at the end.
- Scenario B-11 requires a Validated month. Seed data has past validated months.
  Use `GET /api/cra-tracking/months` to find one, extract its `month` field into
  `validated_month` env variable before running B-11 and C-1.
- Scenarios E-7, E-8, E-9 are best run as separate "bulk create" steps with
  cleanup at the end (delete all created events/expenses).
