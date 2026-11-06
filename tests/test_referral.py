"""Referral page."""

import pytest

BASE = "/api/v2/treatment_plans"

COMPLETE = {
    "referral_date": "2024-05-01",
    "provider_name": "Dr. Jane Smith",
    "diagnosis_tool": "ADOS-2 (Autism Diagnostic Observation Schedule)",
    "city": "Austin",
    "state": "TX",
}


def url(plan_id, path=""):
    return f"{BASE}/{plan_id}/pages/referrals/{path}"


def status(client, plan_id):
    return next(s for s in client.get(f"{BASE}/{plan_id}/pages/").json() if s["page"] == "referral")


def test_no_rows_is_empty(client, plan_id):
    assert status(client, plan_id)["status"] == "empty"


@pytest.mark.parametrize("field,value", [("provider_name", "Dr. Who"), ("city", "A"), ("state", "XX"), ("diagnosis_tool", "Other tool")])
def test_save_rules_reject(client, plan_id, field, value):
    assert client.post(url(plan_id), json={field: value}).status_code == 422


def test_partial_row_is_error_then_complete(client, plan_id):
    row = client.post(url(plan_id), json={"city": "Austin"}).json()
    page = status(client, plan_id)
    assert page["status"] == "error"
    assert {e["field"] for e in page["errors"]} == {"referral_date", "provider_name", "diagnosis_tool", "state"}
    client.patch(url(plan_id, f"{row['id']}/"), json=COMPLETE)
    assert status(client, plan_id)["status"] == "completed"
    assert client.get(url(plan_id)).json() == [{"id": row["id"], **COMPLETE}]


def test_row_from_other_plan_is_404(client, plan_id):
    other = client.post(f"{BASE}/", json={"client_id": 1, "bay": "3"}).json()["id"]
    row = client.post(url(other), json=COMPLETE).json()
    assert client.patch(url(plan_id, f"{row['id']}/"), json={"city": "Dallas"}).status_code == 404
    assert client.delete(url(plan_id, f"{row['id']}/")).status_code == 404


def test_delete(client, plan_id):
    row = client.post(url(plan_id), json=COMPLETE).json()
    assert client.delete(url(plan_id, f"{row['id']}/")).status_code == 204
    assert status(client, plan_id)["status"] == "empty"
