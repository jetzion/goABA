"""Therapy page."""

import pytest

BASE = "/api/v2/treatment_plans"

COMPLETE = {
    "provider_name": "Bright Steps Clinic",
    "service_type": "Speech Therapy",
    "phone_number": "5125550100",
    "email": "office@brightsteps.example",
    "start_date": "2023-01-01",
    "end_date": "2024-01-01",
    "hours": 2.5,
    "frequency": "Weekly",
    "progress": "Positive improvement",
    "is_record_shared": "Shared",
}


def url(plan_id, path=""):
    return f"{BASE}/{plan_id}/pages/therapy/{path}"


def status(client, plan_id):
    return next(s for s in client.get(f"{BASE}/{plan_id}/pages/").json() if s["page"] == "therapy")


def set_box(client, plan_id, checked):
    return client.patch(url(plan_id), json={"no_historical_therapy": checked})


def test_not_answered_no_rows_is_empty(client, plan_id):
    assert status(client, plan_id)["status"] == "empty"
    assert client.get(url(plan_id)).json() == {"no_historical_therapy": None, "therapies": []}


def test_not_answered_with_rows_is_error(client, plan_id):
    client.post(url(plan_id), json=COMPLETE)
    assert status(client, plan_id)["status"] == "error"


def test_checked_no_rows_is_complete(client, plan_id):
    set_box(client, plan_id, True)
    assert status(client, plan_id)["status"] == "completed"


def test_checked_with_rows_is_error(client, plan_id):
    set_box(client, plan_id, True)
    client.post(url(plan_id), json=COMPLETE)
    assert status(client, plan_id)["status"] == "error"


def test_unchecked_no_rows_is_error(client, plan_id):
    set_box(client, plan_id, False)
    assert status(client, plan_id)["status"] == "error"


def test_unchecked_with_valid_row_is_complete(client, plan_id):
    set_box(client, plan_id, False)
    row = client.post(url(plan_id), json=COMPLETE).json()
    assert row["hours"] == 2.5
    assert row["do_not_share_info_with_provider"] is False
    assert status(client, plan_id)["status"] == "completed"


def test_create_needs_clinical_field(client, plan_id):
    assert client.post(url(plan_id), json={"do_not_share_info_with_provider": True}).status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [("hours", 2.55), ("hours", 1000), ("hours", -1), ("phone_number", "512555010"), ("email", "nope"), ("end_date", "2024-01-02"), ("frequency", "Yearly")],
)
def test_save_rules_reject(client, plan_id, field, value):
    assert client.post(url(plan_id), json={**COMPLETE, field: value}).status_code == 422


def test_do_not_share_cannot_be_null(client, plan_id):
    row = client.post(url(plan_id), json=COMPLETE).json()
    assert client.patch(url(plan_id, f"{row['id']}/"), json={"do_not_share_info_with_provider": None}).status_code == 422


def test_omitted_do_not_share_keeps_value(client, plan_id):
    row = client.post(url(plan_id), json={**COMPLETE, "is_record_shared": None, "do_not_share_info_with_provider": True}).json()
    patched = client.patch(url(plan_id, f"{row['id']}/"), json={"hours": 3}).json()
    assert patched["do_not_share_info_with_provider"] is True


def test_record_shared_must_be_empty_when_not_sharing(client, plan_id):
    set_box(client, plan_id, False)
    client.post(url(plan_id), json={**COMPLETE, "do_not_share_info_with_provider": True})
    assert status(client, plan_id)["errors"][0]["field"] == "is_record_shared"


def test_record_shared_required_when_sharing(client, plan_id):
    set_box(client, plan_id, False)
    client.post(url(plan_id), json={**COMPLETE, "is_record_shared": None})
    assert status(client, plan_id)["errors"][0]["field"] == "is_record_shared"


def test_end_before_start_is_error(client, plan_id):
    set_box(client, plan_id, False)
    client.post(url(plan_id), json={**COMPLETE, "end_date": "2022-06-01"})
    assert status(client, plan_id)["errors"][0]["field"] == "end_date"


def test_end_date_optional(client, plan_id):
    set_box(client, plan_id, False)
    client.post(url(plan_id), json={**COMPLETE, "end_date": None})
    assert status(client, plan_id)["status"] == "completed"
