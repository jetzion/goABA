"""Medication page."""

from datetime import date

import pytest

BASE = "/api/v2/treatment_plans"

COMPLETE = {
    "medication_name": "Melatonin",
    "dosage": "1mg",
    "start_date": "2024-01-01",
    "physician_name": "Dr. Jane Smith",
    "reason": "Sleep onset difficulty",
}


def url(plan_id, path=""):
    return f"{BASE}/{plan_id}/pages/medications/{path}"


def status(client, plan_id):
    return next(s for s in client.get(f"{BASE}/{plan_id}/pages/").json() if s["page"] == "medication")


def set_box(client, plan_id, checked):
    return client.patch(url(plan_id), json={"no_medication": checked})


def test_not_answered_no_rows_is_empty(client, plan_id):
    assert status(client, plan_id)["status"] == "empty"
    assert client.get(url(plan_id)).json() == {"no_medication": None, "medications": []}


def test_not_answered_with_rows_is_error(client, plan_id):
    client.post(url(plan_id), json=COMPLETE)
    assert status(client, plan_id)["errors"][0]["message"] == "Select whether the client takes medication"


def test_checked_no_rows_is_complete(client, plan_id):
    assert set_box(client, plan_id, True).json()["no_medication"] is True
    assert status(client, plan_id)["status"] == "completed"


def test_checked_with_rows_is_error(client, plan_id):
    set_box(client, plan_id, True)
    client.post(url(plan_id), json=COMPLETE)
    assert status(client, plan_id)["status"] == "error"


def test_unchecked_no_rows_is_error(client, plan_id):
    set_box(client, plan_id, False)
    assert status(client, plan_id)["errors"][0]["message"] == "Add a medication or check no medication"


def test_unchecked_with_valid_rows_is_complete(client, plan_id):
    set_box(client, plan_id, False)
    client.post(url(plan_id), json=COMPLETE)
    assert status(client, plan_id)["status"] == "completed"


def test_unchecked_with_partial_row_is_error(client, plan_id):
    set_box(client, plan_id, False)
    row = client.post(url(plan_id), json={"medication_name": "Melatonin"}).json()
    page = status(client, plan_id)
    assert {(e["field"], e["row_id"]) for e in page["errors"]} >= {("dosage", row["id"])}


def test_create_needs_a_field(client, plan_id):
    assert client.post(url(plan_id), json={}).status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [("start_date", "2024-01-15"), ("start_date", "2999-01-01"), ("dosage", "1"), ("physician_name", "Dr. Who")],
)
def test_save_rules_reject(client, plan_id, field, value):
    assert client.post(url(plan_id), json={field: value}).status_code == 422


def test_current_month_allowed(client, plan_id):
    this_month = date.today().replace(day=1).isoformat()
    assert client.post(url(plan_id), json={"start_date": this_month}).status_code == 201


def test_start_before_birth_is_error(client, plan_id):
    set_box(client, plan_id, False)
    client.post(url(plan_id), json={**COMPLETE, "start_date": "2019-03-01"})
    assert status(client, plan_id)["errors"][0]["field"] == "start_date"


def test_birth_month_allowed(client, plan_id):
    set_box(client, plan_id, False)
    client.post(url(plan_id), json={**COMPLETE, "start_date": "2019-04-01"})
    assert status(client, plan_id)["status"] == "completed"


def test_delete_all(client, plan_id):
    client.post(url(plan_id), json=COMPLETE)
    client.post(url(plan_id), json=COMPLETE)
    assert client.delete(url(plan_id, "all/")).status_code == 204
    assert client.get(url(plan_id)).json()["medications"] == []
