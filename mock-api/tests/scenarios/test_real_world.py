"""Real-world consultant monthly workflow as a single end-to-end test.

Mirrors apidog/scenarios/real_world_flow.md step by step.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests._helpers import (
    create_event,
    create_expense,
    delete_event,
    delete_expense,
    filter_expenses,
    import_client_cra,
    list_events,
    list_tracking_months,
    submit_month,
    update_event,
    update_expense,
    upload_signature,
)


def test_real_world_consultant_monthly_flow(
    client: TestClient,
    auth_headers: dict[str, str],
    today: str,
    current_month: str,
    current_year: int,
    month_start: str,
    month_day_3: str,
    month_day_5: str,
    sample_pdf: bytes,
    sample_png: bytes,
) -> None:
    """Full consultant workflow:
    login -> fill CRA (work, multi-day, absence, half-day) -> submit
    -> sign -> expenses (3 types) -> update -> filter -> track -> cleanup.
    """
    # ------------------------------------------------------------------
    # Phase 1 — bootstrap (auth is via auth_headers fixture)
    # ------------------------------------------------------------------
    enums = client.get("/api/enums").json()
    assert "Prestation" in enums["cra_activities"]["Travail"]
    assert "CP" in enums["cra_activities"]["Absence"]

    # ------------------------------------------------------------------
    # Phase 2 — fill the CRA (4 events, varied)
    # ------------------------------------------------------------------
    e1 = create_event(client, auth_headers, start_date=today, description="Client onsite")
    e2 = create_event(
        client,
        auth_headers,
        start_date=month_start,
        end_date=month_day_3,
        description="Sprint delivery",
    )
    e3 = create_event(
        client,
        auth_headers,
        categorie="Absence",
        activity="CP",
        start_date=month_day_5,
        description="Paid leave",
    )
    e4 = create_event(
        client,
        auth_headers,
        start_date=today,
        all_day=False,
        nb=0.5,
        description="Morning only",
    )

    # List should contain all 4
    events = list_events(client, auth_headers, current_month)
    ids = {ev["id"] for ev in events}
    assert {e1["id"], e2["id"], e3["id"], e4["id"]}.issubset(ids)

    # Correct one mistake
    updated = update_event(
        client, auth_headers, e4["id"], description="Morning Prestation — updated"
    )
    assert updated["description"] == "Morning Prestation — updated"

    # ------------------------------------------------------------------
    # Phase 3 — submit and sign
    # ------------------------------------------------------------------
    month = submit_month(client, auth_headers, current_month, "Prestation + CP — real world")
    assert month["status"] == "Pending"
    assert month["submitted_at"] is not None

    signed = upload_signature(client, auth_headers, current_month, sample_png)
    assert signed["signature_path"] is not None

    # ------------------------------------------------------------------
    # Phase 4 — expenses (3 types)
    # ------------------------------------------------------------------
    restaurant = create_expense(
        client,
        auth_headers,
        type="Restaurant",
        month=current_month,
        total_amount=38.50,
        billable_to_client=True,
        description="Team lunch",
        receipt=("r.pdf", sample_pdf, "application/pdf"),
    )
    km = create_expense(
        client,
        auth_headers,
        type="Indemnités kilométriques",
        month=current_month,
        total_amount=202.50,
        description="Paris->Lyon 450km",
    )
    assert km["receipt_path"] is None
    transport = create_expense(
        client,
        auth_headers,
        type="Titre de transport",
        month=current_month,
        total_amount=89.00,
        billable_to_client=True,
        receipt=("r.pdf", sample_pdf, "application/pdf"),
    )

    # Correct the restaurant amount
    corrected = update_expense(client, auth_headers, restaurant["id"], total_amount=42.00)
    assert corrected["total_amount"] == 42.00

    # All 3 visible in filter
    all_expenses = filter_expenses(client, auth_headers, year=current_year, limit=50)
    ids = {x["id"] for x in all_expenses["items"]}
    assert {restaurant["id"], km["id"], transport["id"]}.issubset(ids)

    # Filter by type
    restos = filter_expenses(client, auth_headers, year=current_year, type="Restaurant")
    assert all(x["type"] == "Restaurant" for x in restos["items"])
    assert restaurant["id"] in {x["id"] for x in restos["items"]}
    assert km["id"] not in {x["id"] for x in restos["items"]}

    # Delete the transport one, confirm it's gone
    delete_expense(client, auth_headers, transport["id"])
    after_delete = filter_expenses(client, auth_headers, year=current_year, limit=50)
    assert transport["id"] not in {x["id"] for x in after_delete["items"]}

    # ------------------------------------------------------------------
    # Phase 5 — tracking page + import client CRA
    # ------------------------------------------------------------------
    tracking = list_tracking_months(client, auth_headers, page=1, limit=10)
    cm_row = next(m for m in tracking["items"] if m["month"] == current_month)
    assert cm_row["status"] == "Pending"
    assert cm_row["signature_path"] is not None

    imported = import_client_cra(client, auth_headers, current_month, sample_pdf)
    assert imported["client_cra_path"] is not None

    tracking2 = list_tracking_months(client, auth_headers, page=1, limit=10)
    cm_row2 = next(m for m in tracking2["items"] if m["month"] == current_month)
    assert cm_row2["client_cra_path"] is not None

    # ------------------------------------------------------------------
    # Phase 6 — cleanup
    # ------------------------------------------------------------------
    delete_expense(client, auth_headers, restaurant["id"])
    delete_expense(client, auth_headers, km["id"])
    for ev_id in (e4["id"], e3["id"], e2["id"], e1["id"]):
        delete_event(client, auth_headers, ev_id)

    final_events = list_events(client, auth_headers, current_month)
    final_ids = {ev["id"] for ev in final_events}
    assert not {e1["id"], e2["id"], e3["id"], e4["id"]}.intersection(final_ids)
